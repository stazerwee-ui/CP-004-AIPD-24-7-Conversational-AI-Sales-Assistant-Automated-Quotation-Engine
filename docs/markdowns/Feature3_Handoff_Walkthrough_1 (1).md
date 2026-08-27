# Feature 3 — Human Consultant Handoff (AI → Human Takeover)

Project CP-004 · Klass Dignity Care
Every code block below is taken from the running project — `main.py` and `app.js`.

---

## The one sentence to lead with

> One conversation, two possible authors. The backend decides which one is allowed to speak.

That is the whole feature. Everything else is plumbing around it.

---

## Why this is harder than Features 1 and 2

| | Feature 1 & 2 | Feature 3 |
|---|---|---|
| Users at once | One | Two — family and director |
| Server memory | None needed | A ticket that outlives the page |
| Refresh the page | Behaves identically | Must resume the same conversation |
| Failure mode | Wrong number on screen | AI and human both replying at once |

Features 1 and 2 **compute an answer**. Feature 3 has to **remember a decision**.

A pricing request is stateless: send selections, get a total, done. A handoff is not.
The server must know that Marcus took over this conversation four minutes ago, so
that when the family types again, the message goes to Marcus and *not* to the LLM.

---

## Step 1 — The button: a permanent route to a person

The family never has to argue with the assistant to reach a human. A
**"Speak to a consultant"** chip sits permanently above the chat input, alongside
the other quick actions.

```javascript
{
  label: 'Speak to a consultant',
  action: openConsultantModal,
  accent: true,          // copper outline, visually distinct
  hideInHumanMode: true  // hidden once a consultant has taken over
}
```

Two design decisions in those four lines:

- **`accent: true`** — copper outline instead of the grey of the other chips, so the
  route to a human is visually distinct without shouting.
- **`hideInHumanMode: true`** — once a consultant is in the conversation, offering to
  fetch one makes no sense, so the chip removes itself.

The chip row is rebuilt on every assistant message, so this is not static markup —
it is an option in a list that the renderer reads each time:

```javascript
function renderQuickChips() {
  const inHumanMode = state.conversationMode === 'HUMAN';

  getInitialDefaultOptions().forEach(opt => {
    if (opt.hideInHumanMode && inHumanMode) return;

    const btn = document.createElement('button');
    btn.className = opt.accent ? CHIP_ACCENT_CLASS : CHIP_DEFAULT_CLASS;
    btn.innerHTML = opt.label;
    btn.addEventListener('click', () => {
      if (opt.action) opt.action();
      else if (opt.text) { chatTextInput.value = opt.text; sendFreeChatMessage(); }
    });
    quickContainer.appendChild(btn);
  });
}
```

---

## Step 2 — The request form

Clicking the chip opens a short form. It asks for only what a consultant needs to
call back — not a full intake, because the family has already answered those
questions.

```
Name *                     Preferred contact method
Phone number *             Preferred contact time
Email (optional)           Reason for contacting
```

**The form pre-fills what it already knows.** The login screen accepts a phone
number *or* an email, so the value is routed to the matching field rather than
assumed to be a phone number:

```javascript
function openConsultantModal() {
  if (state.user && state.user.name) {
    nameInput.value = state.user.name;
  }

  if (state.user && state.user.contact) {
    const contact = String(state.user.contact).trim();
    const looksLikeEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact);

    if (looksLikeEmail) {
      if (emailInput && !emailInput.value) emailInput.value = contact;
    } else if (phoneInput && !phoneInput.value) {
      phoneInput.value = contact;
    }
  }

  consultantModal.classList.remove('opacity-0', 'pointer-events-none');
}
```

On submit, the whole conversation and the intake state are sent along with the form:

```javascript
consultantRequestForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const resp = await fetch(`${API_BASE}/api/consultant-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_name: name,
      phone: phone,
      email: email,
      preferred_contact_method: method,
      preferred_contact_time: time,
      reason: reason,
      history: chatHistory,      // the full conversation so far
      intake_state: state        // religion, tier, casket, total...
    })
  });

  const data = await resp.json();
  state.consultantRequestId = data.request_id;
  closeConsultantModal();

  appendBubble(`Your request for a Funeral Consultant has been logged successfully
    (Ticket ID: ${data.request_id}). Our on-call director will reach out to you
    via ${method}.`, 'ai');

  // Begin listening for a consultant taking over
  startCustomerPolling();
});
```

**`history` and `intake_state` are the important fields.** Everything else is contact
details. Those two are what let the consultant open the ticket already knowing the
arrangement — covered in the next step.

Note the last line: submitting the form **starts the polling loop**. From this moment
the family's phone is checking every two seconds whether a human has joined.

---

## Step 3 — Ticket creation

The family accepts, and the backend writes a request with a generated briefing.

```python
def create_consultant_request(payload: ConsultantRequestCreate):
    requests_list = load_consultant_requests()

    rand_seq = random.randint(100, 999)
    now_dt = datetime.now()
    ticket_id = f"FR-2026-{now_dt.strftime('%m%d%H')}{rand_seq}"
```

The briefing is built from the intake state, not written by the model:

```python
def generate_ai_executive_summary(intake, history, reason) -> str:
    # Line 1: the service itself
    service_bits = []
    religion = _label(intake.get("religion"))
    ...
    # Line 4: the money and the reference
    total = intake.get("computedTotal")
    if total:
        money = f"Quoted total S${total:,.0f}"
        if quote_id:
            money += f" ({quote_id})"
        lines.append(money + ".")

    arrangement = " ".join(lines)

    # The family's own reason, condensed and set on its own line
    if reason and reason.strip():
        return arrangement + "\nReason: " + summarise_reason(reason)
    return arrangement
```

**Result in the console**

```
FR-2026-080912610      WAITING              Waiting just now
Tan Wei Ming                                        12:50 PM
9123 4567 · Phone call (Immediate)      [Open Chat & Take Over →]

SUMMARY FROM THE ASSISTANT
Buddhist funeral, 5-day wake, Deluxe tier, Oak casket. Wake at HDB void
deck. Cremation, ashes to columbarium niche. Add-ons: catering, livestream.
Quoted total S$8,800 (QT-2026-9812A).
Reason: Wants wake at family home, evening rites
```

**Why this matters more than it looks.** The consultant picks up the phone already
knowing everything. Without it, the first thing a grieving family hears is *"so tell
me what you're looking for"* — after they have just spent ten minutes explaining it.

---

## Step 4 — Activity monitoring and console alerts

Rather than relying on resource-intensive persistent connections (like WebSockets), the dashboard uses a resilient, lightweight polling cycle to synchronize data, track time elapsed, display in-console toast alerts, and monitor connection health.

### 4a. Polling cycle initialization

When the staff interface loads and is active, a background polling cycle starts. It schedules two concurrent tasks: a backend sync every 5 seconds, and a visual clock tick every 1 second.

```javascript
function startConsoleListPolling() {
  if (consoleListPollTimer) clearInterval(consoleListPollTimer);
  consoleListPollTimer = setInterval(loadStaffDashboardData, 5000);

  // Separate, faster tick purely for the "x seconds ago" label, so it counts
  // up smoothly between the five-second data fetches.
  if (consoleClockTimer) clearInterval(consoleClockTimer);
  consoleClockTimer = setInterval(renderConsoleFreshness, 1000);
}

function stopConsoleListPolling() {
  if (consoleListPollTimer) clearInterval(consoleListPollTimer);
  consoleListPollTimer = null;
  if (consoleClockTimer) clearInterval(consoleClockTimer);
  consoleClockTimer = null;
  lastConsoleSyncAt = null;
}
```

### 4b. Sync status and live connection indicators

The staff interface is expected to be left open for long periods. To give directors visual confidence that the connection hasn't silently failed:
1. `lastConsoleSyncAt` tracks the UNIX timestamp of the last successful fetch.
2. A separate 1-second interval recalculates the seconds elapsed since the last fetch.
3. If no successful fetch occurs for over 20 seconds, the connection status dot `#console-live-dot` is flagged with the CSS class `.is-stale`, turning it from bright green to cold grey.

```javascript
function renderConsoleFreshness() {
  const label = document.getElementById('console-last-sync');
  if (!label) return;

  if (!lastConsoleSyncAt) {
    label.textContent = 'connecting';
    return;
  }

  const seconds = Math.floor((Date.now() - lastConsoleSyncAt) / 1000);
  label.textContent = seconds < 5 ? 'just now' : `${seconds}s ago`;

  // If polls stop landing, the number keeps climbing and the dot goes cold,
  // which is the director's first hint that the backend has gone away.
  const dot = document.getElementById('console-live-dot');
  if (dot) dot.classList.toggle('is-stale', seconds > 20);
}
```

### 4c. Backend consultant requests endpoint

On the server side, FastAPI loads requests from file storage, partitions them into lists based on their state (`WAITING`, `IN PROGRESS`, and `RESOLVED`), and returns them along with total status counts:

```python
@app.get("/api/consultant-requests")
def list_consultant_requests():
    requests_list = load_consultant_requests()
    
    waiting = [r for r in requests_list if r.get("status") == "WAITING"]
    in_progress = [r for r in requests_list if r.get("status") == "IN PROGRESS"]
    resolved = [r for r in requests_list if r.get("status") == "RESOLVED"]
    
    return {
        "requests": requests_list,
        "counts": {
            "waiting": len(waiting),
            "in_progress": len(in_progress),
            "resolved": len(resolved),
            "total": len(requests_list)
        }
    }
```

### 4d. Dashboard synchronization

Every 5 seconds, the dashboard executes an asynchronous GET request to the endpoint above. If the response succeeds, it stores the timestamp, refreshes the freshness labels, triggers change detection, and updates the stats badges in the dashboard header:

```javascript
async function loadStaffDashboardData() {
  if (!staffRequestsList) return;
  try {
    const resp = await fetch(`${API_BASE}/api/consultant-requests`);
    if (!resp.ok) throw new Error('Failed to load requests');
    const data = await resp.json();

    // A response landed, so the console is in touch with the backend.
    lastConsoleSyncAt = Date.now();
    renderConsoleFreshness();

    // Raise console alerts for anything new since the last poll
    detectNewActivity(data.requests);

    // Update counter badges
    const elWaiting = document.getElementById('staff-count-waiting');
    const elProgress = document.getElementById('staff-count-in-progress');
    const elResolved = document.getElementById('staff-count-resolved');

    if (elWaiting) elWaiting.textContent = data.counts.waiting;
    if (elProgress) elProgress.textContent = data.counts.in_progress;
    if (elResolved) elResolved.textContent = data.counts.resolved;

    // Filter and render list...
  } catch (err) {
    console.error('Error loading requests:', err);
  }
}
```

### 4e. Change detection and filtering

The polling response is diffed against a memory map (`seenTicketMessageCounts`) of known request IDs and message counts. We filter out the staff's own echoed messages so alerts are only generated for new requests or customer replies:

```javascript
function detectNewActivity(requests) {
  if (!Array.isArray(requests)) return;

  // First load after sign-in seeds the baseline silently, otherwise the
  // director gets a burst of alerts for tickets that were already there.
  if (!hasSeededTicketBaseline) {
    requests.forEach(req => {
      seenTicketMessageCounts.set(req.request_id, (req.conversation || []).length);
    });
    hasSeededTicketBaseline = true;
    return;
  }

  requests.forEach(req => {
    const msgCount = (req.conversation || []).length;

    if (!seenTicketMessageCounts.has(req.request_id)) {
      notifyDirector(
        `New request from ${req.customer_name}`,
        req.ai_summary || req.reason || 'A family has requested a consultant.',
        req.request_id
      );
      seenTicketMessageCounts.set(req.request_id, msgCount);
      return;
    }

    const previous = seenTicketMessageCounts.get(req.request_id);
    if (msgCount > previous) {
      // Only alert on messages from the family, not our own replies
      // echoing back from the server.
      const latest = (req.conversation || [])[msgCount - 1] || {};
      if (latest.role === 'user') {
        notifyDirector(
          `${req.customer_name} replied`,
          latest.content || 'New message on an open consultation.',
          req.request_id
        );
      }
      seenTicketMessageCounts.set(req.request_id, msgCount);
    }
  });
}
```

Two decisions worth explaining out loud:

- **The baseline seed.** Without it, signing in with eleven waiting tickets fires
  eleven alerts at once.
- **`latest.role === 'user'`.** Without it, Marcus gets alerted about his own
  messages coming back from the server.

### 4f. Console toast alert implementation

Instead of popping desktop browser notifications, the dashboard spawns and mounts ephemeral DOM elements into a designated container (`#console-toast-stack`). These toast alerts are programmed to self-destruct after 6.6 seconds:

```javascript
function notifyDirector(title, body, requestId) {
  // Show the in-console toast
  showConsoleToast(title, body);
}

function showConsoleToast(title, body) {
  const stack = document.getElementById('console-toast-stack');
  if (!stack) return;

  const toast = document.createElement('div');
  toast.className = 'console-toast';
  toast.innerHTML = `
    <div class="console-toast-title">${escapeHtml(title)}</div>
    <div class="console-toast-body">${escapeHtml(body)}</div>
  `;
  stack.appendChild(toast);

  // Fade out, then remove, so the stack does not grow unbounded.
  setTimeout(() => toast.classList.add('is-leaving'), 6000);
  setTimeout(() => toast.remove(), 6600);
}
```

### 4g. Waiting time and urgency styling

The dashboard visually color-codes waiting times dynamically using CSS classes, highlighting cases that have been unattended for 5 minutes (amber) or 15 minutes (red):

```javascript
function waitingUrgencyClass(isoString, status) {
  if (status !== 'WAITING') return 'text-creamMuted/70';
  const minutes = (Date.now() - new Date(isoString).getTime()) / 60000;
  if (minutes >= 15) return 'text-ember font-semibold';   // red
  if (minutes >= 5)  return 'text-brass font-semibold';   // amber
  return 'text-creamMuted';
}
```

A timestamp makes the director do arithmetic. **"Waiting 9 min"** in amber does not.

---

## Step 5 — Takeover: the state machine

This is the technical heart of the feature.

```python
@app.post("/api/consultant-requests/{request_id}/takeover")
def takeover_consultant_request(request_id: str):
    requests_list = load_consultant_requests()
    for req in requests_list:
        if req.get("request_id") == request_id:
            req["status"] = "IN PROGRESS"
            req["mode"] = "HUMAN"
            req["assigned_staff"] = "Marcus Chen (Funeral Consultant)"
            req["updated_at"] = datetime.now().isoformat()

            req["conversation"].append({
                "role": "staff",
                "content": "🟢 Marcus Chen (Funeral Consultant) has joined the chat and taken over from AI Assistant.",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "sender": "System"
            })
            save_consultant_requests(requests_list)
            return req
```

### The gate that silences the AI

At the very top of `/api/chat`, before anything else happens:

```python
@app.post("/api/chat", response_model=ChatResponse)
def chat_with_assistant(request: ChatRequest):

    # 1. Check if user is in an active HUMAN mode request
    if request.request_id:
        requests_list = load_consultant_requests()
        for req in requests_list:
            if req.get("request_id") == request.request_id and req.get("mode") == "HUMAN":
                req["conversation"].append({
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.now().strftime("%I:%M %p"),
                    "sender": req.get("customer_name", "Customer")
                })
                req["updated_at"] = datetime.now().isoformat()
                save_consultant_requests(requests_list)
                return ChatResponse(
                    response="Your message has been delivered directly to your human consultant.",
                    mode="HUMAN",
                    request_id=request.request_id
                )
```

**Read that carefully — it is the feature.** The function returns before the LLM is
ever called. The message is stored for Marcus instead. Without this check, the
family would get an AI reply *and* a human reply to the same question.

```
mode = "AI"      → the assistant answers
mode = "HUMAN"   → the assistant is silent, messages route to staff
mode = "CLOSED"  → conversation finished
```

---

## Step 6 — The family's side updates itself

The phone polls its own ticket every two seconds:

```javascript
async function pollCustomerChat() {
  if (!state.consultantRequestId) return;

  const resp = await fetch(`${API_BASE}/api/consultant-requests/${state.consultantRequestId}`);
  const ticket = await resp.json();

  state.conversationMode = ticket.mode;

  // Reflect the handoff in the chip row: no point offering an escalation
  // to someone already speaking with a consultant.
  renderQuickChips();

  const banner = document.getElementById('human-mode-banner');
  if (ticket.mode === 'HUMAN') {
    banner.classList.remove('hidden');
  } else if (ticket.mode === 'CLOSED') {
    banner.classList.add('hidden');
    if (state.customerPollTimer) clearInterval(state.customerPollTimer);
  }

  // Append any staff messages we have not shown yet
  ticket.conversation.forEach(m => {
    if (m.role === 'staff' && !historyContents.includes(m.content)) {
      if (m.sender === 'System') {
        appendSystemLine(m.content.replace(/^[^\w]+/, ''));
      } else {
        appendBubble(m.content, 'staff', m.sender);
      }
    }
  });
}
```

**Three things happen on the family's screen the moment Marcus takes over:**

1. The green **"Consultant is replying"** banner appears
2. The **"Speak to a consultant" chip disappears** — they are already talking to one
3. Consultant messages arrive in tinted bubbles with a copper left edge, visually
   distinct from Hannah's white ones

```
        Marcus Chen joined the chat

  Marcus Chen
  ┌──────────────────────────────────┐
  │ Hello Mr Tan, I have your        │
  │ arrangement in front of me.      │
  └──────────────────────────────────┘
```

---

## Step 7 — Staff replies

```python
@app.post("/api/consultant-requests/{request_id}/message")
def send_staff_message(request_id: str, payload: StaffMessageSend):
    requests_list = load_consultant_requests()
    for req in requests_list:
        if req.get("request_id") == request_id:
            msg_obj = {
                "role": "staff",
                "content": payload.message,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "sender": payload.staff_name or "Marcus Chen"
            }
            req["conversation"].append(msg_obj)
            req["updated_at"] = datetime.now().isoformat()
            save_consultant_requests(requests_list)
            return req
```

Both sides append to the **same `conversation` array** on the same ticket. There is
one record; two clients read and write it. That is why the ordering stays correct
without either side coordinating with the other.

---

## Step 8 — Closing the session

When the consultation is complete, the staff member clicks **"End Consultation"** in the staff chat view and confirms in the dialog. This puts the conversation into the final `CLOSED` state and stops the background polling.

### 8a. Backend state transition

The server marks the request status as `RESOLVED` and the conversation mode as `CLOSED`, appending a final system message to notify the family:

```python
@app.post("/api/consultant-requests/{request_id}/end")
def end_consultant_request(request_id: str):
    requests_list = load_consultant_requests()
    for req in requests_list:
        if req.get("request_id") == request_id:
            req["status"] = "RESOLVED"
            req["mode"] = "CLOSED"
            req["updated_at"] = datetime.now().isoformat()
            
            req["conversation"].append({
                "role": "staff",
                "content": "Your consultant has completed the session and marked this request as resolved. Thank you for speaking with Solace Dignity Care.",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "sender": "Marcus Chen"
            })
            save_consultant_requests(requests_list)
            return req
            
    raise HTTPException(status_code=404, detail="Consultant request not found")
```

**How the server processes the session closure:**
- **Status Update (`status: RESOLVED`):** Moves the ticket out of the active queue and indexes it as resolved, updating the sync counters for the console.
- **Mode Shift (`mode: CLOSED`):** Silences the real-time routing to the consultant. Any new chat sessions initiated by the user will trigger a fresh AI interaction rather than routing to the closed ticket.
- **System Message Injection:** Appends a final closure message to the conversation array. Because both client and staff look at the same single record, this message appears instantly on both screens as the final resolution text.
- **Persistence:** Writes the modified requests list back to the server's local JSON database using `save_consultant_requests(requests_list)`.

### 8b. Frontend resolution response

Upon confirming the end of consultation, the staff client executes the POST request, closes the chat modal, and reloads the staff dashboard to move the request into the resolved/archived category:

```javascript
btnConfirmEndConsultation.addEventListener('click', async () => {
  if (!state.activeStaffRequestId) return;
  try {
    const resp = await fetch(`${API_BASE}/api/consultant-requests/${state.activeStaffRequestId}/end`, { method: 'POST' });
    if (resp.ok) {
      if (endConsultationModal) endConsultationModal.classList.add('opacity-0', 'pointer-events-none');
      closeStaffChatModal();
      loadStaffDashboardData();
    }
  } catch (err) {
    console.error('Error ending consultation:', err);
  }
});
```

### 8c. Teardown on the family's client

As soon as the family's regular polling detects that the ticket has transitioned to `mode: 'CLOSED'`, the polling loop is cleared to save resources, the green human consultant banner is hidden, and the final resolution bubble is rendered in the chat:

```javascript
  const banner = document.getElementById('human-mode-banner');
  if (ticket.mode === 'HUMAN') {
    banner.classList.remove('hidden');
  } else if (ticket.mode === 'CLOSED') {
    banner.classList.add('hidden');
    if (state.customerPollTimer) clearInterval(state.customerPollTimer);
  }
```

This completes the loop: the staff dashboard is refreshed, the user is notified that the session is closed, and all active polls are safely torn down.

---

## The full lifecycle

```
Family taps "Speak to a consultant"
        ↓
Request form opens, pre-filled with name and contact
        ↓
Family submits  →  POST /api/consultant-requests
                   (+ full chat history + intake state)
        ↓
Ticket created: status WAITING, mode AI, + generated summary
        ↓
Console polls (5s) → detectNewActivity() spots a new id
        ↓
Console toast alert
        ↓
Marcus clicks Open Chat & Take Over
        ↓
POST /takeover → status IN PROGRESS, mode HUMAN, staff assigned
        ↓
Family's poll (2s) → banner appears, escalation chip disappears
        ↓
/api/chat now returns before the LLM — messages route to Marcus
        ↓
Marcus replies → POST /message → family's poll renders it
        ↓
End Consultation → mode CLOSED, status RESOLVED
```

---

## Demo script (about 90 seconds)

Two windows side by side. Family's phone on the left, console on the right.

1. **Tap "Speak to a consultant"** → the form opens, already pre-filled
2. **Submit** → *the console shows a toast alert.*
   Pause here. Point out that the new request has appeared in the console list.
3. **Point at the summary** — everything the family told the assistant, already there
4. **Click Open Chat & Take Over** → on the phone, the chip vanishes and the banner
   turns green
5. **Type as Marcus** → it appears on the family's phone in about two seconds
6. **End Consultation** → resolved

Optional extra beat: after the takeover, point out that the "Speak to a consultant"
chip has **removed itself** from the family's screen — they are already talking to a
person.

---

## Questions you should answer before they are asked

**"Why a button rather than letting the AI decide?"**
Because the family should never have to work out the magic words. A permanent,
visible route to a human is the safer design in a grief context — the person in
front of you is upset, and asking them to phrase a request correctly is a bad
experience. The backend does also detect phrases like "speak to someone" and offers
the handoff automatically, but that is a convenience on top of the button, not the
mechanism we depend on.

**"Why polling instead of WebSockets?"**
At this scale a 1.5-second poll is indistinguishable from a socket, without
reconnection logic, heartbeat handling, or a second server process. Honest scope, not
a gap.

**"Why JSON files instead of a database?"**
The prototype needs to prove the workflow, not the storage engine. The read/write
functions are isolated, so swapping to SQLite touches two functions.

**"What was the hardest part?"**
Server-side state. Features 1 and 2 are stateless — ask, get an answer, done. This is
the only feature where two people are in one conversation at the same time, so the
server has to remember whose turn it is. The `mode` check at the top of `/api/chat`
is the entire feature in one condition.

**"What would you improve?"**
`takeover` has no guard — it does not check whether `assigned_staff` is already set,
so two directors could both claim the same ticket, or one could double-click and
append two join notices. A single `if req.get("assigned_staff"): raise HTTPException`
would fix it. Naming this yourself is stronger than having it found for you.
