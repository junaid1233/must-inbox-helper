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

### Task 2 — grouping by intent
- `app/grouping.py`: `group_results()` returns one group per intent that has messages: `intent`, `label`, `count`, `needs_attention_count`, `message_ids`. Groups follow the fixed `Intent` order (`other_or_unclear` last), members keep input order, empty groups are left out.
- Groups hold **ids, not copies**, so each result exists once (in `results`) and can't drift out of sync with its group.
- `BatchResponse` gains `groups`. Rejected rows are not grouped; they stay in `errors`. Provider failures land in `other_or_unclear`.

### Task 3 — CSV import and sample dataset
- `sample_data/messages.json`: 15 synthetic messages covering every intent plus hard cases: missing status, a supplied status, prompt injection, vague text, Spanish, a message that contradicts its context (s-014), a fake `555-` phone number, and an exact duplicate (s-015 = s-001 under a different id).
- `sample_data/messages.csv` is **generated from the JSON** with Python's `csv` writer, so the two can't drift and quoting is correct (a test asserts they match). `sample_data/malformed.csv`: hand-written broken file with its expected outcome fixed in a test.
- `app/csv_import.py`: header aliases (`message`/`body` → `text`, `name` → `candidate`, `id` → `message_id`, `status`, `notes`, …), unknown columns ignored, Excel BOM stripped, `,` / `;` / tab delimiter detected from the header, blank lines skipped, **`strict=True` quoting**. File-level problems → `CsvFileError` (HTTP 400 with a plain message). Row with the wrong number of values → row error with an "unquoted comma?" hint. More than 200 rows → rejected, never truncated. Error text never includes cell values.
- `process_batch(..., row_problems=...)` lets the importer report unparseable rows through the same `errors` list, so the "every row exactly once" rule still holds.
- Endpoints: `POST /api/process-csv` (`{"csv": "..."}`, ≤ 1 MB) and `GET /api/sample`.

### Task 4 — batch review UI with approve / reject / reopen
- `frontend/src/review.ts`: review state as **pure functions** with no network access. Rules: every draft starts `pending`; **approve** only while pending and only with non-blank text, and it **locks** the draft; **reject** only while pending; **reopen** returns approved/rejected to pending **keeping the edited text**; edits only while pending; invalid actions are no-ops. "Edited" = current text ≠ generated text.
- `InputPanel.tsx`: tabs for **Paste** (one message per blank-line-separated paragraph), **Import CSV** (file input, 1 MB check, column help) and **Sample data**.
- `BatchView.tsx` / `MessageCard.tsx`: summary (received / processed / rejected) and live review counts; "show only messages that need attention" filter; "Rows not processed" list; one section per intent group. Each card shows the original message, known status/context, confidence band + reason, attention reasons, an editable draft, and actions. Approved cards say **"Approved for use. Not sent: copy it into your own email or messaging tool."** with Copy and Reopen.
- Backend: batch results now include the validated `message`, so the reviewer sees exactly what each draft answers (CSV rows are parsed server-side, so the browser didn't have the text).
- Review state is **in memory only**. Decision: storing candidate messages in `localStorage` would leave PII in the browser, so instead the page warns before unload when there's review work, and asks before a new batch replaces the current review.
- Frontend tests: Vitest 5 + Testing Library + jsdom. `review.test.ts` (state rules, paste parsing) and `App.test.tsx` (the full flow with `fetch` mocked).

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

### Task 2 findings
- Grouping tests (written first) passed on the first run. Since grouping is a simple bucket step, I probed what actually decides whether groups are useful: **classification of paraphrased messages**. One realistic message per category, none written to match the keywords: **6/10 correct**. All 4 misses went to `other_or_unclear` / low / flagged (the intended safe failure, not a wrong category):
  - "where my application **stands**" → missed. **Real bug:** the rule was `where … stand` + trailing `\b`, the same inflection bug the reviewer found with "withdrawing" on Day 1, which I hadn't fixed everywhere. Fixed (`stand(s|ing)?`); regression test fails without the fix and passes with it.
  - "I **interviewed** with Maria … next steps", "I **sent** my application through the portal … did it come through?", "decided to **take another job**, please take me out of the process" → missed. **Deliberately not fixed:** adding keywords for exactly the messages I just tested would overfit and inflate the score. Kept as a baseline; Day 3 will measure on a fresh, unseen set.
- Live batch: **every processed message (5/5) needed human attention.** If everything is flagged, the flag can't help anyone prioritise. Most flags come from "medium confidence" and "status not provided". Open design question for Day 3/4: split the flag into "must check" (injection, outcome wording, provider failure, unclear intent) vs "informational".

### Task 3 findings
- **Why `strict=True` matters (checked, not assumed):** for `x1,"unterminated quote` followed by rows x2 and x3, Python's default CSV mode returned **one** record whose text contained x2 and x3. Two messages lost, no error. Strict mode raises "unexpected end of data". Kept as a regression test.
- First run: 1 failure, in my test. The regex `more than one` was case-sensitive and the message starts "More". Fixed the test.
- Probing unseen inputs: **tab-separated text** (as pasted from a spreadsheet) was reported as "no message text column", which is misleading. Fixed by detecting tab as well as `;`, with a test. CRLF line endings, an Excel trailing comma and quotes inside unquoted fields all parsed correctly.
- Accepted, not fixed (documented): NUL bytes pass through into text (harmless, since drafts never include message text); one cell over 131,072 characters rejects the whole file (the csv module can't resume; messages are capped at 5,000 anyway); formula-like cells (`=HYPERLINK…`) aren't a risk because the app never exports CSV.
- Sample dataset results: the contradiction case **s-014** ("interview is tomorrow at 2pm" vs context "Monday 3 November, 10:00") lands in `other_or_unclear` with **no warning about the contradiction**. Contradiction detection doesn't exist yet; Day 3 stress case. 8 of 15 sample messages are flagged for attention.
- A row that fails CSV parsing reports `message_id: null` even when its first cell holds a readable id (e.g. `m-002`). Minor; noted for Day 4.

### Task 4 findings
- **Node engine mismatch:** `jsdom@30.1.3` and its dependencies require Node ≥ 22.19 (some ≥ 22.22.2); this machine has **22.13.1**. npm only warns, and the non-DOM tests happened to pass, but running on an unsupported engine isn't verification. Rather than change the system Node, I pinned **`jsdom@29.1.1`** (`engines: ^22.13.0`). A clean `npm ci` now gives 0 `EBADENGINE` warnings.
- Frontend tests passed on the first run (18/18). **Mutation check of the key test:** I temporarily made "Approve draft" also call `fetch("/api/send")`. The "never makes a network request" test **failed** (`expected 4 to be 3`), then passed again after restoring the file. So the test really guards the no-send rule.
- **Accessibility, found in the browser:** the sample batch had **15 buttons all named "Approve draft"**, so a screen-reader user listing buttons can't tell them apart. Every action button now has a name that says which message it acts on ("Approve draft for Priya Raman (s-001)"); visible text unchanged; test added.
- **Attention noise I introduced:** every pasted message was flagged "No message_id supplied", because pasted text never has ids. The paste parser now assigns `paste-1…`, so the backend warning is kept for imports where an id was expected. Re-checked in the browser: 0 such warnings for pasted input.
- Grammar: "1 need attention" → "1 needs attention".
- My Python patch script for test updates mangled `\n` escapes in a heredoc, so it changed nothing (the 2 stale tests failed, correctly). Redid it with the Edit tool. Lesson: don't patch source through shell heredocs when escaping is involved.
- Removed CSS left over from the single-message page (`.layout`, `.row`, `.facts`).

## Changes made after verification

- CSV delimiter detection covers tab; tests for tab and CRLF.
- `where (i|my application) stand(s|ing)?` + regression test.
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
| `pytest -q tests/test_grouping.py` (before implementation) | collection error, as expected |
| `pytest -q` (with grouping) | 144 passed, 2 xfailed |
| Paraphrase probe, 10 messages (1 per intent) | 6/10 correct; 4 misses all → `other_or_unclear` (safe) |
| Regression test for "stands", with the fix stashed / restored | 1 failed / passes ✅ |
| `pytest -q` (after fix) | **145 passed, 2 xfailed** |
| Live batch (same 8 rows) | groups: status 2 (`c-101`, `c-106`), scheduling 1, compensation 1 (`auto-4`), unclear 1 (`c-108`); sum of counts 5 = processed; no id repeated; rejected rows absent from groups |
| `pytest -q` (with CSV tests, first run) | 175 passed, 1 failed (case-sensitive regex in my test), 2 xfailed |
| Lenient vs strict `csv.reader` on a stray quote | lenient: 1 record swallowing 2 rows; strict: `csv.Error` ✅ |
| `pytest -q` (after tab support) | **179 passed, 2 xfailed** |
| Live `POST /api/process-csv` with `messages.csv` | 15 received / 15 processed / 0 rejected; 10 groups (status 4: s-001, s-002, s-011, s-015; unclear 3: s-012, s-013, s-014); 8/15 need attention |
| Live `POST /api/process-csv` with `malformed.csv` | 7 / 3 / 4: line 3 "4 values … unquoted comma?", blank text, duplicate `m-004`, line 8 "1 value" (matches the expectation written beforehand) |
| Live CSV with no text column | HTTP 400 with plain message ✅ |
| Live `GET /api/sample` | 15 messages, s-001 … s-015 |
| `npm ci` with jsdom 30.1.3 / 29.1.1 | EBADENGINE warnings / **0** |
| `pytest -q` (batch results carry `message`) | 180 passed, 2 xfailed |
| `npx vitest run` (first run) | 18 passed |
| Mutation: Approve also calls `fetch` | "never makes a network request" test **fails** (`expected 4 to be 3`) ✅; restored → passes |
| `npx vitest run` (final) | **19 passed** |
| `npm run build` | OK |
| Browser: sample dataset | 15/15 processed, 10 groups; card shows original text, reasons, draft |
| Browser: edit + approve s-001 | "Edited", then "Approved", green, draft read-only, "Not sent…" note; **`/api/` request count unchanged (32 before and after)** |
| Browser: reject s-012 | "Rejected"; counts "13 pending · 1 approved · 1 rejected · 1 edited"; still 32 requests |
| Browser: CSV import of `malformed.csv` with review work present | confirmation asked first; 7 / 3 / 4 with the 4 row reasons listed; review reset to 3 pending |
| Browser: paste 3 paragraphs (+ a whitespace-only one) | "Process 3 messages"; multi-line message kept whole; ids `paste-1…` after fix, 0 "No message_id" warnings |
| Browser: 375 px | no element wider than the viewport; cards stack |

## What I unlearned or changed in my workflow

- Wrote down the identity rules (exactly once, unique ids, which duplicate wins) **before** coding. That turned vague "handle duplicates" into tests with one right answer.
- Resisted tuning keywords to the probe set I'd just seen. A probe is for measuring, and fixing exactly what it found would make the next measurement meaningless.

## End of Day 2 — status

**Done and verified:** paste / CSV / sample input → per-row validation → classification → grouping → editable drafts with approve / reject / reopen, entirely in demo mode. Approval was shown not to make any network request, by a test that was mutation-checked and by the browser network log. Tests: 180 backend (+2 known xfail), 19 frontend.

**Not done / open:**
- "Needs attention" is still set on most messages (8/15 of the sample); the must-check vs informational split is still open.
- Contradiction between message and context (s-014) isn't detected.
- No end-to-end test that drives the real browser against the real backend; the component tests mock `fetch`, and the live flow was checked by hand in the browser pane.
- Review state is lost on reload (by design, warned).

## Remaining work

- Day 3: stress tests (fresh paraphrase set, the directive's 18 scenarios), contradiction handling, attention-flag design.
