# Feature 4 — 24/7 Conversational AI Chatbot, Step-by-Step Guided Intake & Real-Time State Synchronization

**Project CP-004 · Solace Dignity Care Portal**  
*Dual-Engine Conversational Assistant (Hannah 24/7), Natural Language Entity Extraction, 5W1H Procedure Grounding, and Real-Time Cross-Screen State Synchronization.*

---

## The one sentence to lead with

> Natural language text typed by a grieving family is converted in real time into verified structured data that synchronizes the entire application state—from live pricing calculations and visual planner selectors to PDF contract generation and on-call director dispatch.

That is the whole feature. Everything else is plumbing around it.

---

## Why this is harder than Feature 3

| | Feature 3 (Human Consultant Handoff) | Feature 4 (AI Chatbot & State Sync) |
|---|---|---|
| **Input Shape** | Structured modal form fields (name, phone, dropdown reason) | **Unstructured, noisy natural language** (voice-of-customer, slang, typos, grief venting) |
| **Data Processing** | Direct field copy from modal into ticket JSON | **Semantic entity extraction, keyword tokenization, and sequential intent parsing** |
| **System Intelligence** | Static routing state machine (`AI` → `HUMAN` → `CLOSED`) | **Hybrid Dual-Engine** (Local Ollama LLM + Deterministic Rule Fallback + RAG Catalog) |
| **State Synchronization** | Syncs conversation feed across 2 UI screens | **Multi-screen synchronization** (Chatbot ↔ Planner Selectors ↔ Math Engine ↔ Family Hub ↔ PDF Contract) |
| **Safety & Guardrails** | Human takeover on button click | **Autonomous Crisis Interception (SOS 1767), PDPA NRIC masking, anti-jailbreak, & conflict detection** |
| **Failure Tolerance** | Ticket stays in queue until picked up | **Zero-stall guarantee**: conversation must never crash, hallucinate numbers, or ask double questions |

**Feature 3 coordinates a handover between two humans. Feature 4 acts as an intelligent intermediary that translates unstructured human language into deterministic business rules, calculations, and active UI states.**

---

## The Dual-Engine Pipeline

```
[Family Types Message / Clicks Step Chip]
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Client-Side Intake & Optimistic UI (app.js)              │
│    - Renders user bubble immediately                        │
│    - Appends message to local chatHistory                   │
│    - Dispatches fetch POST to /api/chat                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Backend Priority 0: Safety & Privacy Layer (main.py)     │
│    - PDPA NRIC/FIN Masking (S****567A)                      │
│    - Cumulative Multi-Turn Crisis Risk Meter (SOS 1767)     │
│    - Anti-Prompt Jailbreak & False Premise Defenses         │
│    - MSF ComCare Social Safety Net & CASE Grievances        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Three-Way Intent & Selection Resolver (main.py)          │
│    - EXPLICIT_SELECTION : Commits choice, advances step     │
│    - QUALIFIED_SELECTION: Commits choice, answers side query│
│    - PURE_INQUIRY       : Freezes state, synthesizes summary│
│    - HESITATION         : Freezes state, gives cultural advice│
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 5W1H Step Procedure Context & Catalog RAG Injection      │
│    - Injects step_by_step_procedures.json (What/Why/How)    │
│    - Injects exact catalog pricing & inclusions             │
│    - Enforces step discipline rule (no jumping ahead)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Dual-Engine Generation & Single-Question Bridge          │
│    - Mode A: Ollama LLM with structured RAG grounding       │
│    - Mode B: 100% Deterministic Fallback Ladder (Offline)   │
│    - Single-Question Bridge: Appends exact pending prompt   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Response Payload Returned to Client                      │
│    { response: "...", updates: { tier: "deluxe", ... } }    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Cross-Screen State Synchronization (app.js)              │
│    - Updates browser `state` object                         │
│    - Screen 4: Highlights chosen cards in Planner UI        │
│    - Math Engine: Fires /api/calculate for new total + GST  │
│    - Screen 2: Updates Family Hub Coordination Card         │
│    - Screen 5: Updates e-Sign PDF Quote Table               │
└─────────────────────────────────────────────────────────────┘
```

---

## The three places data can be

| Where | What it is |
|---|---|
| **The family's browser** | `state`, `chatHistory`, and active DOM selectors in `app.js` |
| **The server** | `main.py` session state, 18 RAG knowledge datasets in `./data/`, and `leads.json` on disk |
| **The director's portal** | `consultant_requests.json` and `oncall_alerts.log` read by staff |

Data moves between them **only** by `fetch()`.

---

## Stop-by-Stop Data Flow Walkthrough

---

### Stop 1 — The family types a message or taps a chip
The user is at Step 1 (`deceasedName`) and types:
> **`"We'll choose the Deluxe tier, is the Mercedes hearse included?"`**

In [app.js](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/app.js#L988-L1015), `sendFreeChatMessage()` captures the text input, displays an optimistic user chat bubble, and appends the turn to local history:

```javascript
// app.js
appendBubble(userText, 'user');
chatHistory.push({ role: 'user', content: userText });
```

**Where is the data?** Only in Chrome's memory on the user's phone.

---

### Stop 2 — Leaving the phone
`sendFreeChatMessage()` fires an asynchronous `fetch()` POST request to the backend:

```javascript
// app.js
const res = await fetch(`${API_BASE}/api/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "We'll choose the Deluxe tier, is the Mercedes hearse included?",
    history: chatHistory,
    request_id: state.consultantRequestId
  })
});
```

**What `JSON.stringify` does:** Converts the JavaScript message and history objects into a JSON text payload.  
**Where does it go?** To the FastAPI application running in `main.py`.

---

### Stop 3 — Line 0 Priority: Safety & Privacy Layer
Before parsing steps or calling the LLM, the message passes through mandatory guardrails:

```python
# main.py
# 1. PDPA NRIC & Credit Card Masking
is_pii, pii_reply, sanitized_msg = detect_and_mask_pii(request.message)

# 2. Cumulative Multi-Turn Crisis Scoring
is_crisis, crisis_reply, score, reason = is_crisis_message(request.message, request.history)
if is_crisis:
    return ChatResponse(response=CRISIS_REPLY, updates=updates, needs_human=True, reason=reason)

# 3. Anti-Prompt Injection Defense
if is_prompt_attack(request.message):
    return ChatResponse(response=DEFENSE_REPLY, updates=updates)
```

**Why this code matters**: If a family expresses acute distress (score $\ge 70$ pts), the system immediately halts intake and serves the **SOS 1767** emergency protocol.

---

### Stop 4 — Three-Way Turn Intent Resolution
The engine analyzes the turn's intent and evaluates whether any intake fields were updated:

```python
# main.py
updated_fields = [
    f for f in updates 
    if updates.get(f) not in (None, "") and updates.get(f) != updates_before.get(f)
]
field_updated = len(updated_fields) > 0

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
else:
    turn_intent = "GENERAL_CONVERSATION"

answering_step = turn_intent in ["EXPLICIT_SELECTION", "QUALIFIED_SELECTION"]
```

**What happens here:**
* `is_comparison` is False (user is not asking "Standard vs Deluxe").
* `field_updated` is True (`tier` was set to `"deluxe"`).
* `is_question_or_interruption` is True (*"is the Mercedes hearse included?"*).
* `turn_intent` resolves to **`QUALIFIED_SELECTION`**.

---

### Stop 5 — Natural Language Entity Extractor & State Scoping
In [main.py](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L543-L820), `extract_state_from_history()` scans the conversation and extracts canonical catalog keys:

```python
# main.py
if kw(text_lower, "deluxe", "deluxe tier", "deluxe package", "dlx"):
    state["tier"] = "deluxe"
```

Because `turn_intent == "QUALIFIED_SELECTION"`, the engine commits `tier = "deluxe"` to active state, while leaving `deceasedName = None` intact.

---

### Stop 6 — 5W1H Step Procedure Guidance Retrieval
In [main.py](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/main.py#L1610-L1645), `get_step_procedure_context("deceasedName")` pulls structured 5W1H knowledge from [data/step_by_step_procedures.json](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/data/step_by_step_procedures.json):

```python
# main.py
active_step_field = field_before or pending_field
step_proc_context = get_step_procedure_context(active_step_field)
```

**What this produces for Ollama**:
```
ACTIVE INTAKE STEP #1: DEPARTED LOVED ONE'S LEGAL NAME (Field: 'deceasedName')
- Canonical Step Question: "May I know the name of your departed loved one?"
- What this step collects: Full legal name as per NRIC/Passport.
- Why this is required: Required by NEA & hospital mortuary release permits.
- CRITICAL STEP DISCIPLINE RULE: This is Step 1. If the family mentions a package or side question, answer their question directly, acknowledge any choice made, and prompt for the deceased loved one's name. Do NOT ask for Date of Birth or jump ahead.
```

---

### Stop 7 — Catalog Grounding & Ollama Generation
The backend combines the catalog context, procedure context, and conversation history into the system prompt:

```python
# main.py
system_instruction = (
    f"{SYSTEM_PROMPT}\n\n{catalog_context}\n\n"
    f"The family is currently in our guided step-by-step intake.\n"
    f"1. Answer their specific question using the exact catalog data provided.\n"
    f"2. CRITICAL STEP DISCIPLINE: Do NOT generate your own follow-up questions or ask questions for other intake steps. The intake guidance system will append the correct single question."
)
```

Ollama executes locally on `http://127.0.0.1:11434/api/chat` and generates:
> *"The Deluxe Dignity Service ($4,500) indeed includes an upgraded Mercedes-Benz black hearse for procession day. This upgraded hearse adds a touch of elegance to your farewell ceremony."*

---

### Stop 8 — Single-Question Bridge Assembly
Python takes Ollama's answer, formats an acknowledgment for the selected field, and appends the single canonical pending question:

```python
# main.py
chosen_labels = []
for f in updated_fields:
    v = updates.get(f)
    if f == "addons" and isinstance(v, dict):
        chosen_labels.extend([k.title() for k, enabled in v.items() if enabled])
    elif v:
        chosen_labels.append(str(v).replace("_", " ").title())

prefix = f"I have noted your choice of {', '.join(chosen_labels)}. " if chosen_labels else ""
target_q = next_question  # "May I know the name of your departed loved one?"

if target_q and target_q.lower() not in ollama_reply.lower():
    ollama_reply = f"{prefix}{ollama_reply} {target_q}"

return ChatResponse(response=ollama_reply, updates=updates)
```

---

### Stop 9 — Response Payload Returned to Browser
The browser receives the JSON response:

```json
{
  "response": "I have noted your choice of Deluxe. The Deluxe Dignity Service ($4,500) indeed includes an upgraded Mercedes-Benz black hearse for procession day. May I know the name of your departed loved one?",
  "updates": {
    "tier": "deluxe"
  },
  "needs_human": false
}
```

---

### Stop 10 — Real-Time Cross-Screen State Synchronization
In [app.js](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/app.js#L1077-L1110), the client processes the response:

```javascript
// app.js
// 1. Sync backend updates into client state
if (data.updates) {
  Object.keys(data.updates).forEach(key => {
    state[key] = data.updates[key];
  });
}

// 2. Re-render Planner Screen selectors (Highlights Deluxe Card)
renderPlannerSelectors();

// 3. Recalculate Subtotal + 9% GST
recalculatePlannerPrice();

// 4. Update Family Hub coordination card
renderCoordinationSummary();

// 5. Append assistant bubble to chat
appendBubble(data.response, 'assistant');
```

**Where is the data now?**  
1. `state.tier` is `'deluxe'` in browser memory.
2. Screen 4 (Planner) automatically highlights the **Deluxe Dignity Service ($4,500)** card.
3. Sticky Price Bar recalculates to **$4,500 + 9% GST = $4,905.00**.
4. The conversation remains perfectly queued on Step 1 (Deceased Name).

---

## The 5 Design Decisions That Make This Work

### Decision 1: Separation of Truth
* **Python manages**: Numbers, prices, GST math, step ordering, safety gates, and state transitions.
* **Ollama manages**: Tone, empathy, phrasing, and natural language synthesis.
* *Why?* Language models hallucinate math and skip steps. Python is deterministic and cannot make math mistakes.

### Decision 2: Three-Way Turn Intent Resolution
* A message is not simply a "question" or an "answer". It can be an **Explicit Selection**, a **Qualified Selection (Choice + Question)**, a **Pure Inquiry**, or a **Hesitation**.
* *Why?* Treating a comparative inquiry (*"Standard vs Deluxe"*) as a selection pollutes the state; treating a qualified choice (*"We choose Deluxe, is hearse included?"*) as a pure question loses the user's choice.

### Decision 3: 5W1H Procedure Knowledge Injection
* The dedicated [data/step_by_step_procedures.json](file:///c:/Users/staze/Desktop/AIPD/codes17aug2026/codes17aug2026/data/step_by_step_procedures.json) provides What, Why, How, When, and Where for all 17 intake steps.
* *Why?* Ollama can answer procedural inquiries (e.g. *"Why do you need the death certificate now?"*) accurately from Singapore NEA rules rather than guessing.

### Decision 4: Single-Question Output Governance
* Ollama is strictly forbidden from appending its own closing questions during guided intake. Python supplies the single canonical step question.
* *Why?* Eliminates double-question collisions where the AI asks two different questions in the same speech bubble.

### Decision 5: 100% Offline Fallback Ladder
* If local Ollama goes offline or encounters a timeout, the deterministic rule engine steps in instantly with zero dropped messages.
* *Why?* In bereavement care, a system crash or infinite loading spinner is completely unacceptable.

---

## Questions an Evaluator / Examiner Might Ask

### 1. "What happens if the family asks a question completely unrelated to funerals?"
> The bot recognizes off-topic queries and opens with: *"While that is outside our usual funeral care, [answers concisely]"*, before smoothly returning to the pending intake step.

### 2. "How does the chatbot prevent pricing hallucinations?"
> Pricing inquiries are intercepted and computed by `answer_price_question()` in Python. Base package rates, casket upgrades, wake days, and Singapore's 9% GST are calculated deterministically with half-up rounding.

### 3. "What happens if a user expresses suicidal thoughts?"
> The 4-Tier Cumulative Crisis Risk Meter flags the message (score $\ge 70$ pts), bypasses all commercial intake immediately, and outputs the **SOS 1767** emergency protocol (Hotline `1767`, WhatsApp `9151 1767`, Ambulance `995`).

### 4. "What happens if a user wants to change an earlier answer?"
> The user can say *"Go back to step 1"* or *"Change the casket to Teak"*. `parse_navigation_request()` in Python rolls back the state deterministically and re-prompts the target step.
