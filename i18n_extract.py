#!/usr/bin/env python3
"""
i18n_extract.py — find untranslated strings in index.html, inject data-i18n
attributes, and emit a stub dictionary you only have to fill in.

WHY THIS EXISTS
---------------
Hand-editing several hundred elements is slow and error-prone. This does the
mechanical part: scanning, key naming, attribute injection, and producing a
translation worksheet. A human still supplies the actual translations.

WHAT IT DOES NOT TOUCH
----------------------
  - the director console (admin login + staff dashboard). Staff tool, stays
    English on purpose.
  - runtime placeholder data ("Jane Doe", "USR-...", dates, "@user")
  - technical values ("PBKDF2-SHA256 (260k)")
  - anything already carrying data-i18n

USAGE
-----
    python i18n_extract.py --scan          # report only, changes nothing
    python i18n_extract.py --apply         # inject attributes + write stubs
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "index.html")
OUT_STUB = os.path.join(HERE, "i18n_stub.json")
OUT_CSV = os.path.join(HERE, "i18n_worksheet.csv")

# Everything at or after this line is the director console. Staff tool.
CONSOLE_MARKER = 'id="admin-login-modal"'

# Text that looks like data, not UI copy.
SKIP_PATTERNS = [
    r"^[\d\s\.\,\:\-\/\$\+\%]+$",          # pure numbers / prices
    r"^@\w+$",                              # @username
    r"\b(USR|QT|SOL|DOC|CP)-\d",            # ids and project codes
    r"^\W+$",                               # punctuation / arrows / bullets
    r"^(PBKDF2|SHA|AES|RSA|HTTP)",          # crypto / protocol names
    r"^\d{1,2}:\d{2}",                      # times
    r"^\d{1,2}\s+\w{3}\s+\d{4}",            # "15 Jul 2026"
    r"^(Jane Doe|Marcus Chen|Kelvin|Hannah)",  # seeded demo names
    r"^&\w+;$",                             # bare HTML entity (&middot;)
    r"^[A-Z]{1,3}$",                        # EN / BM / ZH / SD initials
    # Language names in the switcher are endonyms. A Tamil speaker looking for
    # their language looks for "தமிழ்", not a translation of it. Leave them.
    r"(English|简体中文|Bahasa Melayu|தமிழ்)",
    r"^\d+-Tap$",                           # "1-Tap"
]

SKIP_TAGS = {"script", "style", "path", "svg", "title", "meta", "link"}


def slugify(text, prefix):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    s = "_".join(s.split("_")[:6])          # keep keys readable
    return f"{prefix}_{s}"[:52]


def should_skip(text):
    t = text.strip()
    if len(t) < 2:
        return True
    if not re.search(r"[A-Za-z]{2}", t):
        return True
    return any(re.search(p, t) for p in SKIP_PATTERNS)


def screen_prefix(line_no, bounds):
    for start, end, name in bounds:
        if start <= line_no < end:
            return name
    return "misc"


def find_bounds(html):
    """Locate screen boundaries so generated keys are namespaced sensibly."""
    marks = []
    for m in re.finditer(r'id="(screen-\d+|[a-z-]*modal)"', html):
        line = html[: m.start()].count("\n") + 1
        marks.append((line, m.group(1)))
    marks.sort()
    bounds = []
    for i, (line, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else 10**9
        short = name.replace("screen-", "s").replace("-modal", "").replace("-", "_")
        bounds.append((line, end, short))
    return bounds


def scan(html):
    console_line = html[: html.find(CONSOLE_MARKER)].count("\n") + 1 \
        if CONSOLE_MARKER in html else 10**9
    bounds = find_bounds(html)
    found = []
    seen_keys = {}

    for i, line in enumerate(html.split("\n"), 1):
        if i >= console_line:
            continue  # director console stays English
        # element with a simple text child
        for m in re.finditer(r"<(\w+)([^>]*)>([^<>{}]+)</\1>", line):
            tag, attrs, text = m.groups()
            if tag in SKIP_TAGS or "data-i18n" in attrs:
                continue
            t = text.strip()
            if should_skip(t):
                continue
            key = slugify(t, screen_prefix(i, bounds))
            n = seen_keys.get(key, 0)
            seen_keys[key] = n + 1
            if n:
                key = f"{key}_{n+1}"
            found.append({"line": i, "tag": tag, "kind": "text",
                          "key": key, "en": t})

        # placeholders
        for m in re.finditer(r'placeholder="([^"]{3,})"', line):
            if "data-i18n-placeholder" in line:
                continue
            t = m.group(1).strip()
            if should_skip(t):
                continue
            key = slugify(t, screen_prefix(i, bounds) + "_ph")
            found.append({"line": i, "tag": "input", "kind": "placeholder",
                          "key": key, "en": t})

        # aria-labels (screen reader users need these translated too)
        for m in re.finditer(r'aria-label="([^"]{3,})"', line):
            if "data-i18n-aria" in line:
                continue
            t = m.group(1).strip()
            if should_skip(t):
                continue
            key = slugify(t, screen_prefix(i, bounds) + "_aria")
            found.append({"line": i, "tag": "*", "kind": "aria",
                          "key": key, "en": t})

    return found


def apply(html, found):
    """Inject attributes. Works line by line, longest match first, so nested
    replacements on the same line don't clobber each other."""
    lines = html.split("\n")
    by_line = {}
    for f in found:
        by_line.setdefault(f["line"], []).append(f)

    for line_no, items in by_line.items():
        line = lines[line_no - 1]
        for f in sorted(items, key=lambda x: -len(x["en"])):
            if f["kind"] == "text":
                pat = f'<{f["tag"]}([^>]*)>({re.escape(f["en"])})</{f["tag"]}>'
                line = re.sub(
                    pat,
                    lambda mm: f'<{f["tag"]}{mm.group(1)} data-i18n="{f["key"]}">{mm.group(2)}</{f["tag"]}>',
                    line, count=1)
            elif f["kind"] == "placeholder":
                line = line.replace(
                    f'placeholder="{f["en"]}"',
                    f'data-i18n-placeholder="{f["key"]}" placeholder="{f["en"]}"', 1)
            elif f["kind"] == "aria":
                line = line.replace(
                    f'aria-label="{f["en"]}"',
                    f'data-i18n-aria="{f["key"]}" aria-label="{f["en"]}"', 1)
        lines[line_no - 1] = line
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.scan or args.apply):
        ap.print_help()
        return 0

    with open(HTML, encoding="utf-8", newline="") as fh:
        html = fh.read()

    found = scan(html)
    print(f"Found {len(found)} untranslated strings (console excluded)")
    kinds = {}
    for f in found:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    for k, v in sorted(kinds.items()):
        print(f"  {k}: {v}")

    if args.scan:
        for f in found[:40]:
            print(f'  L{f["line"]:<5} {f["key"]:<44} {f["en"][:44]}')
        if len(found) > 40:
            print(f"  ... and {len(found)-40} more")
        return 0

    # stub dictionary: English filled, others left empty for a human
    stub = {"en": {}, "zh": {}, "ms": {}, "ta": {}}
    for f in found:
        stub["en"][f["key"]] = f["en"]
        for lang in ("zh", "ms", "ta"):
            stub[lang][f["key"]] = ""
    with open(OUT_STUB, "w", encoding="utf-8") as fh:
        json.dump(stub, fh, ensure_ascii=False, indent=2)

    # worksheet a translator can fill in without touching code
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write("key,english,chinese,malay,tamil\n")
        for f in found:
            safe = f["en"].replace('"', '""')
            fh.write(f'{f["key"]},"{safe}",,,\n')

    with open(HTML, "w", encoding="utf-8", newline="") as fh:
        fh.write(apply(html, found))

    print(f"\nWrote {OUT_STUB}")
    print(f"Wrote {OUT_CSV}  <- give this to your translator")
    print("Injected attributes into index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
