# Unlearning note

*Drafted on Day 5 from the events recorded in `logs/day-1.md` … `logs/day-5.md`. Every example below happened and is logged there. Personal reflections should be added in the author's own words.*

## Habits abandoned

1. **Scaffolding everything up front.** The first action was to inspect the workspace and write `intent.md`; code came in small, separately committed slices (single message → API → UI → batch → grouping → CSV → review).
2. **Treating a green first run as done.** It happened repeatedly and was wrong every time it was checked: the first backend suite was 41/41 green while an independent review reported 9 findings, 6 of them confirmed by running code (including a crash on deeply nested JSON); the injection detector passed its tests yet missed 5 of 6 unseen attacks and falsely flagged 3 of 5 harmless messages. A green first run became a signal to probe harder.
3. **Writing my own evaluation data.** On Day 2 the paraphrase probe was written by the same hand that wrote the keyword rules. On Day 3 a separate agent, with no access to the code, wrote 40 held-out messages; accuracy came out at 55%, lower than the self-written probe (6/10).
4. **Acting on impressions.** On Day 2 the attention flag looked over-used. The Day 3 breakdown showed most flags had real reasons, and narrowing it would have made one wrong classification unflagged. The change was not made.
5. **Trusting documentation because it was written down.** `.env.example` offered a provider that never existed (written on Day 1, wrong until Day 4), and the first draft of `Final directive.md` claimed a warnings cap that the code doesn't enforce. Both were found only by checking against the running system.

## How the AI-first workflow changed the process

The AI wrote nearly all the code, tests and documents. The human-directed parts were: deciding behaviour before code (identity rules, review rules, stress expectations), insisting on failing tests before fixes, and deciding what *not* to do (no keyword tuning on held-out data; no `httpx2` swap days before submission). Three separate AI roles were used deliberately: a **builder**, an **independent reviewer** given only code and requirements, and an **independent data writer** given no code at all.

## AI output that needed correction (examples)

- Output validation crashed on `"[" * 100000` (`RecursionError`); outcome-wording checks were bypassed by "Congrats!", a curly apostrophe and a zero-width space.
- The first contradiction check reused the *draft* outcome list on *candidate* text and flagged "Congrats on the new role at your agency!".
- The secret-scan step went wrong three times (argument order twice, then an exit-code bug) before it became a tested script.
- A Python patch script mangled escape characters and silently changed nothing; a too-new `jsdom` required a newer Node than the machine had.

## How independent verification improved the result

The independent review reported 9 findings (6 confirmed by the reviewer running code; part of one did not hold up). Most were then reproduced by regression tests that failed before the fix and are still in the suite. A **mutation check** proved the most important test is real: making "Approve" call `fetch` made the "approval never sends" test fail. The **fresh-clone run** strictly from the README caught nothing new, which is the point: it is the evidence that setup works for someone else.

## What became easier, and what became harder

*Easier:* breadth. Tests, edge-case probes, docs and UI arrived quickly. *Harder:* the volume of plausible-looking code to verify, and the AI's confident tone on wrong output, made checking the bottleneck rather than writing.

## What failed or remains uncertain

- No real LLM provider was built or tested; the keyword mock reaches 55% on held-out messages (0 confidently wrong, but poor recall).
- Injection, language and conflict detection are heuristics with documented misses.
- Only Windows was verified; there is no automated browser end-to-end test (the browser flow was checked by hand, repeatedly).

## Next time

Write the independent evaluation set on Day 1, not Day 3; put the real provider behind the interface early with recorded fixture responses; add an automated browser test (e.g. Playwright) for the review flow; and keep docs next to the tests that prove each claim.
