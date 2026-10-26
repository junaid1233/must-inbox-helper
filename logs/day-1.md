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

## Prompts / AI-assisted approaches used

- Pasted the full challenge directive into Claude Code and asked it to inspect the workspace and propose a Day 1 plan **before** writing code. It reported findings and a 5-task plan; I approved the folder choice before anything was created.
- AI drafted `intent.md`, `.gitignore`, `.env.example` and the log template from the directive.

## Verification performed

- `git check-ignore -v .env backend/.env .env.example` → `.env` and `backend/.env` are ignored; `.env.example` hits the `!.env.example` negation, so it stays tracked.
- `git status --short` after staging → only the intended files; no `.env`.
- Registry access: `python -m pip index versions fastapi` returned 0.162.0; `npm view vite version` returned 8.3.5, `react` 19.3.1, `vitest` 5.0.5. So installs should work in Tasks 2 and 4 (not yet tried).

## Failures or incorrect assumptions discovered

- `py` launcher is broken on this machine (it points at a missing Python 3.13 install) and `python3` is the Microsoft Store stub. Only `python` works. README must use `python`, not `py` / `python3`.
- Git warned about LF→CRLF conversion → added `.gitattributes`.
- My pre-commit secret scan had a flag-order bug (`git grep ... --cached` → `fatal`), and I chained the commit after it, so the commit ran without a valid scan. Re-ran it correctly against `HEAD` afterwards: no matches. Lesson: don't chain a commit after a check without failing on the check's exit code.

## Changes made after verification

- Added `.gitattributes`.

## Tests actually run and results

| Command | Result |
|---|---|
| `git check-ignore -v .env backend/.env .env.example` | `.env` files ignored; `.env.example` tracked ✅ |
| `python -m pip index versions fastapi` | 0.162.0 — PyPI reachable ✅ |
| `npm view vite version` | 8.3.5 — npm registry reachable ✅ |
| `git grep -nI -E "sk-ant-\|api[_-]?key\s*=\s*[A-Za-z0-9_-]{20,}" HEAD` | exit 1, no matches ✅ (first attempt errored, see above) |

No application tests yet; there is no application code yet.

## What I unlearned or changed in my workflow

- Did not start by scaffolding everything. Inspected first, got a plan approved, and wrote the intent before any code.

## Remaining work (Day 1)

- Task 2: Pydantic models, `AIProvider` interface, deterministic `MockProvider`, output validation, pytest.
- Task 3: `POST /api/process` in FastAPI, checked with a real request.
- Task 4: minimal Vite + React + TS page, checked in the browser.
- Task 5: finish this log.
