# Two tools instead of hundreds of manual edits

## The problem, as your screenshots show it

In screenshot 14 the bottom nav (家庭中心, 方案策划) and the price bar
(实时动态报价总额, 生成并审阅报价单) are Chinese, but the add-on cards directly
above them are English. In screenshot 15 the header is Chinese while Hannah's
greeting and every quick-reply chip are English.

Same cause both times: `setLanguage()` walks `[data-i18n]`, which only exists
on static HTML. Everything a renderer builds after page load has no attribute,
so it is never touched.

Fixing that by hand means editing every renderer, and every renderer written
later reintroduces the bug.

---

## Tool 1 — `i18n_extract.py` (static HTML, one-time)

Scans `index.html`, injects `data-i18n` / `data-i18n-placeholder` /
`data-i18n-aria` attributes, and produces a translation worksheet.

```
python i18n_extract.py --scan     # report only, changes nothing
python i18n_extract.py --apply    # inject attributes, write stub + CSV
```

Current result: **45 strings** (11 aria-labels, 3 placeholders, 31 text nodes).

It deliberately skips:
- the director console (staff tool, stays English)
- runtime placeholders — "Jane Doe", "USR-20260825-007", dates, "@user"
- technical values — "PBKDF2-SHA256 (260k)"
- **language endonyms** — a Tamil speaker looks for "தமிழ்" in the switcher,
  not a translation of it
- anything already carrying `data-i18n`

`--apply` writes `i18n_worksheet.csv` with one row per string and empty
columns for Chinese, Malay and Tamil. Hand that to a translator; they never
touch code.

**Run `--scan` first and read the list.** It is a regex tool, not a parser —
it will occasionally catch something it should not.

---

## Tool 2 — `i18n_auto.js` (dynamic content, permanent)

This is the piece that actually solves your problem.

Add after `app.js`:

```html
<script src="app.js"></script>
<script src="i18n_auto.js"></script>
```

How it works:

1. Builds a reverse map, English string → dictionary key, from
   `I18N_TRANSLATIONS.en`.
2. Walks text nodes. Any node whose text exactly matches a known English
   string gets translated — **no `data-i18n` attribute needed**.
3. Caches the original English in `data-i18n-src` before replacing, so
   repeated switching keeps working.
4. A `MutationObserver` re-runs on newly inserted subtrees, so content
   rendered *after* a switch is translated as it appears.

Verified: injecting a card while Tamil is active produced
`பொதுவான கேள்விகள்` with no renderer changes. Switching
zh → ms → ta → en → zh returned the correct string every time.

Console exclusion verified: the same English string injected inside
`#staff-dashboard-modal` stayed English while the copy outside it became
Chinese.

### Debugging helper

```js
window.__i18nAudit()
```

Lists every visible English string with no dictionary entry. Run it on each
screen in each language to find what is still missing. It currently reports
**87** strings.

### What it is not

Exact-match only. No fuzzy matching, no partial replacement, no machine
translation. A string absent from the dictionary is left alone. It is a
safety net, not a licence to stop adding keys.

Strings under 4 characters are skipped — "None", "OK" and similar would match
too loosely and change text in unrelated places.

Opt out of any subtree with `data-i18n-skip`. Use it on anything the family
typed themselves.

---

## Suggested order

1. `python i18n_extract.py --scan`, read the output.
2. `--apply`, then review the `index.html` diff before committing.
3. Add `i18n_auto.js` to `index.html`.
4. Merge `i18n_stub.json` into `I18N_TRANSLATIONS` once translations come
   back, keeping all four dictionaries key-for-key balanced.
5. Walk each screen in each language running `__i18nAudit()`, and add keys for
   what it reports.

The backend replies (`REPLY_STRINGS` in `main.py`) are a separate job and are
**not** covered by either tool. With Ollama down, a family who chose Tamil
still receives English — including the crisis message. See
`PROMPT_i18n_remaining.md`.

---

## One caution about the auto layer

It translates by matching English text. If two different UI elements use the
same English word with different intended meanings, both get the same
translation. The 4-character floor removes most of that risk, but if you hit a
case where context matters, give that element a real `data-i18n` key — an
explicit key always wins over the reverse-map guess.
