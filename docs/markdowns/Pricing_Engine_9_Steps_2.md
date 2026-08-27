# Feature 2 - Pricing Engine: The 9 Steps

**Project CP-004 - Klass Dignity Care Portal**
Real-Time Dynamic Pricing Rules Engine

**Scenario used throughout:** the family has Standard selected and clicks **Premium**.

---

## The pipeline

```
[1 Event Listener] -> [2 Build Payload] -> [3 fetch / POST / stringify]
   -> [4 uvicorn + FastAPI] -> [5 Pydantic Validation] -> [6 Rules Engine]
   -> [7 GST + Rounding] -> [8 Response Back] -> [9 Display]
```

| Steps | Where it runs | Language |
|---|---|---|
| 1 - 3 | Browser | JavaScript |
| 4 - 8 | Local server | Python |
| 9 | Browser | JavaScript |

The two sides are separate programs. Text in JSON format is the only thing that
crosses between them.

---

## STEP 1 - Event listener

An event listener is code that waits for something to happen. Every option button in the
planner has one attached.

```javascript
    item.addEventListener('click', () => {
      state.tier = key;
      renderPlannerSelectors();
      recalculatePlannerPrice();
    });
```

What happens on click:

```
Before:  state.tier = 'standard'
Click Premium
After:   state.tier = 'premium'
```

`state` is the app's memory - a single JavaScript object holding every selection for the
whole session. This is where the input is **stored**.

---

## STEP 2 - Build the payload

`recalculatePlannerPrice()` **reads** from `state` and assembles a small parcel containing
only what the server needs.

```javascript
async function recalculatePlannerPrice() {
  const seq = ++calcSeqCounter;
  const payload = {
    tier: state.tier,
    religion: state.religion || 'christian',
    wakeDuration: state.wakeDuration,
    casket: state.casket,
    wakeLocation: state.wakeLocation || 'hdb',
    ashManagement: state.ashManagement || 'cremation',
    addons: state.addons
  };

  const response = await fetch('http://localhost:8000/api/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  if (seq === calcSeqCounter) {
    renderPriceFromBackend(data);
  }
}
```


### Why the `||` defaults matter

```javascript
wakeLocation: state.wakeLocation || 'hdb',
```

If the family has not chosen a venue yet, `state.wakeLocation` is `undefined`.

- Without `||`: sends `undefined`, Pydantic rejects it, no price appears
- With `||`: sends `'hdb'`, the request succeeds

The payload is where the data is cleaned before sending.

---

## STEP 3 - fetch, POST and stringify

```javascript
await fetch('http://localhost:8000/api/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

| Part | Meaning |
|---|---|
| `fetch` | The JavaScript command that sends a network request |
| the URL | `localhost` = this computer, `8000` = the port uvicorn listens on, `/api/calculate` = which function should handle it |
| `method: 'POST'` | "Here is data, process it". GET would only be asking for something |
| `headers` | Tells the server the body is JSON so it knows how to unpack it |
| `JSON.stringify` | Converts the JavaScript object into **text** |

### Why it must become text

A JavaScript object exists as memory addresses and internal structures that only make sense
inside that one running program. Networks carry text and bytes, not live objects. Python
would not understand a JavaScript object even if it could see it.

JSON is a text format both languages read, so it is the common ground.

What actually travels down the wire:

```
{"tier":"premium","religion":"taoist","wakeDuration":"5day","casket":"teak",
"wakeLocation":"hdb","ashManagement":"columbarium",
"addons":{"catering":true,"security":true}}
```

---

## STEP 4 - uvicorn and FastAPI

### uvicorn

uvicorn is the server program that **hosts** the backend. It listens on port 8000 and
receives the incoming request. That is its entire job at this point - it does not know or
care what the request is for.

Without uvicorn, `main.py` is just a file on disk. Nothing is listening.

### FastAPI, job one: routing

FastAPI reads the method and path of the request:

```
POST /api/calculate
```

Then checks its registry of endpoints:

```python
@app.get("/api/status")       # no
@app.get("/api/catalog")      # no
@app.post("/api/calculate")   # MATCH
@app.post("/api/chat")        # no
```

Result: `calculate_price()` is the function to run.

Without this step, every request arriving at port 8000 would land in one undifferentiated
pile with nothing to sort it.

### FastAPI, job two: converting text back to Python

```
text:    {"tier":"premium","addons":{"catering":true}}
Python:  {"tier": "premium", "addons": {"catering": True}}
```

Note `true` becomes `True` - JavaScript and Python spell booleans differently. FastAPI
handles that translation.

### A note on wording

FastAPI does not "turn the function into a web address". The function stays an ordinary
Python function. FastAPI **maps** the address `/api/calculate` to it, making it reachable
from outside. Giving someone a phone number does not turn them into a phone; it makes them
contactable.

---

## STEP 5 - Pydantic validation

### Where validation is triggered

These are the two lines that connect Step 4 to Step 5, at the top of `calculate_price()`
in `main.py`:

```python
@app.post("/api/calculate", response_model=PricingResponse)
def calculate_price(request: PricingRequest):
```

Reading them piece by piece:

| Piece | Meaning |
|---|---|
| `@app.post` | A decorator - a label attached to the function below it. Registers this function for POST requests |
| `"/api/calculate"` | The address. This is what FastAPI matched in Step 4 |
| `response_model=PricingResponse` | Declares the shape of the answer that will be sent back (see Step 8) |
| `def calculate_price(...)` | The function itself - this is the rules engine |
| `request` | The parameter name. Inside the function the data is read as `request.tier`, `request.casket`, and so on |
| `: PricingRequest` | A type annotation. **This is what triggers validation** |

The type annotation is the important part. Because the parameter is declared as a
`PricingRequest`, FastAPI automatically reads the incoming JSON, validates it against that
class, converts it into a Python object, and passes it in as `request`.

Pydantic is never called directly anywhere in the code. The annotation does it.

### The contract being checked

```python
class PricingRequest(BaseModel):
    tier: str
    religion: str
    wakeDuration: str
    casket: str
    wakeLocation: Optional[str] = "hdb"
    ashManagement: Optional[str] = "cremation"
    addons: Dict[str, bool]
```

| Sent | Result |
|---|---|
| `"tier": "premium"` | Passes |
| `"tier": 123` | Rejected - expected a string |
| `"tier"` missing entirely | Rejected - field required |
| `"addons": "catering"` | Rejected - expected name/true-false pairs |

If validation fails, the request is rejected immediately and **`calculate_price()` never
executes**.

Without Pydantic this would require manual `if` checks for every field on every request.
One class declaration replaces all of them.

---

## STEP 6 - The rules engine

Now FastAPI and Pydantic step aside and the project's own logic runs.

### The repeating pattern

Every component follows the same four moves: check it exists, look up the price, add it to
the subtotal, record the line item.

```python
    # 1. Base Service Tier
    tier_key = request.tier
    if tier_key not in PRICING_CONFIG["tiers"]:
        raise HTTPException(status_code=400, detail=f"Invalid service tier: '{tier_key}'")
    tier_info = PRICING_CONFIG["tiers"][tier_key]
    subtotal += tier_info["price"]
    breakdown.append(BreakdownItem(name=tier_info["name"], price=tier_info["price"], type="tier"))
```

Religion, venue, duration, casket and ash management all use this identical shape with a
different lookup table.

### Where the prices come from

`PRICING_CONFIG` is loaded from `dataset.json` when the server starts:

```python
PRICING_CONFIG = {
  "tiers": {
    "standard": {"name": "Standard Service Tier", "price": 3200},
    "premium":  {"name": "Premium Heritage Service", "price": 6800}
  }
}
```

So `"premium"` is a lookup, not a calculation. Prices come from data, not from code.

### Order matters

The wake duration is resolved **before** the venue and add-ons, because both are charged per
day and need the day count:

```python
days = duration_info["days"]      # "5day" -> 5
```

This is a real dependency, not just a style choice: the venue and the per-day add-ons cannot
be priced until the number of days is known. Resolving the duration first is what makes those
later calculations possible.

### The one piece of real branching logic

```python
    # 7. Addons
    for addon_key, is_selected in request.addons.items():
        if is_selected:
            if addon_key not in PRICING_CONFIG["addons"]:
                raise HTTPException(status_code=400, detail=f"Invalid addon key: '{addon_key}'")
            addon_info = PRICING_CONFIG["addons"][addon_key]
            
            if "price_per_day" in addon_info:
                cost = addon_info["price_per_day"] * days
                subtotal += cost
                breakdown.append(BreakdownItem(
                    name=f"{addon_info['name']} ({days} Days)", 
                    price=cost, 
                    type="addon"
                ))
            else:
                cost = addon_info["price_flat"]
                subtotal += cost
                breakdown.append(BreakdownItem(
                    name=addon_info["name"], 
                    price=cost, 
                    type="addon"
                ))
```

| Add-on | Type | 3-day wake | 5-day wake |
|---|---|---|---|
| Catering | per day, 450 | 1,350 | 2,250 |
| Overnight Security | per day, 250 | 750 | 1,250 |
| Memory Video | flat, 350 | 350 | 350 |
| A/C Tentage | flat, 900 | 900 | 900 |

Choosing a longer wake changes the catering cost automatically. The customer never has to
work that out.


### Running total for the example

```
Premium Heritage Service         6,800
Taoist Ceremony Rites           +2,500
Venue (HDB, 5 days)                 +0
5-Day Wake surcharge              +800
Teak Elegant Dignity Casket     +2,800
Columbarium Niche Placement     +1,200
Catering Service (5 Days)       +2,250     450 x 5
Overnight Security (5 Days)     +1,250     250 x 5
                              ---------
Subtotal                        17,600
```

---

## STEP 7 - GST and rounding

```python
tax = js_round(subtotal * 0.09)
total = subtotal + tax
```

```
17,600 x 0.09 = 1,584
TOTAL           19,184
```

### Why a custom rounding function

```python
def js_round(val: float) -> int:
    """JS Math.round implementation in Python (half-up rounding)."""
    return int(val + 0.5) if val >= 0 else int(val - 0.5)
```

| Value | Python `round()` | JavaScript `Math.round()` |
|---|---|---|
| 2.5 | 2 | 3 |
| 3.5 | 4 | 4 |

Python's built-in `round()` uses **banker's rounding**: on an exact half it rounds to the
nearest even number. That is a statistical convention, designed to avoid bias when summing
many rounded values. It is not what is expected on an invoice, where conventional half-up
rounding is the norm.

This is not a rare edge case in this project. Every price in the catalog is a round hundred,
so multiplying a subtotal by 0.09 very often lands exactly on a half.



| Subtotal | `js_round()` | Python `round()` |
|---|---|---|
| 2,650 | 239 | 238 |
| 3,650 | 329 | 328 |
| 4,050 | 365 | 364 |

The function name describes the behaviour it copies: JavaScript's `Math.round()` rounds half
away from zero, which is the conventional behaviour wanted here. The function itself is
ordinary Python and runs entirely on the server - the browser receives an already-rounded
figure.

This is a bug that was prevented before it could happen.

---

## STEP 8 - The answer travels back

The response shape is also declared and enforced:

```python
class BreakdownItem(BaseModel):
    name: str
    price: int
    type: str

class PricingResponse(BaseModel):
    subtotal: int
    tax: int
    total: int
    breakdown: List[BreakdownItem]
```

FastAPI converts the Python object back into text and sends it over port 8000:

```json
{
  "subtotal": 17600,
  "tax": 1584,
  "total": 19184,
  "breakdown": [
    { "name": "Premium Heritage Service", "price": 6800, "type": "tier" },
    { "name": "Taoist Ceremony Rites", "price": 2500, "type": "religion" },
    { "name": "Catering Service (5 Days)", "price": 2250, "type": "addon" }
  ]
}
```

The `breakdown` array is what allows the frontend to display an itemised list rather than
just a single number.

---

## STEP 9 - Display

```javascript
const data = await response.json();     // text back into a JS object
if (seq === calcSeqCounter) {           // is this still the newest request?
  renderPriceFromBackend(data);
}
```

### Why the sequence check

If the user clicks three options quickly, three requests are in flight at once, and they can
return out of order.

```
Request A (Premium) sent    seq = 1
Request B (Deluxe)  sent    seq = 2
Response B arrives    2 === 2   ->  displayed
Response A arrives    1 !== 2   ->  discarded
```

Without this guard, a slower older response could overwrite a newer price and show the
wrong total.

### What gets rendered

`renderPriceFromBackend(data)` then:

- builds the breakdown rows from `data.breakdown`
- sets the headline total from `data.total`
- resizes the budget bars
- saves the figures into `state` so the PDF quote can use them later

**Total round trip: 5 to 20 milliseconds**, which is why the price appears to update
instantly.

---

## Summary of responsibilities

| Step | Component | Responsibility |
|---|---|---|
| 1 | Event listener | Detect the click, store the choice in `state` |
| 2 | `recalculatePlannerPrice()` | Read `state`, build a 7-field payload |
| 3 | `fetch` + `JSON.stringify` | Convert to text, send as POST |
| 4 | uvicorn | Receive on port 8000 |
| 4 | FastAPI | Route to the right function, convert text to Python |
| 5 | Pydantic | Validate the data shape |
| 6 | `calculate_price()` | Look up and total each component |
| 7 | `js_round()` | Apply 9 percent GST with JavaScript-compatible rounding |
| 8 | FastAPI | Convert the result back to text and return it |
| 9 | `renderPriceFromBackend()` | Rebuild as a JS object and draw the breakdown |
