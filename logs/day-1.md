# Day 1

**Date:** 2026-10-26

> Record only what actually happened. Leave a section as _not done_ rather than guessing.

## Goal for the day

Define and prove: inspect the environment, write `intent.md`, set up the project skeleton, and build one working path from a single message → classification → draft (backend + minimal UI).

## Work completed

### Environment inspection
- The parent folder (`USA client zuhu/`) is not a git repo and holds unrelated client work (`Essence-Ai-App/`, a Laravel project with its own `.git`). No Inbox Helper code existed.
- Decision: build in a new sibling folder `must-inbox-helper/` with its own git repo, so nothing mixes with client work.
- Tooling found: Python 3.12.10 (`python`), pip 25.0.1, Node v22.13.1, npm 10.9.2, git 2.46. Not installed: pnpm, uv.
- `ANTHROPIC_API_KEY` is not set → mock provider will be the default.

### Task 1 — skeleton and documents
- `git init -b main` in `must-inbox-helper/`.
- `.gitignore` (excludes `.env*` except `.env.example`, venvs, `node_modules`, build output).
- `.gitattributes` (`eol=lf`) added after git warned it would convert LF→CRLF on this Windows checkout.
- `.env.example` with placeholders only: `AI_PROVIDER=mock`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `AI_TIMEOUT_SECONDS`, `FRONTEND_ORIGIN`.
- `intent.md`: problem, users, workflow, assumptions, scope, non-goals, success criteria, risks.
- Log templates `logs/day-1.md` … `day-5.md`. Days 2–5 are left blank on purpose.

### Task 2 — backend core (models, provider interface, mock provider, validation)
- `backend/` venv with pinned deps (`fastapi 0.162.0`, `pydantic 2.14.1`, `pytest 9.1.1`, …) in `requirements.txt`.
- `app/models.py`: `CandidateMessage` (strips whitespace; rejects empty text/id; caps length), `MessageResult`, `Intent` enum (10 categories).
- Confidence decision: a **band** (`high`/`medium`/`low`), not a number, so it can't be mistaken for a calibrated probability. The mock's bands come from keyword-match counts, documented in `app/providers/mock.py`.
- `app/providers/base.py`: `AIProvider.analyze(message) -> raw JSON str`. Providers are untrusted; everything they return goes through validation.
- `app/providers/mock.py`: deterministic keyword rules + template drafts. Echoes a candidate name only if it looks like a plain name. States an application status only if the input supplied one.
- `app/validation.py`: parses and checks provider output. Unknown intent → `other_or_unclear`; bad confidence → `low`; empty draft → no draft + warning; wrong `message_id` → rejected; outcome wording ("shortlisted", "hired", …) → warning.
- `app/pipeline.py`: `process_message` turns timeouts, provider errors, bad output and unexpected exceptions into a flagged result with no draft, instead of crashing. Logs ids and error types only, never message text.

## Prompts / AI-assisted approaches used

- Pasted the full challenge directive into Claude Code and asked it to inspect the workspace and propose a Day 1 plan **before** writing code. It reported findings and a 5-task plan; I approved the folder choice before anything was created.
- AI drafted `intent.md`, `.gitignore`, `.env.example` and the log template from the directive.
- Task 2: AI wrote the backend core and a first test suite. Tests were written against the directive's required behaviour, not against the implementation.
- **Separate AI review:** a second agent was given only the code and the requirements (not my opinion of it) and asked to find bugs, safety gaps and weak tests, confirming each by running code. It reported 9 findings plus weak tests; 6 were confirmed by running probes.

## Verification performed

- `git check-ignore -v .env backend/.env .env.example` → `.env` and `backend/.env` are ignored; `.env.example` hits the `!.env.example` negation, so it stays tracked.
- `git status --short` after staging → only the intended files; no `.env`.
- Registry access: `python -m pip index versions fastapi` returned 0.162.0; `npm view vite version` returned 8.3.5, `react` 19.3.1, `vitest` 5.0.5. So installs should work in Tasks 2 and 4 (not yet tried).

## Failures or incorrect assumptions discovered

- `py` launcher is broken on this machine (it points at a missing Python 3.13 install) and `python3` is the Microsoft Store stub. Only `python` works. README must use `python`, not `py` / `python3`.
- Git warned about LF→CRLF conversion → added `.gitattributes`.
- My pre-commit secret scan had a flag-order bug (`git grep ... --cached` → `fatal`), and I chained the commit after it, so the commit ran without a valid scan. Re-ran it correctly against `HEAD` afterwards: no matches. Lesson: don't chain a commit after a check without failing on the check's exit code.

### Task 2 failures
- **First suite: 41/41 passed on the first run, yet the code had real bugs.** Passing tests proved only that my tests matched my assumptions.
- My own probe of realistic messages found: a clear "reschedule my interview" got only `medium`; "remote + pay range?" tied → `other_or_unclear` with an awkward "share more detail" draft; a prompt-injection message got a safe draft but **no warning** (planned for Task 3); Spanish → `other_or_unclear` (expected limitation).
- The independent review found (all reproduced by new tests that failed before the fix — 21 failed, 2 errored):
  1. **Crash:** `json.loads` raises `RecursionError` (deeply nested `[[[[…`) and `ValueError` (5000-digit integer), which are not `JSONDecodeError` → escaped `process_message` and would kill a batch.
  2. **Outcome check easy to slip past:** "You have been selected", "offer you the job", "not to proceed", "Congrats!", "short listed", curly apostrophe `You’ve passed`, zero-width space inside "shortlisted" — none were flagged.
  3. A provider omitting `message_id` passed silently.
  4. Overlapping keywords double-counted (`pay` + `pay range`) → one phrase gave `high`.
  5. Trailing `\b` broke inflections ("withdraw**ing**" matched nothing); "status of my application for the position" tied with role → unclear; withdrawal draft "we wish you all the best" read as confirming a withdrawal for "Should I withdraw or wait?".
  6. A recruiter-supplied status "Shortlisted" triggered the fabricated-outcome warning on every draft (alert fatigue).
  7. `logger.exception` would log tracebacks that can contain the candidate's text from SDK errors.
  8. Provider `reason`/`warnings` were unbounded.
  9. Name allow-list `À-ÿ` included `×` and `÷`.
  - Weak tests: `confidence in ("high","medium")` hid the real value; outcome tests matched several patterns at once, so a broken one wouldn't show.
- One "finding" didn't hold: "I accepted the offer" already classified as `offer`.
- **My fix for #5 conflicted with my fix for #4:** I added the phrase "status of my application", but the new overlap-merging folded it into "status", so it still counted once. Root cause was bare `role`/`position` matching context ("applied for the X role"); changed those to question-like phrasings and removed the useless phrase.
- Secret scan went wrong again at the Task 2 commit, three ways: (a) `--cached` in the wrong position again, but this time the commit was guarded on the exit code and **was correctly blocked**; (b) the pattern matched the log line quoting the regex itself (false positive); (c) my first `scripts/check-secrets.sh` read `$?` after an `if` with no `else`, so it reported a clean tree as a scan failure. Fixed by moving it into a script with a tighter key-shaped pattern, and testing both a clean tree (exit 0) and a staged fake `sk-ant-…` canary (exit 1, blocked).
- The reviewer's probe script saved over mine in the scratchpad (same filename). Its output showed two more missed phrasings ("through to the final interview", "extending an offer").

## Changes made after verification

- Added `.gitattributes`.
- Task 2: catch `ValueError`/`RecursionError` on parse, plus a catch-all around validation; NFKC + apostrophe + zero-width normalisation before outcome matching; widened outcome list; missing `message_id` → warning; overlapping matches merged; `withdraw\w*`, `accept(ed|ing)? the offer`; neutral withdrawal draft; supplied status excluded from the outcome check; `logger.warning` with type only; reason/warnings clipped to 300 chars and 10 items; name regex excludes `×÷`; tightened weak test assertions.
- `tests/test_review_regressions.py` keeps every finding as a regression test.

## Tests actually run and results

| Command | Result |
|---|---|
| `git check-ignore -v .env backend/.env .env.example` | `.env` files ignored; `.env.example` tracked ✅ |
| `python -m pip index versions fastapi` | 0.162.0 — PyPI reachable ✅ |
| `npm view vite version` | 8.3.5 — npm registry reachable ✅ |
| `git grep -nI -E "sk-ant-\|api[_-]?key\s*=\s*[A-Za-z0-9_-]{20,}" HEAD` | exit 1, no matches ✅ (first attempt errored, see above) |

| `pytest -q` (first Task 2 suite) | 41 passed |
| `pytest -q tests/test_review_regressions.py` (before fixes) | 21 failed, 4 passed, 2 errors — findings confirmed |
| `pytest -q` (after fixes, first run) | 66 passed, 1 failed (my conflicting fix) |
| `pytest -q` (after role-pattern change) | 66 passed, 1 failed (Priya test expected `medium`, now correctly `high`) |
| `pytest -q` (final) | **69 passed** |
| `sh scripts/check-secrets.sh` (clean tree) | exit 0, no matches ✅ |
| `sh scripts/check-secrets.sh` (staged fake `sk-ant-…` canary) | exit 1, blocked ✅ |

## What I unlearned or changed in my workflow

- Did not start by scaffolding everything. Inspected first, got a plan approved, and wrote the intent before any code.
- "All green on the first run" is now a signal to probe harder, not to move on. Reading real outputs and an independent review found 9 issues the green suite hid.
- Wrote failing regression tests from review findings **before** fixing, so each fix is proven, not assumed.

## Known limitations recorded so far

- The outcome-wording check is a word list and cannot be complete; new phrasings were still being found at the end of Task 2. Human approval of every draft is the actual control.
- The mock classifier is keyword-based: misses paraphrases and non-English text, and picks one intent for multi-intent messages.

## Remaining work (Day 1)

- Task 3: `POST /api/process` in FastAPI, checked with a real request; add prompt-injection detection/warning.
- Task 4: minimal Vite + React + TS page, checked in the browser.
- Task 5: finish this log.
