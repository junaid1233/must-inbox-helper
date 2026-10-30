# Submission checklist

Checked on 2026-10-26 (Day 5) against section 10 ("Acceptance criteria") and section 8 ("Required deliverables") of the challenge directive. **"Done" means verified, not just that the code exists.** Status: ✅ verified · ⚠️ partly / with caveat · ❌ not done.

## Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Multiple messages can be entered or imported | ✅ | Paste, CSV and sample tabs; browser end-to-end run (Day 5 log); `test_batch.py`, `test_csv_import.py`, `App.test.tsx` |
| Every valid input receives a traceable classification result | ✅ | "Every row exactly once" invariant over a 200-row mixed batch (`test_large_mixed_batch_invariant`); each result has its `row` and `message_id` |
| Messages are grouped correctly per the implemented behaviour | ✅ | `test_grouping.py`; S03/S04; each id in exactly one group |
| Every valid message gets a safe draft or a documented reason why not | ✅ | Provider failures/invalid output → `draft_reply: null` + warning (S14, S15); template drafts tested free of outcome wording |
| Drafts can be edited, approved and rejected | ✅ | `review.test.ts`, `App.test.tsx`; browser run (edit → Edited, approve, reject, reopen) |
| No reply is sent externally | ✅ | No send endpoint (`test_no_endpoint_can_send_messages`); review actions make no network request (component test, **mutation-checked**; browser Network count unchanged, 0 `/api/` calls during review) |
| Uncertain or unsupported cases are handled transparently | ✅ | `other_or_unclear` + flag + reason; language/conflict/injection warnings; UI lists every attention reason |
| Automated tests cover core behaviour and important failures | ✅ | 262 backend (+2 strict xfail known misses), 19 frontend; S01–S18 |
| README instructions have been tested | ⚠️ | Fresh clone run from the README on **Windows 11** (Day 4 log). macOS/Linux commands **not run**, and marked so in the README |
| All required documentation exists | ✅ | See the table below |
| Daily logs reflect real work | ✅ | Logs record failures and mistakes as they happened. All five "days" were worked on 2026-10-26, and each log says so |
| Loom recording created and verified | ❌ | **Not recorded.** Script ready: `docs/loom-script.md`. Recording and link check are for the author to do |
| Known limitations and failures disclosed | ✅ | README "Known limitations", `Final directive.md` §8, `docs/stress-report.md`, the logs |

## Required deliverables

| Deliverable | Status | Notes |
|---|---|---|
| `intent.md` | ✅ | Original intent preserved; dated Day 5 amendment |
| `Final directive.md` | ✅ | Includes an initial-vs-final decisions table; claims checked against the code (one false claim corrected on Day 4) |
| `README.md` | ✅ | Commands verified via a fresh clone (Windows) |
| `logs/day-1.md` … `logs/day-5.md` | ✅ | |
| `unlearning-note.md` | ⚠️ | Drafted from logged events; the author should add personal reflections in their own words |
| Loom demonstration | ❌ | Script only |
| Working code and tests | ✅ | |
| Sample dataset | ✅ | `sample_data/` (synthetic), `eval/heldout_messages.json` |
| Configuration templates | ✅ | `.env.example` (corrected Day 4) |

## Before submitting (author)

*Updated 2026-10-30: the unlearning note was rewritten in first person, the spoken script was added to `docs/loom-script.md`, and an "About this submission" paragraph was added to the README.*

1. In `unlearning-note.md`, replace the **[I need to add this myself…]** line with your own words: how it felt to let AI write the code, and which habit was hardest to drop.
2. Put your name into the first line of the spoken script in `docs/loom-script.md`.
3. Record the Loom, open the link in a private window to confirm it plays, then add it to the README deliverables table (it says "Not recorded yet").
4. Run `sh scripts/check-secrets.sh`, then push to `github.com/junaid1233/must-inbox-helper` and confirm the link opens.
5. Log any further work under its real date, not inside Days 1–5.
