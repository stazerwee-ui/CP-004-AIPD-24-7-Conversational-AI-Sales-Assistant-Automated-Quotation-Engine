# Feature 3 — Human Consultant Handoff (AI → Human Takeover)

Project CP-004 · Klass Dignity Care

---

## The one sentence to lead with

> One conversation, two possible authors. The backend decides which one is allowed
> to speak.

That is the whole feature. Everything else is plumbing around it.

---

## Why this is harder than Features 1 and 2

| | Features 1 & 2 | Feature 3 |
|---|---|---|
| Users at once | One | Two — family and director |
| Server memory | None needed | A ticket that outlives the page |
| Refresh the page | Behaves identically | Must resume the same conversation |
| Failure mode | Wrong number on screen | AI and human both replying at once |

**Features 1 and 2 compute an answer. Feature 3 has to remember a decision.**

A pricing request is stateless: send the selections, get a total, done. Nothing
persists, and refreshing the page changes nothing.

A handoff is not. The server has to know that Marcus took over this conversation
four minutes ago, so that when the family types again, the message goes to Marcus
and *not* to the language model. Three things follow from that, none of which
existed in Features 1 or 2:

- A **state machine** that decides whether the AI is allowed to speak
- **Two clients reading one record**, staying in sync without stepping on each other
- **Persistence** — the ticket outlives the page, the browser, and the server

---

## The state machine

Every consultant request carries a field called `mode`. It has exactly three values,
and the transitions only go one way:

```
    AI  ──────────►  HUMAN  ──────────►  CLOSED
    │                  │                    │
 assistant       assistant silent,     conversation
 answers         messages go to        finished
                 the consultant
```

```python
"mode": "AI"        # the assistant answers
"mode": "HUMAN"     # the assistant is silent, messages route to staff
"mode": "CLOSED"    # the consultation is over
```

You cannot go from CLOSED back to HUMAN without raising a new request. That
constraint is the point: **at any moment there is exactly one answer to the question
"who is speaking to this family?"**

Do not confuse `mode` with `status`. They change together but mean different things:

| Field | Values | What it is for |
|---|---|---|
| `status` | WAITING / IN PROGRESS / RESOLVED | where the ticket sits in the queue |
| `mode` | AI / HUMAN / CLOSED | who is allowed to reply |

A ticket can be WAITING and still in AI mode — nobody has picked it up, so the
assistant is still handling the conversation.

Stops 7 and 9 below are where this state machine actually does its work.

---

## The three places data can be

There are only three:

| Where | What it is |
|---|---|
| **The family's browser** | `state` and `chatHistory` — variables in `app.js`, living in memory |
| **The server** | `main.py` running, plus the file `consultant_requests.json` on disk |
| **The director's browser** | Whatever it last read from the server |

Data moves between them **only** by `fetch()`. Nothing else.

---

## Stop 1 — Before anything happens

The family has been chatting. Their choices live in the browser's memory, in a
variable called `state`:

```javascript
state = {
  user: { name: 'Tan Wei Ming', contact: '9123 4567' },
  religion: 'buddhist',
  tier: 'deluxe',
  casket: 'oak',
  computedTotal: 8800,
  consultantRequestId: null      // ← no ticket yet
}
```

**Where is this?** Only in Chrome's memory on the family's phone. The server knows
nothing about it. Refresh the page and it's gone.

---

## Stop 2 — They tap the button

`openConsultantModal()` runs in `app.js`. It reads `state.user` and fills the form
boxes:

```javascript
nameInput.value = state.user.name;      // "Tan Wei Ming" → into the Name box
phoneInput.value = state.user.contact;  // "9123 4567"    → into the Phone box
```

The login screen accepts a phone number *or* an email, so the real code checks which
one it is before deciding where to put it:

```javascript
const contact = String(state.user.contact).trim();
const looksLikeEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact);

if (looksLikeEmail) {
  if (emailInput && !emailInput.value) emailInput.value = contact;
} else if (phoneInput && !phoneInput.value) {
  phoneInput.value = contact;
}
```

That regex asks: does this have an `@` with characters either side, and a dot near
the end? If yes, it is an email.

| Login value | Phone field | Email field |
|---|---|---|
| `9123 4567` | `9123 4567` | *(empty)* |
| `stazerwee@gmail.com` | *(empty)* | `stazerwee@gmail.com` |

**Where is the data?** Still only in the browser. It has just moved from a variable
onto the screen.

---

## Stop 3 — They press submit

This is the moment data leaves the phone.

```javascript
const resp = await fetch(`${API_BASE}/api/consultant-requests`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    customer_name: "Tan Wei Ming",
    phone: "9123 4567",
    reason: "want to ask about the wake location",
    history: chatHistory,
    intake_state: state
  })
});
```

**What `JSON.stringify` does:** turns the JavaScript object into one long line of
text, because text is all you can send over the internet.

**Where does it go?** `API_BASE` is `http://127.0.0.1:8000`. So this text is sent to
the Python program running in your uvicorn window.

**`await` means:** stop here and wait for a reply. The form stays open until it comes
back.

**The two fields that matter** are `history` and `intake_state`. Everything else is
contact details. Those two are what let the consultant open the ticket already
knowing the arrangement.

---

## Stop 4 — The server receives it

In `main.py`:

```python
@app.post("/api/consultant-requests")
def create_consultant_request(payload: ConsultantRequestCreate):
```

**`@app.post("/api/consultant-requests")`** — "when text arrives at this address, run
the function below."

**`payload`** is now that text, turned back into Python data. So
`payload.customer_name` is `"Tan Wei Ming"`.

**What `ConsultantRequestCreate` is** — the shape the incoming data must match:

```python
class ConsultantRequestCreate(BaseModel):
    customer_name: str
    phone: str
    email: Optional[str] = None
    preferred_contact_method: Optional[str] = "Phone call"
    preferred_contact_time: Optional[str] = "Immediate"
    reason: Optional[str] = "Package consultation"
    history: Optional[List[Dict[str, Any]]] = None
    intake_state: Optional[Dict[str, Any]] = None
```

`customer_name: str` has no default, so it is **required** — a request missing it is
rejected with a 422 before your code runs. `Optional[...] = "Phone call"` means the
default is used if nothing is sent.

The function then does three things.

### 1. Makes a ticket number

```python
rand_seq = random.randint(100, 999)
now_dt = datetime.now()
ticket_id = f"FR-2026-{now_dt.strftime('%m%d%H')}{rand_seq}"
# → "FR-2026-080912610"
```

`%m` month, `%d` day, `%H` hour — plus three random digits.

### 2. Writes the summary

```python
ai_summary = generate_ai_executive_summary(
    payload.intake_state, payload.history, payload.reason
)
# → "Buddhist funeral, 5-day wake, Deluxe tier, Oak casket. Quoted total S$8,800."
```

This reads the choices out of `intake_state` and builds a sentence. It is assembled
from the stored choices, **not written by the model** — the consultant is about to
phone a bereaved family, and a summary saying "Deluxe" when they chose "Standard"
would be a bad conversation.

### 3. Builds the ticket

```python
new_request = {
    "request_id": "FR-2026-080912610",
    "customer_name": "Tan Wei Ming",
    "phone": "9123 4567",
    "status": "WAITING",
    "mode": "AI",
    "ai_summary": "Buddhist funeral, 5-day wake...",
    "assigned_staff": None,
    "conversation": [...]
}
```

**`status` and `mode` are different things.** `status` is where it sits in the queue
(WAITING / IN PROGRESS / RESOLVED). `mode` is who is allowed to reply (AI / HUMAN /
CLOSED). A ticket can be WAITING and still in AI mode.

**Where is the data now?** In the server's memory, as a Python dictionary. Still not
saved. If uvicorn crashed here, it would vanish.

---

## Stop 5 — Saved to the file

```python
requests_list.insert(0, new_request)
save_consultant_requests(requests_list)
return new_request
```

`insert(0, ...)` puts it at the front of the list, so newest tickets appear first
with no sorting needed.

And `save_consultant_requests` is just this:

```python
def save_consultant_requests(data):
    with open(CONSULTANT_REQUESTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
```

- **`"w"`** = write mode. It **wipes the file** and writes the whole list back, new
  ticket included. Not an append — ten existing tickets all get rewritten to add the
  eleventh.
- **`json.dump`** converts the Python dictionary into JSON text.
- **`indent=2`** pretty-prints it, which is why you can read it in Notepad.

**Python dict vs JSON — the difference:**

```python
{"status": "WAITING", "assigned_staff": None}     # Python, in memory
```

```json
{"status": "WAITING", "assigned_staff": null}     ← JSON, text on disk
```

Nearly identical. Python's `None` becomes `null`, `True` becomes `true`. JSON is a
*text format*; a dict is a *live object*.

**Where is the data now?** In a real file on your hard drive:
`new18july/consultant_requests.json`. You can open it in Notepad and see it.

**This is the important moment.** The ticket now exists somewhere both browsers can
reach.

Then the server replies to the phone with the ticket number, the form closes, and
the phone stores it:

```javascript
const data = await resp.json();
state.consultantRequestId = "FR-2026-080912610";
closeConsultantModal();
startCustomerPolling();          // ← begin listening for a takeover
```

That last line matters: from this moment the family's phone is checking every two
seconds whether a human has joined.

---

## Stop 6 — The console notices

**Nobody told the console anything.** It has been asking the same question every 5
seconds since the director signed in:

```javascript
consoleListPollTimer = setInterval(loadStaffDashboardData, 5000);
```

And each time:

```javascript
const resp = await fetch(`${API_BASE}/api/consultant-requests`);
const data = await resp.json();
```

On the server, that address runs:

```python
@app.get("/api/consultant-requests")
def list_consultant_requests():
    requests_list = load_consultant_requests()   # ← reads the file

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

And `load_consultant_requests()` is the mirror of the save function:

```python
def load_consultant_requests():
    if os.path.exists(CONSULTANT_REQUESTS_PATH):
        try:
            with open(CONSULTANT_REQUESTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading consultant requests:", e)
    return []
```

`"r"` = read mode. `json.load` turns the file's text back into a Python list.
If the file does not exist yet, it returns an empty list so the app still starts.

**It opens the same file Stop 5 wrote to**, and sends everything in it back.

Then the console throws away every card on screen and redraws them all:

```javascript
staffRequestsList.innerHTML = data.requests.map(req => `...card...`).join('');
```

Tan Wei Ming's ticket is in that data, so a card gets drawn. **That is all
"appearing in the dashboard" means.**

**Where has the data travelled?**

```
Family's browser → server → FILE → server → director's browser
```

The two browsers never touched.

**Practical consequence for the demo:** there can be up to a five-second gap between
submitting and the ticket appearing. That is normal, not a bug.

### Waiting time

The card also shows how long the family has been waiting, recalculated on every
redraw:

```javascript
function waitingUrgencyClass(isoString, status) {
  if (status !== 'WAITING') return 'text-creamMuted/70';
  const minutes = (Date.now() - new Date(isoString).getTime()) / 60000;
  if (minutes >= 15) return 'text-ember font-semibold';   // red
  if (minutes >= 5)  return 'text-brass font-semibold';   // amber
  return 'text-creamMuted';
}
```

Now, minus when the ticket was made, divided into minutes. Because the whole list is
rebuilt every five seconds, the number climbs on its own.

```
Lim Hui Ling      Waiting just now      ← grey
Tan Wei Ming      Waiting 9 min         ← amber
Rajesh Kumar      Waiting 22 min        ← red
```

A timestamp makes the director check the clock and subtract. "Waiting 22 min" is the
answer they actually wanted.

---

## Stop 7 — Marcus takes over

He clicks the button. The console sends:

```javascript
fetch(`${API_BASE}/api/consultant-requests/FR-2026-080912610/takeover`, { method: 'POST' })
```

The server changes three things and saves the file again. **This is the state
machine transition** — `mode` moving from AI to HUMAN is what silences the assistant
in Stop 9:

```python
@app.post("/api/consultant-requests/{request_id}/takeover")
def takeover_consultant_request(request_id: str):
    requests_list = load_consultant_requests()
    for req in requests_list:
        if req.get("request_id") == request_id:
            req["status"] = "IN PROGRESS"
            req["mode"] = "HUMAN"           # ← the important one
            req["assigned_staff"] = "Marcus Chen (Funeral Consultant)"

            req["conversation"].append({
                "role": "staff",
                "content": "Marcus Chen (Funeral Consultant) has joined the chat and taken over from AI Assistant.",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "sender": "System"
            })
            save_consultant_requests(requests_list)
            return req
```

The "has joined" notice is stored as a **message**, not just a field change, so the
transition shows up in the conversation the family is reading and stays in the
record afterwards. `"sender": "System"` is what makes the frontend draw it as a
centred line rather than a speech bubble.

---

## Stop 8 — The phone notices

The phone has been asking about *its own* ticket every 2 seconds:

```javascript
const resp = await fetch(`${API_BASE}/api/consultant-requests/FR-2026-080912610`);
const ticket = await resp.json();
state.conversationMode = ticket.mode;    // now "HUMAN"
```

Seeing `"HUMAN"`, three things happen at once:

```javascript
renderQuickChips();                          // 1. escalation chip disappears

if (ticket.mode === 'HUMAN') {
  banner.classList.remove('hidden');         // 2. green banner appears
} else if (ticket.mode === 'CLOSED') {
  clearInterval(state.customerPollTimer);
}

ticket.conversation.forEach(m => {           // 3. staff messages render
  if (m.role === 'staff' && !historyContents.includes(m.content)) {
    if (m.sender === 'System') appendSystemLine(m.content);
    else appendBubble(m.content, 'staff', m.sender);
    chatHistory.push({ role: 'assistant', content: m.content });
  }
});
```

**`!historyContents.includes(m.content)` is the dedupe check.** Every poll downloads
the *whole* conversation. Without this filter, the same message would render again
every two seconds forever.

**Why 2 seconds here but 5 in the console?** Someone waiting for a reply notices a
delay more than a director glancing at a queue.

---

## Stop 9 — The AI goes quiet

Now the family types "can I add catering?". It goes to the chat address as usual —
but the **first thing** that runs there is:

```python
if req.get("mode") == "HUMAN":
    req["conversation"].append({"role": "user", "content": "can I add catering?"})
    save_consultant_requests(requests_list)
    return ChatResponse(response="Your message has been delivered directly to your human consultant.")
```

**That `return` ends the function.** The AI code sitting below it never runs. The
message is saved to the file for Marcus instead.

This is the state machine being enforced. Stop 7 set `mode` to `"HUMAN"`; this check
reads it. One field written in one place, read in another — and that is the whole
mechanism by which a human takes over a conversation from an AI.

**Why position matters.** Every message from the family passes through this
function. If this check were further down, the AI might have already written a reply
before anyone asked whether it should.

**What breaks without it:** the family asks "can I add catering?" and gets *two*
answers — one from Hannah quoting $450/day, one from Marcus saying he will sort it
out. Confusing at best, contradictory if the AI's number is out of date.

| Family types | mode = AI | mode = HUMAN |
|---|---|---|
| "can I add catering?" | Hannah: *"Catering is $450 per day…"* | Saved for Marcus. AI says nothing. |

---

## Stop 10 — Marcus replies

```python
@app.post("/api/consultant-requests/{request_id}/message")
def send_staff_message(request_id: str, payload: StaffMessageSend):
    for req in requests_list:
        if req.get("request_id") == request_id:
            req["conversation"].append({
                "role": "staff",
                "content": payload.message,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "sender": payload.staff_name or "Marcus Chen"
            })
            save_consultant_requests(requests_list)
            return req
```

**This is the same `conversation` array the family's messages go into.** One record,
in order. If each side kept its own list you would have to merge them later and
reconcile timestamps — and any disagreement would show as messages in the wrong
order.

The family's phone picks it up on its next two-second check.

```json
"conversation": [
  { "role": "user",      "sender": "Tan Wei Ming",  "content": "Hi, I need a Buddhist package" },
  { "role": "assistant", "sender": "AI Assistant",  "content": "Our Buddhist Ceremony Rites..." },
  { "role": "staff",     "sender": "System",        "content": "Marcus Chen has joined the chat" },
  { "role": "staff",     "sender": "Marcus Chen",   "content": "Hello Mr Tan, I have your..." }
]
```

---

## Stop 11 — Closing

```python
req["mode"] = "CLOSED"
req["status"] = "RESOLVED"
save_consultant_requests(requests_list)
```

On the family's next two-second check, the `CLOSED` branch fires and
`clearInterval(state.customerPollTimer)` stops the phone asking.

**Why stop?** A finished conversation has nothing left to look for. Otherwise every
resolved ticket leaves a browser pinging the server every two seconds forever.

**Why mark it resolved instead of deleting it?** The record is the point — a funeral
company needs to know what was said and by whom. Resolved tickets stay in the console
under their own counter.

> Your consultant has completed the session and marked this request as resolved.
> Thank you for speaking with Solace Dignity Care.

---

## The whole journey in one picture

```
"Tan Wei Ming"  typed into the form
       │
       │  fetch POST
       ▼
   main.py  builds the ticket
       │
       │  save_consultant_requests()  →  "w" mode
       ▼
consultant_requests.json    ← a real file on your disk
       ▲                    │
       │  load()            │  load()
       │                    ▼
   main.py              main.py
       ▲                    │
       │  fetch every 2s    │  fetch every 5s
       │                    ▼
Family's phone        Director's console
```

---

## The one sentence

**The family writes to a file. The director reads from that file. Neither knows the
other exists.**

Everything else — the modes, the summary, the polling — is detail hanging off that.

---

## Questions to have ready

**"Why polling instead of the server telling you?"**
The proper answer is WebSockets, but at this scale asking every two seconds looks
identical and avoids reconnection logic, heartbeats, and a second server process.

**"Why fetch the whole list every time?"**
Simpler than tracking what changed, and with a handful of tickets the cost is
nothing. A production system would paginate.

**"Why a JSON file instead of a database?"**
The prototype proves the workflow, not the storage engine. Reading and writing happen
in two functions, so swapping to SQLite would touch only those two.

**"What was the hardest part?"**
Server-side state. Features 1 and 2 answer and forget. This one has to know, at every
moment, which of two participants is allowed to speak — and the `mode` check at the
top of `/api/chat` is that entire idea in one condition.

**"What would you improve?"**
`takeover` has no guard — it does not check whether `assigned_staff` is already set,
so two directors could claim the same ticket, or one double-click appends two "joined"
notices. A single `if` statement would fix it.
