# Day 3

**Date:** 2026-10-26, the same calendar day as Days 1–2. The "days" are the challenge's work phases, done back to back.

> Record only what actually happened. Leave a section as _not done_ rather than guessing.

## Goal for the day

Raise the load: run the directive's 18 stress scenarios, measure the classifier on messages it wasn't built around, record failures honestly, fix them with regression tests.

## Work completed

- `backend/tests/test_stress.py`: S01–S18, expectations written from the directive before running.
- `eval/heldout_messages.json` + `eval/run_heldout.py`: 40 held-out messages and a measurement script reporting accuracy and *confidently wrong* results.
- `backend/app/checks.py`: `looks_non_english()` and `find_conflicts()` (claimed outcome vs recorded status; message times vs context times). Wired into `process_message` for every provider. The mock lowers its confidence to low for non-English text.
- `docs/stress-report.md`: the per-scenario table (expected / first run / after fix / evidence / remaining limitation).

## Prompts / AI-assisted approaches used

- **Held-out data from an independent agent:** a separate agent wrote 40 labelled messages with instructions *not to read any files*, so the messages couldn't be shaped by the keyword rules I know. That fixes the bias in my own Day 2 paraphrase probe, where I wrote both the rules and the test messages.
- Stress expectations taken from the directive's wording, not from current output.

## Verification performed

- Stress suite run before any fix to get honest first-run results.
- Held-out baseline measured before any fix, then re-measured after.
- New checks probed on every English message available (53) for false positives.
- Browser: sample dataset loaded; s-013 shows the language warning and s-014 the time-conflict warning on their cards.

## Failures or incorrect assumptions discovered

- **First stress run: 29 passed, 6 failed.** S09 (contradiction, 2 tests): nothing detected conflicts. S12 (non-English, 4 cases): no language warning at all; the mixed message "Hi! ¿Hay novedades sobre el status de mi application?" was quietly classified as a status inquiry because of the English word "status".
- **Held-out accuracy 22/40 (55%)**, 47% excluding the catch-all category. Encouraging part: 0 confidently wrong; 17 of 18 misses were flagged as unclear.
- My first conflict check **reused the draft-side outcome list on candidate text** and flagged "Congrats on the new role at your agency!" as an outcome claim, plus "tell me I've been hired" (a demand, not a claim). Replaced with first-person claim patterns and a demand guard; both cases are regression tests.
- "pour" and "mon" were on my foreign-word list but are also English. Removed before measuring.
- **My Day 2 assumption was wrong:** I thought the attention flag was over-firing. A per-message breakdown showed only 2/15 sample flags come from medium confidence alone, and removing that flag would have made h-01 confidently wrong. Left unchanged.
- A long heredoc in Bash broke on quote characters in the data; wrote the files with the Write tool instead.
- The app had stopped the backend preview server ~7 minutes before I went to verify; restarted it.

## Changes made after verification

- Conflict detection rewritten to first-person claims + demand guard; `pour`/`mon` removed from the language list.
- No keyword tuning on the held-out set (deliberate).

## Tests actually run and results

| Command | Result |
|---|---|
| `pytest tests/test_stress.py` (first run) | **29 passed, 6 failed** (S09 ×2, S12 ×4) |
| `eval/run_heldout.py` (baseline) | 22/40; 17 safe misses; 1 flagged wrong; **0 confidently wrong** |
| `pytest tests/test_language_and_conflicts.py` (first version) | 26 passed (then probing found 2 false positives) |
| Language check over 53 English messages | 0 false positives |
| Conflict check over sample + held-out (after fix) | s-014 (intended); h-25 (intended "not in supplied data"); no false positives |
| `pytest tests/test_language_and_conflicts.py` (after fix) | 33 passed |
| `pytest -q` (full backend) | **248 passed, 2 xfailed** |
| `eval/run_heldout.py` (after changes) | unchanged: 22/40, 0 confidently wrong |
| `npx vitest run` | 19 passed |
| Browser, sample dataset | s-013 language warning and s-014 conflict warning shown on cards |

## What I unlearned or changed in my workflow

- Stopped writing my own evaluation data for my own rules. An independent agent with no access to the code produced a fairer test, and the score dropped from my own probe's 60% to 55%.
- Measured before deciding on the attention flag instead of acting on yesterday's impression. The data said leave it.
- "Safe failure rate" (confidently wrong = 0) turned out to be a more useful number than accuracy for a tool where a human reviews everything.

## Known limitations recorded today

- Keyword mock recall is poor (55% held-out); improving it means a real LLM provider, which is not built.
- Conflict detection only covers dates/times and self-claimed outcomes.
- Language detection is heuristic (Latin-script languages beyond ES/FR/DE/PT/IT may be missed).
- Conflict warning lists times lowercased and sorted ("10:00, monday, november") rather than as written. Cosmetic; not fixed.

## Remaining work

- Day 4: README and `Final directive.md`; app logging config (without message text); friendlier 422 wording; verify the `httpx2` deprecation suggestion before acting; fresh-clone setup test.
- Optional, only if an API key is available: real LLM provider behind the existing interface.
