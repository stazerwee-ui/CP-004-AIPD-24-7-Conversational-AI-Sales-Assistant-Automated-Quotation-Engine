# What You Will Like About Feature 4: The 24/7 Conversational AI Chatbot (Hannah)

**Project CP-004 · Solace Dignity Care Portal**  
*Prototype Version: 18 August 2026*  
*Module Focus: Feature 4 — Dual-Engine 24/7 AI Chatbot (Hannah), Intelligent Query Answering, Semantic Extraction & Real-Time Cross-Screen State Synchronization.*

---

## Executive Summary: Why Feature 4 Stands Out

In high-stress, emotionally vulnerable moments—often occurring at 2:00 or 3:00 AM—families need immediate, accurate, and empathetic guidance. **Feature 4 (Hannah 24/7 Chatbot)** is not just a standard canned-response chatbot; it is a **deeply integrated, dual-engine bereavement intelligence platform** that combines conversational empathy with deterministic business precision.

Below is a detailed breakdown of the key capabilities, thoughtful design choices, and technical strengths you will love about Feature 4.

---

## 1. Zero-Hallucination Deterministic Price Arithmetic Engine

> **The Problem with Standard AI:** LLMs frequently make arithmetic mistakes, miscalculate taxes, or invent non-existent package discounts when answering pricing inquiries.

* **Exact Real-Time Computation:** When asked questions like *"How much is the Standard package with an Oak casket upgrade and 5 days wake?"*, Hannah routes the math through `answer_price_question()` in [main.py](file:///d:/Zach-Life@ITE02/AIPD_2026/AIPD_submissions/AIPD_work/18AugustPrototype/codes17aug2026/main.py).
* **Deterministic Itemized Math:** It calculates base package fees ($3,200), casket differential (+$1,200), extra wake duration days (+$800), and applies Singapore’s exact 9% GST with half-up rounding (`js_round()`).
* **Legally Consistent Quotes:** Every figure provided in chat matches the visual Planner, the pricing bar, and the e-Sign PDF contract to the exact cent.

---

## 2. Multi-Dataset RAG Deep Domain Knowledge (9 Integrated Knowledge Sources)

Hannah has instant, curated domain mastery across **9 specialized datasets** compiled via `build_knowledge_chunks()`:

1. **Funeral Packages & Rules (`funeral_package_rules.json` & `dataset.json`):** Direct Cremation ($1,500), Standard ($3,200), Deluxe ($4,500), and Premium Heritage ($6,800).
2. **Singapore Government & Statutory Procedures (`sg_government_legal_procedures.json`):** Digital Death Certificate issuance via *My Legacy*, Certificate of Cause of Death (CCOD), NEA Mandai Crematorium bookings, Choa Chu Kang 15-year burial crypt regulations, and Town Council HDB void deck permit processes.
3. **Emergency & Death Procedures (`death_emergency_procedures.json`):** Protocol for deaths occurring at home, hospitals, hospices, overseas repatriation, or unnatural deaths requiring Police & Forensic Medicine Division (FMD) coroner autopsies.
4. **Ash & Post-Funeral Final Disposition (`ash_final_disposal.json`):** Inland Ash Scattering at Garden of Peace (Choa Chu Kang) / Garden of Serenity (Mandai), sea burial coordinates, columbarium niche selection, and keepsake bio-urns.
5. **Multi-Faith & Cultural Rites (`religious_cultural_funeral_data.json`):** Nuanced practices across Buddhist (3 Monks chanting), Taoist (dialect rites: Hokkien, Teochew, Cantonese), Christian, Catholic, Soka Gakkai, Hindu, and Secular/Free Thinker arrangements.
6. **Company Policies & Fair Practices (`company_policies.json`):** 48-hour cooling-off periods, cancellation refund tiers, and 0% interest installment plans.
7. **Transparent Price Benchmarks (`industry_price_benchmarks.json`):** Comparing Solace prices against 2026 Singapore market averages, proactively highlighting hidden industry fees to avoid.
8. **Customer Testimonials (`customer_testimonials.json`):** Verified community reviews categorized by faith and tier.
9. **Service Standards (`service_standards.json`):** On-site Funeral Butler support standards, response time guarantees, and transport protocols.

---

## 3. Real-Time Cross-Screen State Synchronization

Unlike disconnected bots that live in a siloed corner widget, Hannah is **bidirectionally wired to the entire portal**:

```
User types in Chat: "We'd like the Oak casket and a 5-Day wake"
                             │
                             ▼
              FastAPI Semantic Entity Extraction
                             │
                             ▼
         Updates JSON Payload { casket: "oak", wakeDuration: "5day" }
                             │
                             ▼
 ┌───────────────────────────┼───────────────────────────┐
 │                           │                           │
 ▼                           ▼                           ▼
Screen 4: Planner        Sticky Price Bar            Screen 5: PDF Quote
Auto-highlights          Recalculates 9% GST         Regenerates Live
Polished Oak Card        Subtotal: $5,200 + GST      Contract Breakdown
```

* **Zero Duplicate Entry:** What you choose in conversation is immediately reflected if you switch over to the visual Planner screen, and vice versa.
* **Optimistic UI:** Messages appear instantly while background validation and price recalculations execute smoothly.

---

## 4. Zero-Typing Interactive UX (Dynamic Quick Chips & Bubble Pills)

Grieving users are often mentally exhausted and do not want to type lengthy text on mobile keypads. Hannah solves this with intelligent UI components:

* **Bubble-Embedded Choice Pills (`getStepOptionsForMessage`):** When Hannah asks an intake question, tappable action pills dynamically render inside the chat bubble:
  * *Asking about religion?* One-tap chips for `Christian`, `Buddhist`, `Taoist`, `Catholic`, `Soka Gakkai`, `Secular`.
  * *Asking about caskets?* Chips for `Eco-Wood (Included)`, `Oak (+$1,200)`, `Teak (+$2,800)`.
  * *Asking about location?* Chips for `HDB Void Deck`, `Parlour`, `Private Residence`.
* **Persistent Input-Level Quick Chips:** Quick shortcuts for *"Speak to a consultant"*, *"Start Step-by-Step Setup"*, *"View Packages & Pricing"*, and *"Go to Planner"*.

---

## 5. Industry-Leading Multi-Turn Cumulative Crisis Interception (SOS 1767)

Safety in bereavement software is critical. Hannah features a **4-Tier Clinical Risk Scoring Engine** evaluated prior to any LLM generation:

* **Multi-Turn Cumulative Score Meter:** Rather than relying only on obvious single-word triggers like `"suicide"`, the backend tracks despair markers across history turns:
  * **Tier 1 (100 pts):** Explicit lethality triggers immediate bypass.
  * **Tier 2 (40 pts):** Reunion/passing over fantasies (*"can't wait to join him"*, *"won't be around much longer"*), burdensomeness (*"I'm just a burden to them"*).
  * **Tier 3 (25 pts):** Moderate despair (*"world has gone dark"*, *"pain is unbearable"*).
  * **Tier 4 (15 pts):** Depressive drift (*"what is the point of anything"*).
* **Threshold Trigger (≥ 70 pts):** If cumulative signs breach 70 points across multiple messages, Hannah immediately overrides standard intake:
  * Injects compassionate **SOS 1767** emergency protocol (Samaritans of Singapore Hotline `1767`, WhatsApp CareText `9151 1767`, Emergency `995`).
  * Freezes commercial intake and logs an urgent priority alert in `oncall_alerts.log`.

---

## 6. Singapore PDPA Compliance & Automatic PII Masking

* **Proactive Privacy Protection (`detect_and_mask_pii`):** Automatically detects Singapore NRIC/FIN formats (`S/T/F/G/M` + 7 digits + Letter) and credit card numbers entered into chat.
* **Masked Persistence:** Logs and storage mask sensitive digits (`S****567A`), gently reminding the user that identity verification happens securely with the Funeral Director in person.

---

## 7. Financial Hardship Detection & Social Safety Net Routing

* **Dignity For All:** If a family mentions financial distress (*"cannot afford"*, *"no money"*, *"poverty"*), Hannah does not push high-tier upsells.
* **Grant Assistance Guidance (`detect_financial_assistance_need`):** Directly provides information on **MSF ComCare Funeral Assistance Grants**, **CDC Crisis Grants**, **Solace Pro-Bono Care Foundation**, and 0% installment plans.

---

## 8. Multi-Faith Cultural & Taboo Cross-Checking

* **Culturally Sensitive Guidance (`detect_cultural_taboo_or_inquiry`):**
  * Advises on funeral dress codes (avoiding bright red/pink clothing unless attending a longevity celebration wake for elders aged >80/90).
  * Prevents inter-faith conflicts (e.g. joss paper burning restrictions within church parlours).
  * Outlines catering customs (e.g. Buddhist vegetarian requirements).

---

## 9. Conversational Memory & State Recall

* **Active Recall:** Families can ask context queries at any point during a 20-minute interaction:
  * *"What was the deceased's name I gave you earlier?"* → Returns exact recorded name.
  * *"Can you summarize what we've chosen so far?"* → Returns a structured bulleted summary of package, casket, religion, wake location, and estimated price.
* **Deterministic Retrieval:** Extracted directly from backend session memory rather than unreliable LLM generation.

---

## 10. Robust Defense: Anti-Jailbreak, False Premise & Contradiction Resolution

* **Anti-Prompt Jailbreak Shield (`is_prompt_attack`):** Resists prompt leaks, persona override attempts, and malicious injections.
* **False Premise Rebuttal:** If a user claims *"Your colleague said I have a 50% discount code"*, Hannah politely corrects the premise before offering a human consultant, preventing misleading commitments.
* **Conflict Detection:** If a user requests contradictory options (e.g., *"Direct cremation with 3 days void deck chanting"*), Hannah explains the conflict gently and offers clear alternatives (Direct Cremation vs. Standard 3-Day Wake).

---

## 11. High-Stakes Escalation & One-Tap Human Handoff

* **Clear Boundary Control (`question_is_high_stakes`):** High-stakes legal/regulatory topics (probate, letters of administration, CPF bereavement distribution, coroner disputes) are intercepted to prevent hallucinated legal advice.
* **Frictionless Handoff:** Instantly offers to connect with a senior Funeral Consultant without requiring the user to argue with the bot.

---

## 12. Dual-Engine Architecture & 100% Offline Reliability

| Status Indicator | Engine State | Behavior |
|---|---|---|
| 🟢 **AI ONLINE** | Local Ollama LLM + RAG Active | Generates fluid, highly contextual natural language responses. |
| ⚪ **OFFLINE MODE** | Ollama Offline / Fallback Ladder | 100% deterministic rules & keyword engine take over instantly with zero downtime. |
| 🔴 **NO BACKEND** | Server Unreachable | UI displays clear reconnection helper. |

* **Zero-Crash Guarantee:** Even if the local LLM is powered off or crashes mid-conversation, the deterministic ladder answers questions and advances guided intake without dropping a single message.

---

## Summary Matrix: What Makes Feature 4 Exceptional

| Dimension | Standard Generic Chatbot | Solace Feature 4 (Hannah 24/7) |
|---|---|---|
| **Price Calculations** | Hallucinates numbers, estimates wrong taxes | **Exact deterministic engine with 9% GST breakdown** |
| **Domain Knowledge** | Generic internet scrapings | **9 verified Singapore funeral datasets & statutory rules** |
| **Portal Integration** | Isolated floating box | **Real-time multi-screen sync (Planner, Math, PDF, Lead DB)** |
| **Mobile Interaction** | Requires continuous typing | **Dynamic one-tap bubble chips for every intake step** |
| **Crisis Safety** | Keyword-only or none | **4-Tier cumulative multi-turn risk score + SOS 1767 priority intercept** |
| **Data Privacy** | Raw logging | **Automatic Singapore NRIC/FIN & PII masking** |
| **Social Support** | Ignores hardship | **MSF ComCare grants & pro-bono routing** |
| **Cultural Awareness** | Western-centric defaults | **Deep multi-faith, dialect, and taboo cross-checking** |
| **Reliability** | Fails if API drops | **Dual-engine with 100% offline fallback ladder** |

---