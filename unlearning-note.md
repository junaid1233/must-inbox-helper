# What I unlearned

I built Inbox Helper AI-first. The AI wrote nearly all of the code, tests and docs. My part was setting the rules, approving each step, checking what came back, and deciding what *not* to do. One honest note up front: all five "day" phases happened on the same calendar day, 26 October 2026, and every log says so.

**I stopped scaffolding everything first.** My first instruction was to inspect the workspace and write `intent.md` before any code. After that the app grew in small slices: one message, then the API, the UI, batches, grouping, CSV import, review. That was 14 small commits by the end of Day 5.

**I stopped trusting a green first run.** My first backend suite passed 41 out of 41. Then a second AI agent, given only the code and the requirements, came back with 9 findings and confirmed 6 by running code. One was a crash on a deeply nested JSON reply. Another was an outcome check that "Congrats!" slipped straight past. The prompt-injection detector was the same story: its tests passed, then it missed 5 of 6 attacks I hadn't tested and wrongly flagged 3 of 5 normal messages. Not every green run was hiding something; the "approval never sends" test held up when I broke the code on purpose. But now a green first run means: probe harder.

**I stopped writing my own test data.** On Day 2 I wrote both the keyword rules and the paraphrase probe, and scored 6 out of 10. On Day 3 a separate agent with no access to the code wrote 40 test messages. The score was 22 out of 40 (55%). Lower, and more honest.

**I stopped acting on a hunch.** On Day 2 the "needs attention" flag looked like it fired too often. On Day 3 I counted why: only 2 of 15 sample messages were flagged for medium confidence alone, and removing that rule would have let one wrong answer through unflagged. So I left it.

**I stopped believing docs because they were written down.** `.env.example` offered an AI provider that didn't exist, from Day 1 until I checked it on Day 4. `Final directive.md` claimed a warnings limit the code doesn't enforce. Even the first draft of this note said "9 confirmed findings" when the log says 6.

**What checking caught:**
- The secret-scan step was wrong three times before I made it a tested script.
- A test library needed a newer Node than my machine had.
- On purpose, I made "Approve" call the network. The "approval never sends" test failed, so I trust that test.
- A fresh clone, set up only from the README, worked on Windows.

**Easier and harder.** Breadth got easier: tests, edge cases and docs came fast. Checking got harder. There was a lot of confident, plausible code, and checking it, not writing it, became the slow part.

**Still not solved.**
- The mock gets 55% on unseen messages. It was never confidently wrong, but it misses a lot.
- There's no real AI provider yet.
- The injection, language and conflict checks are heuristics with known misses.
- I only verified setup on Windows, and the browser flow was checked by hand, not by an automated test.

**In my own words** (from the "what I unlearned" sections of my logs):
- "All green on the first run" is now a signal to probe harder, not to move on. (Day 1)
- A probe is for measuring. Fixing exactly what it found would make the next measurement meaningless. (Day 2)
- The fresh clone, run strictly from the README, is the only setup test that counts. (Day 4)
- Next time I'd write the independent test set on Day 1, not Day 3, and put a real AI provider behind the interface early.
- **[I need to add this myself: how it felt to let AI write the code, and which habit was hardest to drop.]**
