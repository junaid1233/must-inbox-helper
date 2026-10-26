# Day 5

**Date:** 2026-10-26, the same calendar day as Days 1–4. All five "days" were worked back to back in one session; the day labels are the challenge's work phases, not calendar days.

> Record only what actually happened. Leave a section as _not done_ rather than guessing.

## Goal for the day

Verify and prepare submission: final test run, complete end-to-end run, unlearning note, Loom script, and check every deliverable against the directive.

## Work completed

- Final test, build and evaluation run; **full git history** scanned for key-shaped strings.
- Complete browser end-to-end run of every path (below).
- `unlearning-note.md`, drafted from logged events only.
- `docs/loom-script.md`: a timestamped 5-minute script. **The recording itself is not made.**
- `docs/submission-checklist.md`: each acceptance criterion and deliverable with status and evidence.
- `intent.md`: dated Day 5 amendment (scope as delivered). README: a deliverables table that states plainly that the Loom isn't recorded.

## Prompts / AI-assisted approaches used

- Asked the AI to write the unlearning note *only* from events in the logs, then cross-checked its numbers against the logs.
- Asked for the Loom script to reference only things already verified on screen, then checked each line against the app.

## Verification performed

- Browser end-to-end on the working copy (servers via the preview launcher), scripted in the page with real UI controls, plus a backend-down check.
- Unlearning note and Loom script checked claim by claim (two errors found, below).
- Every README link resolved to an existing file.

## Failures or incorrect assumptions discovered

- **Unlearning note overstated the review result:** it said "9 real defects" / "9 confirmed findings"; the Day 1 log says 9 findings, **6 confirmed by the reviewer running code**, and part of one didn't hold up. Corrected.
- **Loom script said s-013's confidence was "lowered because the rules only cover English".** s-013 matches no keyword, so its confidence is low because nothing matched; the "lowered" note only applies when an English keyword appears in non-English text. Corrected.
- Both errors were plausible-sounding summaries of real events. The checking step, not the writing, caught them.

## Changes made after verification

- Both corrections above; README deliverables table; `intent.md` amendment.

## Tests actually run and results

| Command | Result |
|---|---|
| `pytest -q` | **262 passed, 2 xfailed** |
| `npm test` / `npm run build` | **19 passed** / OK |
| `eval/run_heldout.py` | 22/40 (55%); **0 confidently wrong** |
| `scripts/check-secrets.sh` + `git grep` over all commits for `sk-ant-…` | no matches |
| Browser: header | "Demo mode · mock provider"; notice "Drafts are never sent automatically. Human review is required." |
| Browser: sample | 15 received / 15 processed / 0 rejected; 10 groups with counts and attention counts |
| Browser: review (edit + approve s-003, reject + reopen s-012, attention filter) | s-003 "Approved Edited", read-only, "Approved for use. Not sent…"; s-012 Rejected → Pending, editable; counts "14 pending · 1 approved · 0 rejected · 1 edited"; filter shows 8 cards; **0 `/api/` requests during all review actions** |
| Browser: paste (status + injection) | ids `paste-1`, `paste-2`; injection warning on paste-2 |
| Browser: malformed CSV | 3 / 1 / 2; "unquoted comma?" and "Message text is empty." |
| Browser: backend stopped | "Could not reach the backend. Is it running on port 8000?"; previous results kept on screen; backend restarted |

## What I unlearned or changed in my workflow

- Applied the same "check before trusting" rule to writing as to code: the reflective documents had factual slips that only showed up when compared with the logs and the app.

## Remaining work (for the author)

- **Record the Loom** from `docs/loom-script.md`; verify the link in a private window; add it to the README.
- Put `unlearning-note.md` in your own voice.
- Push the repo to its submission host and check the link (the repo is local only so far).
- Not done and disclosed: real LLM provider; automated browser end-to-end test; macOS/Linux setup verification.
