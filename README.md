# Solace Dignity Care — 24/7 Conversational AI Sales Assistant & Automated Quotation Engine

**Project CP-004 · KLASS Engineering problem statement**
Higher Nitec in AI Applications · ITE College Central

A locally-hosted funeral-services assistant that helps bereaved families arrange a service
at any hour, produces an exact quotation, and hands over to a human consultant when needed.

Everything runs on your own machine. No family data is sent to any external service.

---

## Table of contents

1. [What you need before starting](#1-what-you-need-before-starting)
2. [Setup — step by step](#2-setup--step-by-step)
3. [Running the application](#3-running-the-application)
4. [Trying it out](#4-trying-it-out)
5. [Project structure](#5-project-structure)
6. [Configuration reference](#6-configuration-reference)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. What you need before starting

| Requirement | Minimum | Notes |
|---|---|---|
| **Operating system** | Windows 10 or 11 | Instructions below are for Windows |
| **Python** | 3.9 or newer | Tick **"Add Python to PATH"** during install |
| **Ollama** | Latest | Runs the local language model |
| **RAM** | 8 GB (16 GB recommended) | The model runs on CPU |
| **Free disk space** | ~10 GB | Model weights are large |
| **Internet** | First-time setup only | Needed to download packages and models. The app itself runs offline afterwards |

**Downloads:**
- Python — https://www.python.org/downloads/
- Ollama — https://ollama.com/download
- Git — https://git-scm.com/download/win

Check Python is installed by opening **Command Prompt** and running:

```
python --version
```

You should see `Python 3.9.x` or higher.

---

## 2. Setup — step by step

### Step 1 — Clone the repository

```
git clone https://github.com/stazerwee-ui/CP-004-AIPD-24-7-Conversational-AI-Sales-Assistant-Automated-Quotation-Engine.git
cd CP-004-AIPD-24-7-Conversational-AI-Sales-Assistant-Automated-Quotation-Engine
```



### Step 2 — Create a virtual environment

Keeps this project's packages separate from anything else on your machine.

```
python -m venv venv
venv\Scripts\activate
```

Your prompt should now start with `(venv)`.

### Step 3 — Install Python packages

```
pip install --upgrade pip
pip install -r requirements.txt
```

This takes a few minutes. It installs FastAPI, the speech models' runtimes, and the
embedding libraries.

### Step 4 — Create your `.env` file

The project reads its configuration from a `.env` file, which is **not** included in the
repository because it holds credentials.

```
copy .env.example .env
```

Now open `.env` in Notepad and set an admin token. Generate a strong one with:

```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste the result after `SOLACE_ADMIN_TOKEN=`. For example:

```
SOLACE_ADMIN_TOKEN=kJ8mN2pQ7rS4tU9vW1xY3zA5bC6dE0fG
```

> **Remember this value.** You will type it into the Director & Staff Portal to reach the
> staff console. Without it, the admin routes return `503`.

### Step 5 — Install and start Ollama, then pull the model

Install Ollama from the link above. It starts automatically as a background service on
Windows — you do **not** need to run `ollama serve`.

Pull the language model:

```
ollama pull qwen3.5:4b
```

Confirm it is available:

```
ollama list
```

You should see `qwen3.5:4b` listed.

### Step 6 — Download the speech and embedding models

These files are too large for GitHub (one is 311 MB), so they are downloaded here instead.

```
install_dependencies.bat
```

This fetches:
- `models/kokoro-v1.0.onnx` — neural text-to-speech (311 MB)
- `models/voices-v1.0.bin` — voice pack (27 MB)
- `tools/cloudflared.exe` — optional tunnel for remote demos

Then download the embedding model used for offline answers:

```
python scripts\prepare_offline_bundle.py --download
```

### Step 7 — Verify the setup

```
python scripts\prepare_offline_bundle.py --verify
```

This confirms the offline answer engine works with no network access.

---

## 3. Running the application

With the virtual environment active:

```
venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Then open your browser at:

```
http://127.0.0.1:8000
```

**To stop the server:** press `Ctrl + C` in the Command Prompt.

### Running it on your phone (optional)

**Option A — same Wi-Fi (quick).** Start the server bound to all interfaces:

```
uvicorn main:app --host 0.0.0.0 --port 8000
```


Find your computer's local IP with `ipconfig`, then open `http://YOUR-IP:8000` on a phone
connected to the same Wi-Fi.

Note that the **microphone will not work** over a LAN IP. Browsers only grant microphone
access on `https://` or `localhost`, so voice input is unavailable this way. Use Option B
to demonstrate the voice features.

**Option B — HTTPS tunnel (needed for voice).** Run:

```
start_live_demo.bat
```


This starts the backend if it is not already running, then opens a Cloudflare tunnel and
prints an `https://...` address. Open that address on the phone. Because it is HTTPS, the
microphone and speech-to-text work normally.

The tunnel exposes the local server publicly for the duration of the demo, so close the
window when finished. It is a demonstration convenience only — the AI models, the database
and all family data still stay on the host machine.

---
---


## 4. Trying it out

### As a family member

1. Enter a name and a phone number or email on the entry screen
2. Choose a starting point from the four tiles on the Family Hub
3. Ask the assistant anything, or start the guided setup
4. Build an arrangement in the Planner and watch the price update
5. Sign the quotation on the E-Sign screen and download the PDF

**Things worth trying:**
- Ask *"how much is a Buddhist 3-day funeral?"* — the price comes from deterministic Python, never the language model
- Tap the microphone and speak — transcription runs locally via Whisper
- Tap the speaker icon on any reply — the voice is generated locally via Kokoro
- Switch language using the selector — English, 中文, Bahasa Melayu, தமிழ்
- Say *"I want to speak to a human"* — this escalates to a consultant

### As a director

1. On the entry screen, click **Director & Staff Portal**
2. Enter the `SOLACE_ADMIN_TOKEN` value from your `.env`
3. View escalated tickets, take over a conversation, and reply to the family live

---

## 5. Project structure

```
codes25aug2026/
├── main.py                     FastAPI backend — all API endpoints
├── app.js                      Frontend logic (vanilla JavaScript)
├── index.html                  Single-page interface
├── style.css                   Styling
├── semantic_router.py          Intent classification across 7 routes
├── offline_answers.py          Vector search fallback when Ollama is unavailable
├── i18n_auto.js                Dynamic translation of runtime-rendered content
├── requirements.txt            Python dependencies
├── .env.example                Configuration template (copy to .env)
├── install_dependencies.bat    Downloads model weights
├── data/                       Catalogue, FAQs, pricing rules (19 JSON datasets)
├── scripts/                    Offline bundle preparation and verification
├── models/                     Downloaded model weights (not in the repository)
└── docs/                       Feature documentation
```

### How the pricing guarantee works

Prices are calculated by deterministic Python arithmetic in `/api/calculate`, using values
read from `data/dataset.json`. The language model is never asked to produce a number. A
wrong price shown to a grieving family is a real harm, so this boundary is enforced in code
rather than by prompting.

### How offline operation works

If Ollama is unavailable, the assistant falls back to `offline_answers.py`, which does
vector search across 134 curated FAQs and articles with a similarity threshold and a margin
gate. It answers only when confident, rather than guessing.

---

## 6. Configuration reference

All settings live in `.env`. Copy `.env.example` and edit.

| Variable | Default | Purpose |
|---|---|---|
| `SOLACE_ADMIN_TOKEN` | *(none — required)* | Token for the director console and secure document access |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Where Ollama is listening |
| `OLLAMA_MODEL` | `qwen3.5:4b` | Model used for conversation |
| `APP_HOST` | `127.0.0.1` | Use `0.0.0.0` to allow phone access |
| `APP_PORT` | `8000` | Server port |

**`.env` is excluded from version control by `.gitignore`.** No credential appears anywhere
in the source code.

---

## 7. Troubleshooting

**`'python' is not recognised`**
Python is not on your PATH. Reinstall Python and tick *"Add Python to PATH"*.

**`'uvicorn' is not recognised`**
The virtual environment is not active. Run `venv\Scripts\activate` first.

**Admin console returns `503`**
`SOLACE_ADMIN_TOKEN` is missing from `.env`. Complete Step 4.

**Admin console returns `401`**
The token you typed does not match the one in `.env`. They must be identical.

**Chat replies are slow or say the AI is offline**
Check Ollama is running with `ollama list`. If the model is missing, run
`ollama pull qwen3.5:4b`. Replies take a few seconds on CPU — this is normal.

**`Error: listen tcp 127.0.0.1:11434: bind: Only one usage of each socket address`**
Ollama is already running as a Windows service. This message is harmless — you do not need
to run `ollama serve` at all.

**Microphone or voice playback does not work**
Browsers only allow microphone access over `https://` or `localhost`. Use
`http://127.0.0.1:8000` rather than your LAN IP when testing voice on a computer.

**Port 8000 already in use**
Run on a different port: `uvicorn main:app --port 8001`

---

## Notes on privacy

This project handles bereavement information, so several things are deliberate:

- **Nothing leaves the machine.** The language model, speech recognition and voice synthesis
  all run locally.
- **Uploaded documents** (such as death certificates) are stored outside the public web
  directory under opaque filenames, and are reachable only with a valid admin token.
- **NRIC and FIN numbers** are masked before any text reaches the model or the logs.
- **The database and uploaded documents are excluded from this repository** — they contain
  real records from testing and must not be published.
