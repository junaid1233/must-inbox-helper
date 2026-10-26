# Next-iteration prompt (Inbox Helper)

Paste everything below the line into a new Claude Code session opened in the `must-inbox-helper/` folder. It's written to be reused: run **one iteration per real calendar day** and paste it again the next day.

---

You are my AI-first engineering partner on the **Inbox Helper** for the MUST challenge "Unlearn, Use, Raise the Load". The working version is already built. Your job now is to make the submission stronger **where the graders score it**, in small verified steps, without inventing anything.

## 1. How the work is graded (weights)

| Criterion | Weight | What the graders look for |
|---|---|---|
| Unlearning | 30% | The habits I dropped show up in the work **and** in the log |
| AI usage | 25% | I prompt well, check the results, and iterate |
| Raising the load | 20% | I really made it harder, and I report honestly what broke |
| Quality | 15% | It runs, it has tests, the code is readable |
| Honesty | 10% | I say what failed and don't hide it |

Choose work by weight. Something that improves Unlearning or AI usage beats a cosmetic UI change.

## 2. Read first, then report

Before changing anything, read: `README.md`, `intent.md`, `Final directive.md`, `logs/day-1.md` … `logs/day-5.md`, `unlearning-note.md`, `docs/stress-report.md`, `docs/submission-checklist.md`, and `git log --oneline`. Then run:

- `cd backend && .venv/Scripts/python -m pytest -q` (expect 262 passed, 2 xfailed)
- `cd frontend && npm test && npm run build` (expect 19 passed)
- `backend/.venv/Scripts/python eval/run_heldout.py` (expect 22/40, 0 confidently wrong)

Tell me in 5 lines or fewer: what you found, whether the numbers match, and which work item (§4) you propose for today and why. **Wait for my OK before starting.**

## 3. Rules (do not break these)

1. **Never fabricate.** No invented test results, metrics, prompts, log entries, dates or video links. If something wasn't run, write "not run".
2. **Never backdate.** All five existing logs were written on 2026-10-26. That date stays. New work goes under a dated heading with the **real** date (e.g. `### 2026-10-28 (iteration)`) in the log of the day it continues, or in a new `logs/iterations.md`. Don't rewrite past entries; add corrections as dated notes.
3. **Small steps.** One work item at a time: state the acceptance criteria → write a failing test → implement → run → probe with inputs the tests don't cover → record the result → commit locally.
4. **Check AI output independently.** For anything non-trivial, use a separate agent that sees the code and the requirements but **not** your conclusions. Mutation-check any test that guards a safety rule (break the code on purpose; confirm the test fails).
5. **Ask me first** before: paid API calls, adding a new dependency, deleting files, `git push`, or anything that leaves this machine. I push to GitHub and record the Loom myself.
6. **Never commit secrets.** Run `sh scripts/check-secrets.sh` before every commit. API keys only via `.env` (git-ignored).
7. Keep the "Drafts are never sent automatically. Human review is required." guarantee. No send feature, ever.

## 4. Work items, in priority order

Pick the highest item that isn't done. Each lists the criterion it serves.

**A. Prompt log (AI usage, 25%).** Create `docs/prompt-log.md` from **real** prompts only: the opening build directive, the independent code-review agent prompt (Day 1), the held-out data agent prompt (Day 3), and the prompts in this iteration. For each: the prompt (or a faithful excerpt), what came back, what was wrong with it, how it was checked, and what changed. Use the logs and git history as the source; if a prompt's exact wording isn't recoverable, say so instead of reconstructing it.
*Done when:* at least 5 real entries, each linked to a commit hash or log section.

**B. A real LLM provider (AI usage + Raising the load).** Implement `ClaudeProvider` behind the existing `AIProvider` interface (`AI_PROVIDER=claude`, key from `ANTHROPIC_API_KEY`). Read the `claude-api` skill before writing it. Requirements:
- Candidate text goes in as clearly delimited data, never as instructions; the system prompt states the rules from `Final directive.md` §1–2.
- Structured JSON output in the existing schema; everything still goes through `validation.py`.
- Timeout, rate-limit (429) and network errors map to the existing failure results; at most one retry with backoff.
- **Automated tests never call the API.** Use recorded fixture responses, including malformed ones.
- **Ask me before any live call.** If I approve and give a key, run `eval/run_heldout.py` with both providers and record mock vs Claude accuracy and confidently-wrong counts side by side. Report it honestly even if Claude does worse on some cases.
*Done when:* fixture tests pass, the mock is still the default, and either the live comparison is recorded or "not run (no key)" is written.

**C. Harder load, reported honestly (Raising the load, 20%).**
- A second held-out set written by a fresh agent with no file access: adversarial this time (multilingual injection, sarcasm, two requests in one message, very short and very long, a fake "recruiter note" inside a candidate message). Measure **before** any fix; record first-run numbers.
- Run the same set through the real provider if B is done.
- Add every confirmed failure to `docs/stress-report.md` as a new dated section: expected / first run / fix / remaining limitation.

**D. Automated browser end-to-end test (Quality, 15%).** Playwright test that loads the sample, edits and approves a draft, rejects and reopens another, imports `malformed.csv`, and asserts **no network request** happens during review actions. Ask before adding the dependency. Pin exact versions compatible with Node 22.13.

**E. Make the unlearning visible (Unlearning, 30%).** Don't rewrite the history. Add to each new log entry a short "Habit dropped today → evidence" line linking a commit or test. Then help me (don't write it for me) put `unlearning-note.md` in my own voice: ask me 5 short questions about what felt different, and turn my answers into the note, keeping every factual claim traceable to the logs.

**F. Submission package.** Produce `submission/` (git-ignored): a zip of the code made with `git archive` (no `node_modules`, `.venv`, `dist`; check it's under 25 MB and that a fresh unzip passes the README setup), plus the markdown deliverables. Update `docs/submission-checklist.md`. The two video slots (Loom + 5-minute demo) can be the same recording; I'll add the link.

## 5. End of every session

1. Run the full test suite, the build and the held-out eval; paste the real numbers.
2. Update the log for today's real date, with: goal, what was done, prompts used, what was wrong and how it was caught, tests run (command → result), habit dropped, and what remains.
3. Commit locally (no push) with a clear message.
4. Give me a 5-line summary: done, verified how, what broke, what's next, what needs my decision.
