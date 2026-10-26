# Prompt log

*Written 2026-10-26, at the end of the build session, from that session's transcript. Every prompt below was actually used. Agent briefs are quoted verbatim; long prompts are faithful excerpts and say so. Nothing here is reconstructed from memory.*

The build used three AI roles on purpose:
- a **builder** (Claude Code, the main session);
- an **independent reviewer**, given the code and requirements but not the builder's opinion;
- an **independent data writer**, given no access to the code at all.

The human set the rules, approved each step, and decided what not to do.

---

## 1. Opening build directive (author → builder)

**Prompt (excerpt; the full directive ran to 11 sections):**
> "Act as my AI-first engineering partner, senior full-stack engineer, QA engineer, and technical reviewer… Do not merely generate code. Help me demonstrate a changed engineering workflow: small iterations, deliberate AI usage, independent verification, progressively harder tests, honest failure reporting, and clear documentation… Do not claim that commands, tests, integrations, or features work unless you have actually verified them… **First action:** Inspect the current repository and environment, then report what exists, what is missing, and the proposed Day 1 implementation plan. Do not generate the entire application in a single unreviewed step."

**What came back:** an inspection report and a five-task Day 1 plan. No code yet.
- The workspace held unrelated client work, so the builder proposed a separate folder.
- `py` was broken on this machine (it pointed at a missing Python 3.13).
- There was no API key, so mock mode would be the default.

**What was wrong:** nothing at this step. The plan was reviewed before anything was created.

**How it was checked:** the author approved the folder choice explicitly ("Approved. Create must-inbox-helper/ with its own git repo and start Day 1 Task 1.").

**Effect:** set the working pattern for the whole build: inspect → plan → approve → small task → verify → log. Commit `bf91e74`.

## 2. Approval-gated task prompts (author → builder)

**Prompts (verbatim, examples):** "Go ahead with Day 1 Task 2." · "Go ahead with Day 2 Task 2: grouping by intent." · "Start Day 3: run the progressive stress tests." · "Start Day 4: README, Final directive.md, logging, friendlier errors, and a fresh-setup check."

**Why they're short:** the opening directive carried the rules, so each later prompt only had to release the next step. The builder stated acceptance criteria and stopped after each task for approval. That gave 14 small commits instead of one large generation.

**What was wrong:** the builder also made mistakes inside tasks, and they were caught and logged at the time:
- a secret-scan command was wrong three ways (`80f1d75`, `c07fdfa`);
- one fix cancelled out another fix (`c07fdfa`);
- a too-new test library didn't support the machine's Node version (`a43f0e6`).

## 3. Independent code review (builder → reviewer agent), Day 1 Task 2

**Prompt (verbatim brief, abridged only where marked […]):**
> "You are doing an independent code review. Do NOT edit any files; report only. Project: an 'Inbox Helper' for recruiters. It classifies candidate messages by intent and generates short reply drafts that a human must review. It must never send anything, never invent facts (e.g. application status or outcomes like 'shortlisted'/'hired'), treat candidate message text as untrusted data (prompt-injection resistant), handle invalid model output / provider failures gracefully, never silently drop or duplicate a message, and avoid logging PII. Confidence must not be presented as a calibrated probability. […] Scope: this is an early slice […] Look for: 1. Correctness bugs […] 2. Safety gaps against the requirements above that exist in THIS code […] 3. Tests that pass for the wrong reason or assert too weakly. 4. Unnecessary complexity. Verify claims by running code where possible. Report at most ~10 findings, most severe first, each with file:line, a concrete failing input, and whether you confirmed it by running it. Say plainly if something is fine."

**Design choice:** the reviewer got the code and the requirements, **not** the builder's view of the code, so it wasn't anchored on it.

**What came back:** 9 findings plus weak tests; 6 were confirmed by the reviewer running code. The most serious:
- a crash on `"[" * 100000` (`RecursionError`);
- outcome-wording checks bypassed by "Congrats!", a curly apostrophe and a zero-width space;
- double-counted keywords;
- possible personal data in error tracebacks.

**What was wrong with the review itself:**
- Part of finding 5 didn't hold: "I accepted the offer" already classified correctly.
- The reviewer saved its probe script over the builder's own file (same name in the scratch folder).

**How it was checked:** each finding became a regression test **before** fixing. 21 tests failed (plus 2 errors), confirming the findings; then all passed after the fixes.

**Effect:** commit `c07fdfa`; `backend/tests/test_review_regressions.py`.

## 4. Ambiguous prompt: "Try again" (author → builder)

**Prompt (verbatim):** "Try again"

**Interpretation:** it was unclear what to retry. The builder said its assumption (retry the browser screenshots, which had been timing out) and acted on it, instead of asking.

**What came back:** with screenshots working, a layout bug appeared that every text-based check had missed: optional-field hints wrapped onto their own line and misaligned the inputs.

**What was wrong:** two screenshots *looked* broken but were capture artefacts; measuring the page showed the layout was fine. They weren't "fixed".

**Lesson:** a terse prompt works when the assumption is stated; the screenshot found a real bug, and measuring prevented two false fixes. Commit `4a05b19`.

## 5. Held-out evaluation data (builder → data-writer agent), Day 3

**Prompt (verbatim):**
> "Write a held-out evaluation set of realistic candidate messages for a recruiting inbox classifier. Do NOT read any files or code: the point is that you have not seen the classifier's rules, so the messages aren't tailored to them. Intents (use these exact labels): application_status, interview_scheduling, interview_follow_up, role_inquiry, application_submission, compensation, offer, withdrawal, networking, other_or_unclear. Write 40 messages: 4 per intent. Make them varied and realistic: different lengths (one sentence to a short paragraph), tones (formal, casual, anxious, terse), typos in a few, British and American spelling, indirect phrasing (e.g. "haven't heard anything since I sent my CV" rather than "status"). For other_or_unclear, use messages that genuinely don't fit any other category or are too vague to tell (not trick messages). Every message must have exactly one clearly correct intent that a careful human recruiter would agree on. Use only invented names and details; no real people or companies. Output ONLY a JSON array, no prose, no code fence, in this shape: [{"id": "h-01", "intent": "application_status", "text": "..."}, ...] Order them by id h-01..h-40, mixing intents (don't group them by intent)."

**Why:** on Day 2 the same hand had written both the keyword rules and the paraphrase probe (6/10). That's a biased test. This agent ran on a different model (Sonnet) and was told not to look at the code.

**What came back:** 40 labelled messages in the requested format.

**Measured result:** 22/40 (55%), lower than the self-written probe. **0 confidently wrong**: 17 of the 18 misses fell to `other_or_unclear` and were flagged, and the one wrong category was flagged too.

**What was wrong:** reviewing the set for this log, **h-38** reads as a recruiter writing to a candidate ("the committee has approved extending you the Operations Manager position…"), not a candidate message as the prompt asked. It was kept as is and not re-scored, so the measurement stays independent; noted here instead.

**How it was checked:** the baseline was measured **before** any fix. The keywords were deliberately **not** tuned on this set.

**Effect:** commit `745d1e6`; `eval/heldout_messages.json`, `eval/run_heldout.py`.

## 6. Stress expectations written from the brief, not the code (author → builder)

**Prompt (verbatim):** "Start Day 3: run the progressive stress tests."

**Builder's approach:** expected behaviour for all 18 scenarios in the directive was written as tests **from the directive's wording, before running them**, so a failure would be a real finding.

**What came back:** 29 passed, 6 failed on the first run.
- **S09:** a contradiction between the message and the supplied context wasn't detected.
- **S12:** non-English and mixed-language text got no warning.

**What was wrong in the fix:** the first conflict check reused the *draft* outcome word list on *candidate* text. It flagged "Congrats on the new role at your agency!" and the demand "tell me I've been hired" as claims. Probing on unseen messages caught both; both are now regression tests.

**Effect:** commit `745d1e6`; `docs/stress-report.md`.

## 7. Checking a tool's advice before following it (builder), Day 4

**Trigger (verbatim warning text):** "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead."

**Approach:** the builder didn't install a package because a warning named it. It checked primary sources first:
- Starlette's installed source code;
- the PyPI metadata: author, maintainer, repository and release dates.

**Result:** `httpx2` is legitimate (by the original `httpx` author, maintained by Pydantic). But its newest release was 5 days old and it adds new dependencies. Kept `httpx` for a test-only use; recorded the reasoning in `pytest.ini`.

**What was wrong:** the first warning filter named the wrong warning class, so it didn't match. Fixed. Commit `4ed19b2`.

## 8. Self-check of written documents (builder), Day 4–5

Not a separate prompt; the builder re-read its own documents claim by claim against the code and the logs. It found:
- `.env.example` offered a provider that doesn't exist (since Day 1);
- `Final directive.md` claimed "warnings ≤ 10", which the code doesn't enforce;
- `unlearning-note.md` said "9 confirmed findings" (the log says 6 confirmed);
- the Loom script misdescribed why sample message s-013 has low confidence.

All four were plausible summaries that were wrong. Commits `4ed19b2`, `1a0b7f5`.

## 9. The real rubric changed the plan (author → builder), after Day 5

**Prompt (verbatim, Roman Urdu, with the challenge page pasted):** "abi github pe push nh kro pehly local pe test krln mn or han abi or b axha bnao isko prompt bnao pehly isky lie … loom video to mn khud bnaonga github pe push b mn krnga"
*(Translation: "Don't push to GitHub yet; I'll test locally first. And make it even better, but first write a prompt for that… I'll make the Loom video myself and push to GitHub myself.")*

**What it changed:** the pasted page held the **graders' rubric and weights**, which the build directive didn't have: Unlearning 30%, AI usage 25%, Raising the load 20%, Quality 15%, Honesty 10%. The builder wrote `docs/next-iteration-prompt.md`, ordering the remaining work by those weights. This prompt log was first in that order, because "AI usage" is graded on prompting and iterating, and nothing showed the prompts.

**Decision:** write this log in the original session, while the exact prompts were still available, rather than in a new session that would have to reconstruct them.

## 10. This log (author → builder)

**Prompt (verbatim):** "Yes, write docs/prompt-log.md here from the real prompts in this session, then commit it locally (no push)."

**Check:** commit hashes come from `git log`; figures were cross-checked against `logs/day-1.md` … `day-5.md` before committing.

---

## What worked, and what didn't

| Pattern | Result |
|---|---|
| Give the reviewer code + requirements, not conclusions | 9 findings from a green suite (6 confirmed by running code) |
| Data writer with no access to the code | A fairer score (55% vs 60% on a self-written probe) |
| Write expectations from the brief before running | 6 real first-run failures instead of tests shaped to the code |
| Approval gate after every task | 14 small, reviewable commits |
| Terse prompt with the assumption stated ("Try again") | Worked, but only because the assumption was said out loud |
| Trusting a green first run | Hid real problems in 4 cases (Day 1 backend suite, Day 1 injection tests, Day 2 grouping/classification probe, Day 3 conflict check); the Day 2 "approval never sends" test held up when mutation-checked |
| Re-using a word list in a new context (draft list on candidate text) | Two false positives; caught only by probing |
