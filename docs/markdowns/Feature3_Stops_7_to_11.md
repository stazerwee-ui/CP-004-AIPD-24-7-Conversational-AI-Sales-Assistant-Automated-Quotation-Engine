# Feature 3 — Stops 7 to 11

Project CP-004 · Klass Dignity Care

The ticket already exists in `consultant_requests.json` and a card is showing in the
console. This document covers everything from the moment Marcus clicks **Open Chat &
Take Over** to the moment the consultation is closed.

---

## Where we are

By the end of Stop 6 the ticket looks like this:

```json
{
  "request_id": "FR-2026-080912610",
  "customer_name": "Tan Wei Ming",
  "status": "WAITING",
  "mode": "AI",
  "assigned_staff": null,
  "conversation": [ ...the chat so far... ]
}
```

Two fields matter from here on:

| Field | Now | Meaning |
|---|---|---|
| `status` | `WAITING` | Where it sits in the queue |
| `mode` | `AI` | **Who is allowed to reply** |

Stops 7 to 11 are the story of those two fields changing.

---

# Stop 7 — Marcus takes over

## What the console sends

```javascript
fetch(`${API_BASE}/api/consultant-requests/FR-2026-080912610/takeover`, { method: 'POST' })
```

Note the URL has the ticket ID inside it. There is no body — the server does not need
any data, it just needs to know *which* ticket to claim.

## The full backend function

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

            # System join message
            req["conversation"].append({
                "role": "staff",
                "content": "🟢 Marcus Chen (Funeral Consultant) has joined the chat and taken over from AI Assistant.",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "sender": "System"
            })
            save_consultant_requests(requests_list)
            return req

    raise HTTPException(status_code=404, detail="Consultant request not found")
```

## Line by line

**`@app.post(".../{request_id}/takeover")`**
The `{request_id}` part is a placeholder. Whatever appears there in the URL gets
passed into the function as the `request_id` argument. So a request to
`/api/consultant-requests/FR-2026-080912610/takeover` calls the function with
`request_id = "FR-2026-080912610"`.

**`requests_list = load_consultant_requests()`**
Reads the whole file into a Python list. Every endpoint that changes a ticket starts
this way.

**`for req in requests_list:`**
Walks through every ticket one at a time. There is no index or database lookup —
just a plain search. Fine for a prototype; a database would do this with an index.

**`if req.get("request_id") == request_id:`**
Is this the one we want? `.get()` rather than `[...]` so a ticket missing the field
returns `None` instead of crashing the request.

**The three field assignments**
```python
req["status"] = "IN PROGRESS"      # queue position
req["mode"] = "HUMAN"              # who may reply  ← the important one
req["assigned_staff"] = "Marcus Chen (Funeral Consultant)"
```
`mode` is the one that matters. Stop 9 reads this field to decide whether the AI is
allowed to answer.

**`req["updated_at"] = datetime.now().isoformat()`**
`isoformat()` produces `"2026-08-09T12:52:31.482910"` — a sortable timestamp.

**`req["conversation"].append({...})`**
Adds a "Marcus has joined" notice to the conversation. Note this is stored as a
**message**, not just a status flag. Two reasons:

1. The family sees it appear in their chat.
2. The transition stays in the permanent record — you can look at a resolved ticket
   later and see exactly when the human joined.

**`"sender": "System"`**
This is what tells the frontend to draw it as a centred grey line rather than a
speech bubble. A system announcement is not a person speaking.

**`save_consultant_requests(requests_list)`**
Writes the whole list back to the file. This is the moment the change becomes real.

**`return req`**
Sends the updated ticket back to the console.

**`raise HTTPException(status_code=404, ...)`**
Only reached if the loop finished without finding the ticket. Returns a proper 404
rather than silently doing nothing.

## What the file looks like after

```json
{
  "request_id": "FR-2026-080912610",
  "status": "IN PROGRESS",
  "mode": "HUMAN",
  "assigned_staff": "Marcus Chen (Funeral Consultant)",
  "conversation": [
    ...previous messages...,
    { "role": "staff", "sender": "System", "content": "🟢 Marcus Chen has joined..." }
  ]
}
```

**Where the data is:** back in the file. The family's phone still knows nothing.

---

# Stop 8 — The phone notices

## The polling loop

```javascript
function startCustomerPolling() {
  if (state.customerPollTimer) clearInterval(state.customerPollTimer);
  state.customerPollTimer = setInterval(pollCustomerChat, 2000);
}
```

`setInterval(pollCustomerChat, 2000)` means: run `pollCustomerChat`, wait 2000
milliseconds (2 seconds), run it again, forever.

The `clearInterval` on the first line stops any previous timer before starting a new
one, so two timers can never run at once.

This started back at Stop 3, the moment the form was submitted.

## The full function

```javascript
async function pollCustomerChat() {
  if (!state.consultantRequestId) return;
  try {
    const resp = await fetch(`${API_BASE}/api/consultant-requests/${state.consultantRequestId}`);
    if (!resp.ok) return;
    const ticket = await resp.json();

    state.conversationMode = ticket.mode;

    renderQuickChips();

    const banner = document.getElementById('human-mode-banner');
    if (ticket.mode === 'HUMAN') {
      if (banner) {
        banner.classList.remove('hidden');
        const staffName = document.getElementById('human-consultant-name');
        if (staffName) staffName.textContent = `Staff: ${ticket.assigned_staff || 'Marcus Chen'}`;
      }
    } else if (ticket.mode === 'CLOSED') {
      if (banner) banner.classList.add('hidden');
      if (state.customerPollTimer) clearInterval(state.customerPollTimer);
    }

    if (ticket.conversation && ticket.conversation.length > 0) {
      const historyContents = chatHistory.map(h => h.content);
      ticket.conversation.forEach(m => {
        if (m.role === 'staff' && !historyContents.includes(m.content)) {
          if (m.sender === 'System') {
            appendSystemLine(m.content.replace(/^[^\w]+/, ''));
          } else {
            appendBubble(m.content, 'staff', m.sender);
          }
          chatHistory.push({ role: 'assistant', content: m.content });
        }
      });
    }

  } catch (err) {
    console.error('Error polling customer chat:', err);
  }
}
```

## Line by line

**`if (!state.consultantRequestId) return;`**
No ticket, nothing to poll for. Exits immediately.

**`fetch(\`.../${state.consultantRequestId}\`)`**
Asks for **one** ticket, not the whole list. The console fetches everything; the
phone only cares about its own.

**`if (!resp.ok) return;`**
`fetch` does not throw an error on a 500 — the request technically succeeded, the
answer was just bad news. You have to check `resp.ok` yourself.

**`state.conversationMode = ticket.mode;`**
The phone copies the mode from the server. The server is authoritative; the phone
just mirrors whatever it says.

**`renderQuickChips();`**
Rebuilds the button row. Because the escalation chip is marked `hideInHumanMode`,
this is what makes it disappear.

**The `HUMAN` branch**
```javascript
banner.classList.remove('hidden');
staffName.textContent = `Staff: ${ticket.assigned_staff || 'Marcus Chen'}`;
```
Shows the green banner and fills in the consultant's name from the ticket.
The `|| 'Marcus Chen'` is a fallback if `assigned_staff` is somehow empty.

**The `CLOSED` branch**
```javascript
banner.classList.add('hidden');
clearInterval(state.customerPollTimer);
```
Hides the banner and **stops the timer**. Without that line, every resolved
conversation would leave a browser asking the server for updates every two seconds
forever.

**`const historyContents = chatHistory.map(h => h.content);`**
Makes a list of just the text of every message already on screen:
```javascript
['Hello, I am Hannah...', 'I need a Buddhist package', ...]
```

**`if (m.role === 'staff' && !historyContents.includes(m.content))`**
Two conditions:
- `m.role === 'staff'` — only staff messages need rendering. The family's own
  messages are already on their screen.
- `!historyContents.includes(m.content)` — **the dedupe check**. Every poll
  downloads the *entire* conversation. Without this, the same message would render
  again every two seconds forever.

**`m.sender === 'System'`**
System notices get `appendSystemLine` (a centred grey line). Real people get
`appendBubble` (a speech bubble with a name label).

**`m.content.replace(/^[^\w]+/, '')`**
Strips any leading non-word characters — this removes the 🟢 emoji the backend put
on the front of the join notice.

**`chatHistory.push(...)`**
Records the message so the next poll's dedupe check will skip it.

## What the family sees

```
        Marcus Chen joined the chat

  Marcus Chen
  ┌──────────────────────────────────┐
  │ Hello Mr Tan, I have your        │
  │ arrangement in front of me.      │
  └──────────────────────────────────┘
```

Three changes at once — banner appears, escalation chip disappears, consultant
bubbles arrive in a different colour. Any one alone would be easy to miss.

---

# Stop 9 — The AI goes quiet

The family now types "can I add catering?". It goes to `/api/chat` as usual — but
the **first thing** in that function is this check.

## The gate

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

## Line by line

**`if request.request_id:`**
Only a conversation with a ticket can possibly be in HUMAN mode. A family who never
requested a consultant skips this entirely.

**`and req.get("mode") == "HUMAN"`**
This is the actual condition. If the mode is still `AI`, the loop finds nothing and
execution continues down to the normal assistant logic.

**`req["conversation"].append({...})`**
Stores the family's message **for Marcus** instead of answering it. Note
`"role": "user"` — this is what makes it render as a family message in the staff
chat window.

**`return ChatResponse(...)`**
**This single line is the entire feature.** `return` ends the function. Every line
below it — the intake questions, the price lookups, the catalog answers, the call to
Ollama — never executes.

## Why the position matters

Every message the family sends passes through `chat_with_assistant`. If this check
sat further down, the assistant might have already generated a reply before anyone
asked whether it should.

## What breaks without it

| Family types | With the gate | Without the gate |
|---|---|---|
| "can I add catering?" | Saved for Marcus. AI silent. | Hannah says "$450 per day" **and** Marcus says he will sort it out. |

Two answers to one question, and if the assistant's figure is out of date they
contradict each other — to a grieving family.

## The state machine

```
    AI  ──────────►  HUMAN  ──────────►  CLOSED
    │                  │                    │
 assistant       assistant silent,     conversation
 answers         messages go to        finished
                 the consultant
```

Stop 7 wrote `mode = "HUMAN"`. Stop 9 reads it. **One field written in one place and
read in another — that is the whole mechanism by which a human takes over from an
AI.**

---

# Stop 10 — Marcus replies

## The full backend function

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

    raise HTTPException(status_code=404, detail="Consultant request not found")
```

## What `StaffMessageSend` is

```python
class StaffMessageSend(BaseModel):
    staff_name: Optional[str] = "Marcus Chen (Funeral Consultant)"
    message: str
```

`message: str` has no default, so it is **required** — a request without it is
rejected with a 422 before the function runs. `staff_name` falls back to the default
if not sent.

## Line by line

**`"role": "staff"`**
This is what the family's poll filters on. Only `staff` messages get rendered on
their phone.

**`"timestamp": datetime.now().strftime("%I:%M %p")`**
`%I` = 12-hour clock, `%M` = minutes, `%p` = AM/PM. Produces `"12:52 PM"`.

**`payload.staff_name or "Marcus Chen"`**
Python's `or` returns the first truthy value. An empty string is falsy, so a blank
name falls back to the default.

**`req["conversation"].append(msg_obj)`**
**The same list the family's messages go into.** One conversation, one record, in
order.

## The matching customer endpoint

There is a mirror of this for the family's side:

```python
@app.post("/api/consultant-requests/{request_id}/customer-message")
def send_customer_message(request_id: str, payload: CustomerMessageSend):
    ...
    msg_obj = {
        "role": "user",
        "content": payload.message,
        "timestamp": datetime.now().strftime("%I:%M %p"),
        "sender": payload.sender_name or req.get("customer_name", "Customer")
    }
    req["conversation"].append(msg_obj)
```

Identical shape, different `role`. Both write into the same array.

## Why one shared array

If each side kept its own list of messages, you would have to merge them afterwards
and reconcile the timestamps — and any disagreement would show up as messages
appearing in the wrong order.

One array means order is guaranteed by the order of writes. Neither side has to
coordinate with the other.

```json
"conversation": [
  { "role": "user",      "sender": "Tan Wei Ming",  "content": "Hi, I need a Buddhist package" },
  { "role": "assistant", "sender": "AI Assistant",  "content": "Our Buddhist Ceremony Rites..." },
  { "role": "staff",     "sender": "System",        "content": "Marcus Chen has joined the chat" },
  { "role": "staff",     "sender": "Marcus Chen",   "content": "Hello Mr Tan, I have your..." }
]
```

The family's phone picks this up on its next two-second check.

---

# Stop 11 — Closing the session

## The full backend function

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

## Line by line

**`req["status"] = "RESOLVED"`**
Moves the ticket into the Resolved counter in the console.

**`req["mode"] = "CLOSED"`**
The final state. The next time the family sends a message, the gate in Stop 9 no
longer matches (`mode` is `CLOSED`, not `HUMAN`), so the assistant handles it again.

**The closing message**
Appended so the family sees a proper goodbye rather than the conversation just going
quiet.

## What happens on the family's phone

On the next two-second poll, this branch runs:

```javascript
} else if (ticket.mode === 'CLOSED') {
  if (banner) banner.classList.add('hidden');
  if (state.customerPollTimer) clearInterval(state.customerPollTimer);
}
```

Banner hidden, **timer stopped**. Without that `clearInterval`, every resolved
conversation would leave a browser asking the server for updates every two seconds
indefinitely.

## Why RESOLVED instead of deleting

The record is the point. A funeral company needs to know what was discussed and by
whom. Resolved tickets stay in the file and in the console under their own counter.

---

# The five stops in one picture

```
Stop 7   Console → POST /takeover
         mode: AI → HUMAN, staff assigned, join notice appended
                    ↓  saved to file
Stop 8   Phone reads (every 2s) → sees HUMAN
         banner appears, chip disappears, notice renders
                    ↓
Stop 9   Family types → /api/chat → gate sees mode HUMAN
         message stored for Marcus, AI never runs
                    ↓  saved to file
Stop 10  Marcus types → POST /message
         appended to the SAME conversation array
                    ↓  saved to file
         Phone reads (every 2s) → renders the bubble
                    ↓
Stop 11  Console → POST /end
         mode: HUMAN → CLOSED, status → RESOLVED
                    ↓
         Phone reads → banner hidden, clearInterval, polling stops
```

---

# The pattern every endpoint follows

All four backend functions in these stops are the same shape:

```python
requests_list = load_consultant_requests()      # 1. read the whole file
for req in requests_list:                       # 2. find the ticket
    if req.get("request_id") == request_id:
        ...change some fields...                # 3. edit in memory
        save_consultant_requests(requests_list) # 4. write the whole file back
        return req                              # 5. reply to the caller
raise HTTPException(status_code=404, ...)       # 6. not found
```

Learn that shape and you have read all of them.

---

# Questions to have ready

**"Why store the join notice as a message instead of just a flag?"**
So the family sees it in their chat, and so the transition stays in the permanent
record — you can open a resolved ticket months later and see exactly when the human
took over.

**"What stops the same message rendering over and over?"**
The dedupe check in Stop 8. Every poll downloads the whole conversation, so the phone
compares each message against what it has already shown.

**"Why does the AI stop replying?"**
One field. Stop 7 sets `mode` to `HUMAN`; the check at the top of `/api/chat` reads
it and returns before the assistant code runs.

**"What would you improve?"**
`takeover` has no guard — it never checks whether `assigned_staff` is already set, so
two directors could claim the same ticket, or a double-click appends two join
notices. A single `if` statement would fix it.
