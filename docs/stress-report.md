# Stress test report (Day 3)

**Run on:** 2026-10-26 · **Provider:** mock (keyword rules) · **Code:** `backend/tests/test_stress.py` (S01–S18) plus the held-out measurement in `eval/`.

**Method.** Each scenario's expected behaviour was written from the challenge directive **before** running it against the code, so a failure is a finding, not a test bug. First run: **29 passed, 6 failed** (S09 ×2, S12 ×4). After fixes: all pass; full backend suite **248 passed, 2 xfailed** (the xfails are documented known misses of the injection detector).

## Results

| # | Scenario | Expected behaviour | First run | After fix | Evidence / change | Remaining limitation |
|---|---|---|---|---|---|---|
| S01 | Straightforward status inquiry | `application_status`; draft states no status; "status not provided" warning | Pass | Pass | — | — |
| S02 | Reschedule request | `interview_scheduling`; draft asks for times, doesn't confirm a new slot or echo the proposed days | Pass | Pass | — | Template draft; doesn't acknowledge the specific days offered |
| S03 | Several messages, same intent | One group containing all ids, input order | Pass | Pass | — | — |
| S04 | Several different intents | One group per intent, each id exactly once | Pass | Pass | — | Multi-intent *single* messages get one intent only |
| S05 | Empty message | 422 on `/api/process`; row error in a batch, other rows processed | Pass | Pass | — | — |
| S06 | Malformed CSV | Broken quoting → file error (no silent row merging); wrong column count → row error | Pass | Pass | Day 2 showed lenient CSV mode merges rows silently; strict mode is used | One cell > 131,072 chars rejects the whole file |
| S07 | Missing candidate identifiers | Generated `auto-N` id + warning; greeting falls back to "Hello," | Pass | Pass | — | — |
| S08 | Duplicate messages | Repeated id: later row rejected; same text: both kept and warned | Pass | Pass | — | Near-duplicates (reworded) aren't detected |
| S09 | Message contradicts supplied context / status | Flag + warning naming the conflict; draft confirms neither version | **Fail** (no warning at all) | Pass | New `app/checks.py:find_conflicts`: (a) outcome the candidate claims about themselves vs recorded status, (b) dates/times in message vs context | Heuristic: only weekday/month/today/tomorrow/clock-time conflicts and first-person outcome claims; other contradictions (e.g. role names, locations) are not detected |
| S10 | Unknown application status | Draft doesn't invent a status or outcome; flagged | Pass | Pass | — | — |
| S11 | Prompt injection | Flagged, injection warning first, draft has no outcome claim | Pass | Pass | Detector built Day 1 | Pattern list: non-English and free-form phrasings missed (2 strict xfail tests) |
| S12 | Non-English / mixed language | Flagged, confidence not high, language warning | **Fail** (4/4: no language warning; mixed Spanish/English classified as status with no warning) | Pass | New `looks_non_english` (script share, `¿`/`¡`, foreign function words); mock lowers confidence to low for non-English | Heuristic; languages outside ES/FR/DE/PT/IT in Latin script may be missed |
| S13 | Very long messages | 5,000 chars processed < 1 s, reply stays short; 5,001 → 422; request at the end still found | Pass | Pass | — | Messages over 5,000 chars are rejected, not truncated |
| S14 | Invalid / malformed model output | Same id, flagged, no unsafe draft | Pass | Pass | Day 1 review found and fixed a crash on deeply nested JSON | — |
| S15 | Provider timeout / unavailable | Every row returned, no draft, flagged with reason | Pass | Pass | — | No retry/backoff (mock only) |
| S16 | Several messages with sensitive PII | No SSN/phone/email/passport in logs, errors, reasons or warnings; no draft contains any candidate's PII | Pass | Pass | `caplog` at DEBUG over a real `/api/process-batch` request | Results do return each message's own text to the reviewer (by design) |
| S17 | Batch with valid and invalid records | Every row accounted for exactly once | Pass | Pass | — | — |
| S18 | Clarification is the right response | Flagged; draft asks for more detail | Pass | Pass | — | — |

## Held-out classification measurement

40 messages (4 per intent) written by a **separate agent that never saw the keyword rules** (`eval/heldout_messages.json`). Run: `backend/.venv/Scripts/python eval/run_heldout.py`.

| Measure | Result |
|---|---|
| Accuracy | **22/40 (55%)**; excluding `other_or_unclear` (where every unmatched message lands, inflating the score): 16/34 (47%) |
| Missed → `other_or_unclear` (flagged, safe) | 17 |
| Wrong category, flagged | 1 (h-01: status → submission, medium) |
| **Wrong category, not flagged (confidently wrong)** | **0** |

The keyword mock fails *safely* (unclear and flagged) but has poor recall: indirect phrasing ("haven't heard anything since I sent my CV", "please remove me from consideration") isn't matched. I did **not** tune the keywords on this set, because that would make it useless as a measurement. Better recall needs a real LLM provider, which hasn't been built or tested.

## Probing beyond the scenarios

- Language check on 53 English messages it wasn't written for (held-out + sample): **0 false positives**.
- Conflict check, first version: 2 false positives. "Congrats on the new role at your agency!" was flagged as an outcome claim (wrong word list: the draft-side list was reused on candidate text), and "tell me I've been hired" was read as a claim. Fixed with first-person claim patterns and by skipping demands; both kept as regression tests. After the fix: 1 hit on the held-out set (h-25, "I got the offer letter…"), which is the intended "not in supplied data; don't confirm" warning.

## Decision: attention flag left unchanged

Day 2 noted that most messages are flagged. Breaking down the 8/15 flagged sample messages showed 6 have a must-check reason (duplicate, injection, conflict, non-English, unclear) and only 2 are flagged purely for medium confidence. Unflagging medium confidence would have turned h-01 into a confidently-wrong result. **Kept as is**; the Day 2 hunch was not supported by the data.
