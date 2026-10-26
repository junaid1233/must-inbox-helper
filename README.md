# Inbox Helper

A small recruiting tool that takes a batch of candidate messages, groups them by what each candidate wants, and drafts a short reply for each one. **A human reviews every draft. Nothing is ever sent.**

> **Drafts are never sent automatically. Human review is required.**
> The app has no email, messaging or "send" feature. "Approve" only marks text as ready for you to copy into your own email or messaging tool.

Built for the MUST "Unlearn, Use, Raise the Load" 5-day challenge. Background and decisions: [intent.md](intent.md), [Final directive.md](Final%20directive.md), daily logs in [logs/](logs/), stress results in [docs/stress-report.md](docs/stress-report.md).

## Features

- **Input:** paste messages (one per blank-line-separated paragraph), import a CSV, or load a 15-message synthetic sample.
- **Validation per row:** bad rows are listed with a plain-English reason; good rows still go through. Every row appears exactly once in the output.
- **Intent classification** into 10 categories, with a confidence *band* (high / medium / low; a heuristic, not a probability) and a reason.
- **Grouping** by intent, with counts and "needs attention" counts.
- **Reply drafts** (1–3 sentences) that never state an application status, outcome or date that wasn't supplied.
- **Human review:** edit, approve (locks the text), reject, reopen; edited / pending / approved / rejected shown on each card.
- **Warnings for the reviewer:** prompt-injection attempts, possible duplicates, missing ids, unknown status, non-English text, conflicts between the message and supplied context, outcome wording in a draft, provider failures.
- **Demo mode:** a deterministic mock provider; no API key or network needed.

## Architecture

```
frontend/ (React + TypeScript + Vite)          backend/ (Python + FastAPI + Pydantic)
  InputPanel  paste / CSV / sample   ──HTTP──▶  main.py        endpoints, error handler, logging
  BatchView   groups, row errors                batch.py       per-row validation, ids, duplicates
  MessageCard draft + review actions            csv_import.py  CSV → records (strict quoting)
  review.ts   review state (no network)         pipeline.py    provider call + safety checks
                                                providers/     AIProvider interface, MockProvider
                                                validation.py  checks provider output
                                                safety.py      prompt-injection signals
                                                checks.py      language + conflict checks
                                                grouping.py    group results by intent
```

Provider output is treated as untrusted: it's parsed and validated before anything reaches the UI, and a timeout, error or malformed output becomes a flagged result with no draft, never a crash. Candidate text is treated as data, never as instructions.

## Prerequisites

- **Python 3.12** (3.12.10 used).
- **Node.js 22.13+** (22.13.1 used) and npm 10.
- Git.

**Verified on:** Windows 11 with Git Bash (the fresh-clone check is in [logs/day-4.md](logs/day-4.md)). macOS/Linux commands are given below but **have not been run**.

## Installation

```bash
git clone <repo-url> must-inbox-helper
cd must-inbox-helper
```

### Backend

Windows (Git Bash):

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

macOS / Linux (not verified):

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On Windows, use `python`, not `py` or `python3`: on the development machine `py` pointed at a missing Python and `python3` opened the Microsoft Store.

### Frontend

```bash
cd frontend
npm ci
```

## Environment setup

No configuration is needed for demo mode. Optionally copy `.env.example` to `.env` (repo root or `backend/`):

| Variable | Default | Meaning |
|---|---|---|
| `AI_PROVIDER` | `mock` | Only `mock` exists. Any other value stops the backend at startup. |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Origin allowed by CORS. |
| `LOG_LEVEL` | `INFO` | Backend log level. |

`.env` is git-ignored. There are no secrets in this project today; a real LLM provider would read its key from an environment variable.

## Running

Use two terminals. Start the backend first.

**Backend** (port 8000), from `backend/`:

```bash
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

(macOS/Linux: `.venv/bin/python -m uvicorn app.main:app --port 8000`.) Check it: `curl http://localhost:8000/api/health` should return `{"status":"ok","provider":"mock","demo_mode":true,"sends_messages":false}`.

**Frontend** (port 5173), from `frontend/`:

```bash
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` to the backend on port 8000.

## Demo / mock mode

Demo mode is the default and the only mode. The badge in the header says **"Demo mode · mock provider"**. The mock classifies with English keyword rules and writes template replies, so:

- the same input always gives the same output (good for tests and demos);
- it misses a lot of indirect phrasing: **55% accuracy** on 40 held-out messages, but **none confidently wrong** (misses land in "Other or unclear" and are flagged). See [docs/stress-report.md](docs/stress-report.md).

Quick demo: open the **Sample data** tab → **Load sample dataset**, then edit, approve and reject a few drafts.

## Running tests

Backend, from `backend/`:

```bash
.venv/Scripts/python -m pytest -q
```

Frontend, from `frontend/`:

```bash
npm test
npm run build
```

`npm run build` also type-checks. No test calls a real AI service or needs a network connection.

Classifier measurement (not a pass/fail test), from the repo root:

```bash
backend/.venv/Scripts/python eval/run_heldout.py
```

## Sample input format

**CSV:** a header row with a message column named `text`, `message` or `body`. Optional columns: `message_id` (or `id`), `candidate` (or `name`), `received_at`, `application_status` (or `status`), `context` (or `notes`). Unknown columns are ignored. Comma, semicolon or tab separated; up to 200 rows and 1 MB. Quote any field containing a comma.

```csv
message_id,candidate,application_status,text
c-001,Priya Raman,,"Hi, is there any update on my application?"
c-002,Tomasz Nowak,Under review,"Just checking in on my QA Engineer application."
```

Only fill `application_status` and `context` with information you have verified; drafts may repeat them.

**JSON** (`POST /api/process-batch`):

```json
{"messages": [{"message_id": "c-001", "candidate": "Priya Raman", "text": "Any update on my application?"}]}
```

Examples: [sample_data/messages.csv](sample_data/messages.csv), [sample_data/messages.json](sample_data/messages.json), and a deliberately broken [sample_data/malformed.csv](sample_data/malformed.csv).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Provider and mode; always `sends_messages: false` |
| GET | `/api/intents` | Intent labels |
| GET | `/api/sample` | The synthetic sample dataset |
| POST | `/api/process` | One message → result |
| POST | `/api/process-batch` | 1–200 messages → results, groups, row errors, summary |
| POST | `/api/process-csv` | `{"csv": "..."}` → same as batch; file problems → HTTP 400 |

There is no endpoint that sends, emails or approves anything; approval happens only in the browser.

## Known limitations

- **No real LLM provider.** Only the keyword mock is implemented and tested. Its recall is poor on indirect wording (55% on held-out messages).
- **Single intent per message.** A message asking two things gets one category.
- **Heuristic safety checks.** Prompt-injection, language and conflict detection are pattern-based and miss cases (e.g. non-English injection; conflicts other than dates/times and self-claimed outcomes). They add warnings; they are not guarantees. Human approval of every draft is the real control.
- **Review state is in memory only.** Reloading the page loses approvals (the page warns first). Nothing is stored in the browser, by design, to avoid keeping candidate data there.
- **Limits:** 5,000 characters per message, 200 messages per batch, 1 MB per CSV. One CSV cell over ~131,000 characters rejects the whole file.
- **Message ids are logged.** Logs never contain message text, names or drafts, but they do include `message_id`; don't use personal data (e.g. email addresses) as ids.
- **Verified only on Windows 11** with Python 3.12.10 and Node 22.13.1.

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI says "Could not reach the backend. Is it running on port 8000?" | Start the backend first; check `curl http://localhost:8000/api/health`. |
| Backend exits with `AI_PROVIDER='…' is not supported yet` | Remove `AI_PROVIDER` from `.env` or set it to `mock`. |
| `npm run dev` fails with "Port 5173 is already in use" | Another dev server is running; stop it (the port is fixed so the backend's CORS setting matches). |
| `py` or `python3` doesn't work on Windows | Use `python`. |
| `npm ci` prints `EBADENGINE` | Your Node is older than 22.13; upgrade Node. |
| CSV import says a line "has N values but the header has M" | A field contains an unquoted comma; wrap that field in double quotes. |
| CSV import says "Could not read the CSV near line N" | A quote isn't closed; the file is refused rather than guessing where rows end. |
