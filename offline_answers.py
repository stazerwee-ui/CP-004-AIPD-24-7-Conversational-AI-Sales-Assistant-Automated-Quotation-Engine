"""
offline_answers.py — Deterministic semantic retrieval over curated FAQ and blog posts
for Solace Dignity Care Conversational AI Assistant.

Enables Mode B (Ollama offline/outage fallback) to return human-written,
hallucination-free answers from dataset.json rather than degrading to thin catch-alls.

Features:
- Corpus flattening: 100 substantive FAQs + 49 price-free blog posts = 149 entries.
- Excludes empty services and competitor packages (Funeral Guru / Direct Funeral).
- Embeds questions/titles, NOT long answers, ensuring tight semantic alignment.
- Persistent vector cache in data/offline_answers_vectors.json.
- Dual-gated retrieval:
    - Absolute threshold (0.62)
    - Margin gate (0.04) against runner-up to reject ambiguous queries.
"""

import os
import re
import json
import hashlib
from typing import List, Dict, Optional, Any, Sequence, Tuple

from semantic_router import (
    BaseEmbedProvider,
    resolve_provider,
    get_semantic_router,
    cosine_similarity
)

DEFAULT_RETRIEVAL_THRESHOLD = 0.62
DEFAULT_RETRIEVAL_MARGIN = 0.04

# Two curated third-party price FAQ entries that are explicitly safe to keep
SAFE_PRICE_FAQ_IDS = {"kdc_faq_045", "kdc_faq_099"}


def is_substantive_answer_text(text: Optional[str]) -> bool:
    """Checks whether text is a substantive answer and not a placeholder or heading."""
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < 40:
        return False
    first_sentence = re.split(r"(?<=[.!?])\s", stripped, maxsplit=1)
    if stripped.endswith("?") and len(first_sentence) == 1:
        return False
    if stripped.lower().startswith((
        "frequently asked", "can't find what you need", "cant find what you need",
        "let us handle", "honor their memory"
    )):
        return False
    return True


class AnswerIndex:
    """
    In-memory vector search index over curated FAQ and blog knowledge items.
    """

    def __init__(
        self,
        provider: Optional[BaseEmbedProvider] = None,
        dataset_path: Optional[str] = None,
        cache_path: Optional[str] = None
    ):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_json = os.path.join(base_dir, "data", "dataset.json")
        self.dataset_path = dataset_path or (data_json if os.path.exists(data_json) else os.path.join(base_dir, "dataset.json"))
        self.cache_path = cache_path or os.path.join(base_dir, "data", "offline_answers_vectors.json")
        self.provider = provider or resolve_provider()
        self.entries: List[Dict[str, Any]] = []
        self.vectors: List[List[float]] = []
        self.is_ready = False
        self.cache_loaded = False

    def build_corpus(self, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extracts and filters corpus items from dataset.json:
        - 100 substantive FAQs
        - 49 price-free blog posts
        Total: 149 curated knowledge items.
        """
        if data is None:
            if not os.path.exists(self.dataset_path):
                print(f"[offline_answers] dataset file not found: {self.dataset_path}")
                return []
            try:
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[offline_answers] error reading dataset.json: {e}")
                return []

        entries: List[Dict[str, Any]] = []

        # 1. Process FAQs (100 kept)
        faqs = data.get("faq", [])
        for item in faqs:
            item_id = item.get("id", "")
            q = (item.get("question") or "").strip()
            a = (item.get("answer") or "").strip()
            
            if not q or not a:
                continue
            
            # Length filter: removes ~30 heading-like/empty answers
            if len(a) < 40 or (a.endswith("?") and "?" not in a[:-1] and "." not in a):
                continue
            
            entries.append({
                "id": item_id,
                "type": "faq",
                "question": q,
                "answer": a,
                "category": item.get("category", ""),
                "keywords": item.get("keywords", [])
            })

        # 2. Process Blog Posts (49 kept)
        blogs = data.get("blogPosts", [])
        for post in blogs:
            post_id = post.get("id", "")
            title = (post.get("title") or "").strip()
            content = (post.get("content") or post.get("excerpt") or "").strip()
            
            if not title or not content:
                continue
            
            # Length filter
            if len(content) < 40:
                continue
            
            # Exclude blog posts mentioning prices ($300+, $200,000, etc.)
            has_price = bool(re.search(r"\$\s*\d{3,}", content + " " + title))
            if has_price:
                continue
            
            entries.append({
                "id": post_id,
                "type": "blog",
                "question": title,
                "answer": content,
                "url": post.get("url", "")
            })

        return entries

    def _compute_corpus_hash(self, entries: List[Dict[str, Any]]) -> str:
        """Computes a checksum over all corpus questions and answers."""
        hasher = hashlib.sha256()
        for e in sorted(entries, key=lambda x: x.get("id", "")):
            hasher.update(e.get("id", "").encode("utf-8"))
            hasher.update(e.get("question", "").encode("utf-8"))
            hasher.update(e.get("answer", "").encode("utf-8"))
        return hasher.hexdigest()[:16]

    def load_or_build(self, catalog_data: Optional[Dict[str, Any]] = None):
        """Loads vector index from cache or computes embeddings and builds index."""
        self.entries = self.build_corpus(catalog_data)
        if not self.entries:
            print("[offline_answers] corpus is empty; index not built")
            return

        corpus_hash = self._compute_corpus_hash(self.entries)
        cache_key = f"{self.provider.provider_name}:{self.provider.model_name}:{self.provider.dimension}:{corpus_hash}"

        # 1. Try loading from cache
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("cache_key") == cache_key:
                    cached_vecs = cached.get("vectors", [])
                    if len(cached_vecs) == len(self.entries):
                        self.vectors = cached_vecs
                        self.is_ready = True
                        self.cache_loaded = True
                        print(f"[offline_answers] loaded {len(self.entries)} vector entries from cache")
                        return
            except Exception as e:
                print(f"[offline_answers] cache load error: {e}")

        # 2. Build embeddings
        if not self.provider.is_available:
            print("[offline_answers] embedding provider unavailable; vector index disabled")
            return

        print(f"[offline_answers] embedding {len(self.entries)} questions/titles via {self.provider.provider_name}...")
        questions = [e["question"] for e in self.entries]
        raw_vectors = self.provider.embed_texts(questions)

        if len(raw_vectors) != len(self.entries) or any(len(v) == 0 for v in raw_vectors):
            print("[offline_answers] failed to embed all questions; index incomplete")
            return

        self.vectors = raw_vectors
        self.is_ready = True

        # 3. Save cache
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({
                    "cache_key": cache_key,
                    "provider": self.provider.provider_name,
                    "model": self.provider.model_name,
                    "dimension": self.provider.dimension,
                    "corpus_hash": corpus_hash,
                    "count": len(self.entries),
                    "vectors": self.vectors
                }, f)
            print(f"[offline_answers] saved {len(self.entries)} vectors to {self.cache_path}")
            self.cache_loaded = True
        except Exception as e:
            print(f"[offline_answers] failed to save vector cache: {e}")

    def retrieve(
        self,
        query: str,
        threshold: float = DEFAULT_RETRIEVAL_THRESHOLD,
        margin: float = DEFAULT_RETRIEVAL_MARGIN
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves best matching FAQ or blog answer using semantic similarity against questions.
        Applies:
        - Absolute threshold gate (default 0.62)
        - Margin gate (default 0.04) against runner-up to reject ambiguous queries.
        """
        if not self.is_ready or not self.provider.is_available or not query or not self.vectors:
            return None

        query_vec = self.provider.embed_single(query)
        if not query_vec:
            return None

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for vec, entry in zip(self.vectors, self.entries):
            sim = cosine_similarity(query_vec, vec)
            scored.append((sim, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return None

        best_score, best_entry = scored[0]

        # Gate 1: Absolute threshold
        if best_score < threshold:
            return None

        # Gate 2: Margin check against runner-up
        if len(scored) > 1:
            runner_up_score = scored[1][0]
            if (best_score - runner_up_score) < margin:
                # Ambiguous match between top options — decline to avoid guessing
                return None

        result = dict(best_entry)
        result["score"] = best_score
        return result

    def get_status(self) -> Dict[str, Any]:
        """Diagnostics for /api/status endpoint."""
        return {
            "indexed_entries": len(self.entries),
            "ready": self.is_ready,
            "cached": self.cache_loaded,
            "provider": self.provider.provider_name
        }


# Global singleton instance
_ANSWER_INDEX_INSTANCE: Optional[AnswerIndex] = None

def get_answer_index(provider: Optional[BaseEmbedProvider] = None) -> AnswerIndex:
    global _ANSWER_INDEX_INSTANCE
    if _ANSWER_INDEX_INSTANCE is None:
        prov = provider or get_semantic_router().provider
        _ANSWER_INDEX_INSTANCE = AnswerIndex(provider=prov)
        _ANSWER_INDEX_INSTANCE.load_or_build()
    return _ANSWER_INDEX_INSTANCE


def semantic_faq_answer(query: str, threshold: float = DEFAULT_RETRIEVAL_THRESHOLD, margin: float = DEFAULT_RETRIEVAL_MARGIN) -> Optional[str]:
    """
    Convenience lookup function for main.py. Returns substantive answer string or None.
    """
    index = get_answer_index()
    if not index.is_ready:
        return None
    res = index.retrieve(query, threshold=threshold, margin=margin)
    if res and res.get("answer"):
        return res["answer"]
    return None
