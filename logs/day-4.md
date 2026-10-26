# Day 4

**Date:** 2026-10-26, the same calendar day as Days 1–3 (the "days" are the challenge's work phases).

> Record only what actually happened. Leave a section as _not done_ rather than guessing.

## Goal for the day

Improve reliability and documentation: logging, friendlier errors, the pending `httpx2` question, `README.md`, `Final directive.md`, and a fresh-clone setup check following the README word for word.

## Work completed

- **Logging** (`app/logging_setup.py`): the `app` logger gets a handler and level from `LOG_LEVEL`. New lines: startup (`provider=mock sends_messages=False`), per-batch summary (counts + source), CSV file rejection. Policy unchanged: ids, counts and error types only.
- **Plain-English errors** (`app/errors.py`): keyed on Pydantic error *type*, not its wording ("Message text is empty.", "Message text is longer than 5,000 characters.", "Too many messages: the limit is 200 per batch.", "The request body is not valid JSON."). Used for batch/CSV row errors and a custom 422 handler. The handler also **stops FastAPI echoing the submitted input** in 422 responses (it can contain candidate text). The frontend now shows the message alone.
- **`httpx2`:** investigated (below); kept `httpx`, silenced only that warning with a dated comment.
- **`.env.example` was wrong:** it offered `AI_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` and `AI_TIMEOUT_SECONDS`, none of which exist (`anthropic` stops the backend at startup). Rewritten to list only real settings.
- **`README.md`** and **`Final directive.md`** written.
- **Fresh-clone check** (results below).

## Prompts / AI-assisted approaches used

- Asked the AI to check the `httpx2` suggestion against primary sources (Starlette's installed source, PyPI metadata) before deciding, instead of installing it because a warning said so.
- Re-read `Final directive.md` claim by claim against the code before committing; one claim was false (below).

## Verification performed

- New tests `tests/test_errors_and_logging.py` (row errors, 422 wording, no input echo, envelope errors, malformed JSON, log content).
- Fresh clone of the committed repo into a new folder; every README command run as written.

## Failures or incorrect assumptions discovered

- **`.env.example` documented a provider that doesn't exist**, written on Day 1 ahead of implementation and never revisited. A user following it would have had a backend that refused to start.
- **`Final directive.md` first draft claimed "warnings ≤ 10"**; only provider-supplied warnings are capped, and the system's own checks add more. Corrected before commit.
- **`httpx2` check:** Starlette 1.10's own `testclient.py` imports `httpx2` first and warns on `httpx`. PyPI: author Tom Christie (httpx's author), maintained by Pydantic Services Inc., source `github.com/pydantic/httpx2`, 22 releases since May 2026, **latest released 5 days earlier**, new transitive dependencies (`httpcore2`, `truststore`). Conclusion: legitimate, but not worth swapping a working test-only dependency right before submission. The suppression is documented in `pytest.ini`.
- My first warning filter named `DeprecationWarning`; the class is `StarletteDeprecationWarning(UserWarning)`, so the filter didn't match. Fixed by matching the message only.
- **Fresh-clone side note:** stopping the background `npm run dev` job left its Vite child (`node … vite.js`, PID 6708) listening on 5173. I checked its command line to confirm it was the clone's server before stopping it. This is an artefact of how my tool stops background jobs; Ctrl+C in a normal terminal stops both.

## Changes made after verification

- `Final directive.md` warnings row corrected; `pytest.ini` filter fixed.

## Tests actually run and results

| Command | Result |
|---|---|
| `pytest -q` (after errors + logging) | 262 passed, 2 xfailed, 1 warning |
| `pytest -q` (after warning filter fix) | **262 passed, 2 xfailed**, no warnings |
| `npx vitest run` / `npm run build` | 19 passed / OK |
| **Fresh clone** `python -m venv .venv` + `pip install -r requirements.txt` | OK (pip upgrade notice only) |
| Fresh clone `pytest -q` | **262 passed, 2 xfailed** |
| Fresh clone `npm ci` | 98 packages, **0 EBADENGINE** |
| Fresh clone `npm test` / `npm run build` | **19 passed** / OK |
| Fresh clone `uvicorn app.main:app --port 8000` + `curl /api/health` | exactly the README's documented response |
| Fresh clone `npm run dev` + `curl :5173/api/health` | proxied response OK |
| Fresh clone `eval/run_heldout.py` | same as Day 3 (17 safe misses, 0 confidently wrong) |
| Browser against the fresh clone | badge + notice shown; sample → 15 processed, 10 groups; approve s-001 → "Approved for use. Not sent…"; CSV with an empty row → "Row 2 (f-2): Message text is empty." |
| Fresh clone server log | startup line, `injection signals message_id=s-011`, two `batch processed …` lines; **no message text or names** ("walrus" and "Walrus Person" absent) |

## What I unlearned or changed in my workflow

- Treated documentation as code that can be wrong: `.env.example` and one claim in the directive were false, and only checking them against the running system found it.
- "A warning told me to install X" is not a reason to install X, and "it's probably fine" is not a reason to ignore it. Checking the source and package metadata took minutes and gave a decision I can defend.
- The fresh clone, run strictly from the README, is the only setup test that counts; my working folder had a manually upgraded pip and an extra launch config that a new user wouldn't have.

## Remaining work

- Day 5: full end-to-end run, final test suite, complete logs, `unlearning-note.md`, Loom script; the recording itself is yours to make.
- Not planned: a real LLM provider (no API key).
