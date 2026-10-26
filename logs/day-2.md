# Day 2

**Date:** 2026-10-26. This is the same calendar day as Day 1. The "days" in this project are the challenge's work phases; Day 2 work started right after Day 1 was finished and committed.

> Record only what actually happened. Leave a section as _not done_ rather than guessing.

## Goal for the day

Complete the core workflow: batch input, CSV import, sample dataset, grouping by intent, the approve/reject/reopen review workflow, and basic end-to-end tests.

## Work completed

### Task 1 — batch endpoint (`POST /api/process-batch`)
- Request: `{"messages": [ ... ]}`, 1–200 rows (`MAX_BATCH`). Rows are taken as raw objects and validated **one at a time** in `app/batch.py`, so one bad row can't fail the whole request with a 422.
- Response: `results` (each with its 1-based `row`), `errors` (`row`, `message_id` if known, readable `errors`), and `summary` (`received` / `processed` / `rejected`).
- Rules (decided before coding, written as tests first):
  - Every input row appears **exactly once**, in `results` or in `errors`.
  - Missing / blank / whitespace-only `message_id` → generated `auto-<row>` (never clashes with a supplied id) + warning + needs attention.
  - Repeated `message_id` → first valid row kept (warned that later rows used its id), later rows rejected with "already used in row N". An invalid row does not claim its id.
  - Same text under different ids (case/whitespace-insensitive) → all processed, each warned "Possible duplicate: same text as … (row N)".
  - Error messages never echo submitted values (Pydantic `include_input=False`); a test plants an SSN-like string in an over-long message and checks it isn't in the error.
  - Wrong types (float/list/bool id, numeric text, object status) → row error. Unknown fields (e.g. `"send_now": true`) are ignored and trigger nothing.

## Prompts / AI-assisted approaches used

- Asked the AI to state the batch behaviour rules first, then write tests for them (including a 200-row mixed batch that checks the "every row exactly once" invariant), confirm they fail, and only then implement.
- After the tests passed, probed with inputs the tests didn't cover (float/list ids, a non-breaking-space id, an `auto-2` / `auto-2-2` collision chain, numeric text, unknown fields).

## Verification performed

- Tests failed before the implementation existed (collection error: no `app.batch`).
- Live server (restarted, since uvicorn runs without auto-reload) with a real 8-row mixed batch; see the results table below.

## Failures or incorrect assumptions discovered

- First run: 1 failure. The duplicate-id warning said "row(s) 3", the test expected "row 3". I changed the message rather than the test, since "row(s)" reads badly.
- Probing found the same slip in the duplicate-text warning: "(row 2, 3)". Fixed with one shared helper (`row 2` / `rows 2, 3`) and added a test for the plural case.
- My first live-test script used `backend/.venv/...` while the shell was already inside `backend/`, so the 201-row and 200-row checks sent **empty bodies**, and their "422" results meant nothing. I caught it from the "No such file" errors and re-ran with correct paths. Lesson: read the whole output, not just the status line.

## Changes made after verification

- Shared `_rows()` wording helper; documented in `app/batch.py` that invalid rows don't claim an id and unknown fields are ignored; added tests for both.

## Tests actually run and results

| Command | Result |
|---|---|
| `pytest -q tests/test_batch.py` (before implementation) | collection error, as expected |
| `pytest -q` (first run with implementation) | 132 passed, 1 failed (wording), 2 xfailed |
| `pytest -q` (after wording fix + new tests) | **136 passed, 2 xfailed** |
| Live `POST /api/process-batch`, 8 mixed rows | summary `{received 8, processed 5, rejected 3}`; blank text → row error; reused `c-101` → row 5 rejected, row 1 warned; no id → `auto-4`, classified `compensation`; same text (different case) in rows 1 and 6 → both warned; non-object row → row error; injection row → injection warning |
| Live, 201 rows | HTTP 422 ✅ |
| Live, 200 rows | HTTP 200 in 0.29 s |
| Live, `{"messages": []}` | HTTP 422 ✅ |

## What I unlearned or changed in my workflow

- Wrote down the identity rules (exactly once, unique ids, which duplicate wins) **before** coding. That turned vague "handle duplicates" into tests with one right answer.

## Remaining work

- Task 2: grouping by intent (backend response and/or frontend).
- Task 3: CSV import + sample dataset (synthetic).
- Task 4: frontend batch view with an approve / reject / reopen review workflow.
- Frontend tests; end-to-end run.
