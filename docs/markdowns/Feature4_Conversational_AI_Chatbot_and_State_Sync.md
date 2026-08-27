# Feature 4 — AI Conversational Assistant & State Synchronization Engine

**Solace Dignity Care Portal · Project CP-004**  
*Comprehensive Technical Guide: Dual-Engine Backend Architecture, Conversational Theory, and Code-by-Code Breakdown.*

---

## 1. Executive Summary & Theory

### The Core Problem in Conversational AI
When building an AI chatbot for high-stakes, emotionally sensitive domains like bereavement care, relying purely on a generative Large Language Model (LLM) creates severe risks:
1. **Hallucination of Pricing & Policies**: Generative models can invent pricing tiers, promise unauthorized discounts, or miscalculate GST.
2. **Conversation Drift & Step Amnesia**: In multi-step intake flows, pure LLMs easily lose track of required steps, skip questions, or ask multiple conflicting questions at once.
3. **Safety & Compliance Failures**: LLMs can be tricked via prompt injections or fail to respond appropriately to mental health crises and legal emergencies.

Conversely, a **purely rule-based chatbot** feels robotic, cannot summarize complex comparisons, and frustrates families who phrase answers naturally or ask side questions mid-intake.

---

### The Dual-Engine Hybrid Solution

To solve this, Feature 4 uses a **Dual-Engine Architecture**:
* **The Deterministic Backbone (Python)**: Controls the strict 17-step intake ladder, manages active state transitions, computes price arithmetic, enforces legal/safety guardrails, and guarantees offline zero-downtime reliability via a deterministic fallback ladder.
* **The Intelligent Synthesizer (Local Ollama LLM)**: Acts as a compassionate, empathetic interface. When supplied with exact ground-truth catalog chunks (including 9 RAG knowledge sources and company background from `dataset.json`), Ollama summarizes comparisons logically and explains nuances without data-dumping or hallucinating numbers.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          USER MESSAGE / UI ACTION                               │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: SAFETY & PROTOCOL GUARDS (Python)                    │
│  - PDPA / NRIC Masking        - Crisis Risk Meter (SOS 1767)                    │
│  - Anti-Jailbreak Defense     - Management Grievance Escalation                 │
│  - MSF ComCare Safety Net     - Religious & Cultural Taboo Checks               │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                PHASE 2: THREE-WAY INTENT & SELECTION RESOLVER                   │
│                                                                                 │
│  ┌─────────────────────────┬─────────────────────────┬───────────────────────┐  │
│  │   EXPLICIT SELECTION    │   QUALIFIED SELECTION   │  PURE INQUIRY/ADVICE  │  │
│  │ (Choice without query)  │   (Choice + Question)   │  (Comparison / Query) │  │
│  ├─────────────────────────┼─────────────────────────┼───────────────────────┤  │
│  │ Commit state instantly  │ Commit state choice     │ Freeze state mutation │  │
│  │ Advance next step       │ Ollama answers query    │ Ollama answers query  │  │
│  │ (Deterministic Python)  │ Bridge to NEXT step     │ Bridge to SAME step   │  │
│  └─────────────────────────┴─────────────────────────┴───────────────────────┘  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│               PHASE 3: GROUND-TRUTH INJECTION & OLLAMA SYNTHESIS                │
│  - Retrieve relevant catalog comparison & FAQ grounding chunks                  │
│  - Grounding from dataset.json (Prices, Inclusions, Founders: Roland/Jenny Tay) │
│  - System Prompt instructs Ollama to synthesize concisely without follow-ups    │
│  - Assemble smooth single-question output bridge                                │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│               PHASE 4: CROSS-SCREEN STATE SYNCHRONIZATION (app.js)              │
│  - Update client-side `state` dictionary                                        │
│  - Highlight chosen options on Screen 4 (Planner Selectors)                     │
│  - Trigger `/api/calculate` for real-time subtotal + 9% GST updates             │
│  - Sync Family Hub coordination cards & PDF Quote Generation                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Theoretical Pillars of the Architecture

### Pillar 1: Three-Way Turn Intent Resolution & Pure Inquiry Guards
Instead of a naive binary check (*"Is this a question or an answer?"*), user messages are classified into three distinct categories:
1. **Explicit Selection**: User taps a choice button or makes an unambiguous choice (*"Deluxe tier"*, *"set up installment"*).  
   *Behavior*: State is committed immediately; Python advances to the next step deterministically.
2. **Qualified Selection**: User selects an option while asking a condition or question in the same breath (*"We'll choose Deluxe, is the Mercedes hearse included?"*).  
   *Behavior*: The choice (`tier = "deluxe"`) is committed to state; Ollama answers the hearse question; the engine smoothly bridges forward to the next step (`casket`).
3. **Pure Inquiry / Hesitation / Option Inquiry**: User asks a comparative question, side question about an option, or expresses uncertainty (*"What's one of your interest-free installment plans?"*, *"What's the difference between standard and deluxe?"*, or *"Not sure, what do most families do?"*).  
   *Behavior*: **State is kept strictly read-only (guarded by `is_pure_inquiry`)**; Ollama synthesizes the answer from ground-truth data; the current step question is smoothly re-prompted without jumping ahead.

---

### Pillar 2: Prompt-Level Single-Question Governance
When an LLM answers a side inquiry, it often naturally attempts to close with its own question (*"Would you like me to book this for you?"*). If the backend blindly appends the scripted intake question, the family receives **two competing questions in one message**.

*Solution*: Rather than using fragile regex trimming, we instruct Ollama at the prompt level:  
`"Do NOT generate your own follow-up questions or next-step suggestions at the end of your reply, as the intake guidance system will append the proper step prompt."`  
The backend then bridges the explanation to the next step smoothly.

---

### Pillar 3: Cumulative Multi-Turn Crisis Risk Meter (SOS 1767)
Grieving individuals rarely use direct keywords like *"suicide"*. They often express distress subtly across multiple turns:
* Turn 1: *"I feel like a burden to my family."* (40 points)
* Turn 2: *"I won't be around much longer anyway."* (40 points)

The crisis scoring engine evaluates a **decaying cumulative sum across conversation history** ($Score = Score_{current} + 0.85 \times Score_{history}$). Once the threshold ($\ge 70$ pts) is breached, all intake is suspended, and the verified Singapore SOS 1767 protocol is delivered immediately.

---

## 3. Code-by-Code Backend Deep Dive

Let us trace the key functions in [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py) step by step.

---

### Step 1: Input Sanitization & Privacy (PDPA Guard)

```python
# main.py - Input Sanitization & Singapore NRIC Masking
def sanitize_user_input(raw_msg: str, max_len: int = 600) -> str:
    """Protects server & LLM buffer from oversized payloads, spam, and DoS."""
    if not raw_msg:
        return ""
    text = raw_msg.strip()[:max_len]
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def detect_and_mask_pii(message: str) -> tuple:
    """
    Singapore PDPA compliance guard.
    Detects Singapore NRIC/FIN patterns (S/T/F/G/M + 7 digits + Letter) and Credit Cards.
    """
    msg = message or ""
    nric_pattern = r"\b([STFGMstfgm]\d{7}[A-Za-z])\b"
    card_pattern = r"\b(?:\d{4}[ -]?){3}\d{4}\b"
    
    has_nric = bool(re.search(nric_pattern, msg))
    has_card = bool(re.search(card_pattern, msg))
    
    if not (has_nric or has_card):
        return False, "", msg
    
    # Mask NRIC for server logs (e.g. S1234567A -> S****567A)
    def mask_nric(match):
        val = match.group(1).upper()
        return f"{val[0]}****{val[5:]}"
    
    masked = re.sub(nric_pattern, mask_nric, msg)
    masked = re.sub(card_pattern, "****-****-****-****", masked)
    
    reply = (
        "For your security and Singapore PDPA privacy compliance, please avoid sharing NRIC numbers "
        "or payment card details directly in this chat. Our funeral director will verify official "
        "documents securely in person."
    )
    return True, reply, masked
```

**Why this code matters**:
1. `sanitize_user_input()` prevents buffer flooding and DoS payload injection.
2. `detect_and_mask_pii()` ensures full Singapore Personal Data Protection Act (PDPA) compliance by preventing sensitive personal identity numbers from leaking into LLM contexts or logs.

---

### Step 2: Three-Way Turn Intent & Selection Classification

Located inside `@app.post("/api/chat")` in [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py):

```python
# main.py - Turn Intent Resolution
state_before = extract_intake_state(request.history, "")
question_before, field_before = determine_next_question(state_before, request.history)
updates_before = extract_state_from_history(request.history, "")
in_setup_mode = is_in_step_by_step_mode(request.history) or kw(msg_lower, "start step-by-step setup", "start guided setup", "begin setup")

is_comparison = kw(msg_lower, "vs", "versus", "difference", "differences",
                   "compare", "comparison", "better", "which one")

has_hesitation = kw(msg_lower, "not sure", "dont know", "don't know", "haven't decided", 
                    "havent decided", "what do most", "what is popular", "which is better",
                    "what do you suggest", "what do you recommend", "can you recommend", 
                    "help me decide", "it depends", "not decided", "unsure")

is_question_or_interruption = (
    is_clearly_a_question(msg_lower) 
    or is_comparison 
    or is_policy_question(msg_lower)
    or is_price_arithmetic_question(request.message)
)

updated_fields = [
    f for f in updates 
    if updates.get(f) not in (None, "") and updates.get(f) != updates_before.get(f)
]
field_updated = len(updated_fields) > 0

# Precedence Hierarchy
if request.is_option_selection:
    turn_intent = "EXPLICIT_SELECTION"
elif is_comparison:
    turn_intent = "PURE_INQUIRY"
elif has_hesitation:
    turn_intent = "HESITATION"
elif field_updated and is_question_or_interruption:
    turn_intent = "QUALIFIED_SELECTION"
elif field_updated:
    turn_intent = "EXPLICIT_SELECTION"
elif is_question_or_interruption:
    turn_intent = "PURE_INQUIRY"
elif in_setup_mode and any(updates.get(f) != updates_before.get(f) for f in updates if updates.get(f) not in (None, "")):
    turn_intent = "EXPLICIT_SELECTION"
else:
    turn_intent = "GENERAL_CONVERSATION"

answering_step = turn_intent in ["EXPLICIT_SELECTION", "QUALIFIED_SELECTION"]
```

**Why this code matters**:
* `is_comparison` takes precedence over `field_updated`. If a user asks *"what's the difference between standard and deluxe"*, both options appear in the message, but `is_comparison` ensures the engine treats it as a `PURE_INQUIRY` rather than prematurely selecting Deluxe.
* `QUALIFIED_SELECTION` accurately flags when a choice was made alongside a question.

---

### Step 3: Ground-Truth Context Injection for Ollama

```python
# main.py - Context Grounding for Ollama
if model_name:
    try:
        search_query = request.message
        catalog_context = build_catalog_prompt_context(search_query)

        # Retrieve exact catalog grounding data
        comp_grounding = answer_comparison_question(request.message)
        cat_grounding = answer_catalog_question(request.message)
        gen_grounding = handle_general_or_off_topic_message(request.message)
        wake_days = 5 if state.get("wakeDuration") == "5day" else 3
        price_grounding = answer_price_question(request.message, wake_days)
        
        extra_context = []
        if comp_grounding:
            extra_context.append(f"EXACT CATALOG COMPARISON GROUNDING DATA:\n{comp_grounding}")
        if cat_grounding and is_substantive_answer(cat_grounding):
            extra_context.append(f"EXACT CATALOG FAQ GROUNDING DATA:\n{cat_grounding}")
        if gen_grounding and is_substantive_answer(gen_grounding):
            extra_context.append(f"EXACT GENERAL FAQ GROUNDING DATA:\n{gen_grounding}")
        if price_grounding:
            extra_context.append(f"EXACT PRICING CALCULATION GROUNDING DATA:\n{price_grounding}")
            
        if extra_context:
            catalog_context += "\n\n" + "\n\n".join(extra_context)
```

**Why this code matters**:
* Rather than trusting the LLM to remember numbers from weights, exact data points from `dataset.json` (such as prices, inclusions, and comparisons) are injected directly into `catalog_context`.
* Ollama uses these exact data points to synthesize natural, empathetic summaries.

---

### Step 4: System Prompt & Output Bridge Assembly

```python
# main.py - System Instruction & Output Bridge
if in_setup_mode:
    system_instruction = (
        f"{SYSTEM_PROMPT}\n\n{catalog_context}\n\n"
        f"The family is currently in our 5-step guided intake.\n"
        f"1. Answer their specific question, comparison, or inquiry directly, politely, concisely, and with logical smartness using the exact catalog data provided above.\n"
        f"2. If comparing options, explain key distinctions smoothly (pricing, inclusions, casket, hearse, suitability) rather than dumping raw bullet lists.\n"
        f"3. If the user is asking for advice or expressing uncertainty, provide compassionate, practical recommendations based on common Singapore practices.\n"
        f"4. If the question is completely unrelated to funeral care, start with: 'While that is outside our usual funeral care, [answer]'.\n"
        f"5. Never speculate, fabricate, or make up assumptions about the deceased.\n"
        f"6. IMPORTANT: Do NOT generate your own follow-up questions or closing next-step suggestions, as the intake guidance system will supply the proper step prompt."
    )

# ... LLM generates ollama_reply ...

# Assembly Bridge
if in_setup_mode:
    if turn_intent == "QUALIFIED_SELECTION":
        chosen_val = updates.get(field_before, "")
        chosen_label = str(chosen_val).replace("_", " ").title()
        prefix = f"I have noted your choice of {chosen_label}. " if chosen_label else ""
        target_q = next_question
        separator = "\n\n" if "\n" in ollama_reply else " "
        if target_q and target_q.lower() not in ollama_reply.lower():
            ollama_reply = f"{prefix}{ollama_reply}{separator}{target_q}"
    elif turn_intent in ["PURE_INQUIRY", "HESITATION"]:
        target_q = question_before or next_question or deterministic_reply
        separator = "\n\n" if "\n" in ollama_reply else " "
        if target_q and target_q.lower() not in ollama_reply.lower():
            ollama_reply = f"{ollama_reply}{separator}{target_q}"

effective_updates = updates if answering_step else updates_before
return ChatResponse(response=ollama_reply, updates=effective_updates)
```

**Why this code matters**:
* For a **Qualified Selection**, the user receives immediate confirmation of their choice, the answer to their side question, and the next step question.
* For a **Pure Inquiry**, the user receives a clean, smart comparison summary, and the current step question is smoothly re-prompted without dirtying active state (`effective_updates = updates_before`).

---

### Step 5: Client-Side Cross-Screen State Synchronization ([`app.js`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/app.js))

When the backend returns `ChatResponse(response=..., updates={...})`:

```javascript
// app.js - Processing response and synchronizing UI
async function sendFreeChatMessage() {
  const userText = chatInput.value.trim();
  // ... optimistic bubble render ...

  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userText, history: chatHistory })
  });
  const data = await res.json();

  // 1. Sync backend updates into client state
  if (data.updates) {
    Object.keys(data.updates).forEach(key => {
      state[key] = data.updates[key];
    });
  }

  // 2. Re-render Planner Screen selectors with new selections
  renderPlannerSelectors();

  // 3. Trigger recalculation of subtotal + 9% GST
  recalculatePlannerPrice();

  // 4. Update Family Hub coordination card
  renderCoordinationSummary();

  // 5. Render AI response bubble with dynamic quick-reply action chips
  appendBubble(data.response, 'assistant');
  updateStepOptionButtons(data.response);
}
```

**Why this code matters**:
* Natural language typed in the chat window instantly updates selectors in Screen 4 (Planner), recalculates mathematical pricing tables, and synchronizes with PDF quote generators in real time.

---

## 4. Key File & Component Reference

| Module | Primary File | Key Functions / Definitions |
|---|---|---|
| **17-Step Intake State Machine** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L4245-L4380) | `INTAKE_STEPS`, `determine_next_question()`, `extract_intake_state()` |
| **Natural Language Entity Extractor** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L543-L840) | `extract_state_from_history()`, `is_pure_inquiry`, `kw()` |
| **Three-Way Turn Intent Resolver** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L3200-L3255) | `turn_intent`, `is_comparison`, `has_hesitation`, `is_question_or_interruption` |
| **RAG Catalog Retrieval & Grounding** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L1435-L1620) | `build_knowledge_chunks()`, `retrieve_knowledge()`, `build_catalog_prompt_context()` |
| **Deterministic Fallback Ladder** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L4920-L5120) | `generate_fallback_response()`, `handle_general_or_off_topic_message()` |
| **Deterministic Price Math** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L2500-L2620) | `answer_price_question()`, `find_priced_items()` |
| **Multi-Turn Crisis Risk Meter** | [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L3030-L3150) | `calculate_crisis_risk_score()`, `CRISIS_REPLY` |
| **Client Dispatch & State Sync** | [`app.js`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/app.js#L980-L1120) | `sendFreeChatMessage()`, `renderPlannerSelectors()`, `recalculatePlannerPrice()` |

---

## 5. The Deterministic Fallback Ladder (Offline Zero-Downtime Resilience)

When the local Ollama LLM is unavailable or offline, the engine activates `generate_fallback_response()` in [`main.py`](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L4920-L5120), executing through an 8-tier hierarchy:

1. **Safety & Crisis Interception**: SOS 1767 emergency protocols and PDPA masking take top priority.
2. **Deterministic Price Calculator**: Evaluates arithmetic expressions (e.g. *"Standard + Oak + 5 days"* = $5,200 + 9% GST).
3. **Intent-Mapped FAQs & 5W1H Procedures**: Pulls exact answers from `intent_mapped_faqs.json` and `step_by_step_procedures.json`.
4. **Package & Option Comparisons**: Generates side-by-side comparison tables from catalog data.
5. **Company History & Founders**: Grounded in `dataset.json` (Roland Tay & Jenny Tay, founded 1980).
6. **General Knowledge & Utilities**: Handles mathematical questions, basic small talk, and trivia without crashing.
7. **Hesitation & Uncertainty Support**: Provides sensible defaults and cultural guidance (e.g. suggesting Secular service when undecided on religion).
8. **Single-Question Step Bridge**: Automatically re-prompts the current step question to keep the family moving forward at their own pace.

---

## 6. Summary of Architectural Safeguards

1. **Zero Hallucinations on Calculations**: Math and pricing rules are strictly handled in Python using exact catalog rates.
2. **Zero Premature Step Advancements**: State mutations are frozen during inquiries and comparisons via `is_pure_inquiry`.
3. **Zero Double-Question Clashing**: Output governance prevents competing follow-up questions from the LLM.
4. **Zero-Downtime Guarantee**: If local Ollama is offline, the deterministic rule engine steps in instantly with zero downtime.
