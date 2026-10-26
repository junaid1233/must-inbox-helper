# Intent — Inbox Helper

*Original intent written 2026-10-26 (Day 1). This section is not rewritten later; scope changes go under **Amendments** at the bottom, dated.*

## Problem

Recruiters handle a steady stream of candidate messages: "any update on my application?", "can we move my interview?", "what's the salary range?". Most need a short, polite, accurate reply, but reading, sorting and drafting each one by hand is slow. Doing it carelessly is risky: a hasty reply can promise something the recruiter doesn't know, leak another candidate's details, or tell someone they've progressed when they haven't.

The Inbox Helper takes a batch of candidate messages, groups them by what each candidate wants, and drafts a short reply for each. A human reviews, edits, approves or rejects every draft. Nothing is ever sent by the tool.

## Intended users

- **Primary:** a recruiter or recruiting coordinator working through an inbox of candidate messages.
- **Secondary:** a hiring-challenge reviewer evaluating the build, workflow and honesty of the documentation.

## User workflow

1. Paste messages, load the sample dataset, or import a CSV.
2. See validation errors for empty or malformed records; valid records continue.
3. Process the batch. Each message gets an intent, a reason, a confidence indicator and a review flag.
4. Browse messages grouped by intent, with counts and any warnings.
5. For each message, read the draft reply, edit it if needed, then **Approve** or **Reject**. A rejected draft can be reopened and revised.
6. Approved text is ready for the recruiter to copy and send through their own channel. The tool never sends it.

## Initial assumptions

- Messages are short-to-medium text, mostly English; some may be non-English or mixed.
- Application status, interview times and other facts are **only** known if supplied in the input (e.g. an `application_status` or `context` field). The tool must not invent them.
- A deterministic mock provider is enough to demonstrate and test the full workflow. A real LLM provider is optional and gated behind an environment variable.
- One reviewer at a time; review state can live in the browser session. No accounts or database are needed for the challenge.
- All demo data is synthetic. No real candidate PII.

## Scope

- Input: paste, sample dataset, CSV import, with per-record validation.
- Classification into a fixed set of intents, including `other_or_unclear`.
- Grouping by intent, preserving each message's identity (one message → exactly one group).
- Draft reply generation (normally 1–3 sentences), with output validation.
- Mandatory human review: edit, approve, reject, reopen; edited/pending status visible.
- Provider abstraction with a mock provider (default) and an optional LLM provider.
- Graceful handling of bad model output, timeouts and provider failures.
- Automated tests that never call a real LLM.

## Non-goals

- Sending email or contacting candidates in any way.
- Authentication, multi-user collaboration, or a database.
- Integrations with ATS, email or calendar systems.
- Background job queues or deployment infrastructure.
- Calibrated probability scores. Any confidence value will be documented as a heuristic unless the provider supplies something better.

## Success criteria

- Multiple messages can be entered or imported; invalid records are reported, not silently dropped.
- Every valid message gets exactly one traceable result (same `message_id` in and out).
- Every valid message gets a safe draft, or a documented reason why one couldn't be produced.
- Drafts can be edited, approved and rejected; approval never sends anything.
- Ambiguous, conflicting, injected or unsupported messages are flagged for human attention rather than confidently answered.
- The automated test suite runs offline and covers the core path and the stress cases in the directive.
- README commands are verified by actually running them.

## Risks and uncertainties

- **Hallucinated facts in drafts** (e.g. "you've been shortlisted"). Mitigation: drafting rules, output checks, and flags when status is unknown.
- **Prompt injection** inside candidate messages. Mitigation: treat message text as data, never as instructions; test it explicitly.
- **Keyword-based mock classification will be brittle** on paraphrases, sarcasm and non-English text. This is a known limitation of mock mode, to be measured rather than hidden.
- **Real LLM behaviour is unverified** until an API key is available; may not be tested at all within the challenge.
- **Time:** five days is short. Features beyond the core review workflow may be cut; cuts will be recorded here as amendments.

## Amendments

### 2026-10-26 (Day 5): scope as delivered

- **Real LLM provider: not built.** The original intent called it optional. No API key was available, so only the provider interface and the mock exist. An unknown `AI_PROVIDER` stops the backend instead of silently falling back.
- **Added: provider-independent safety checks.** Prompt-injection signals (Day 1), non-English detection and message/context conflict detection (Day 3). These address the "hallucinated facts" and "prompt injection" risks listed above, and are warnings, not guarantees.
- **Added: held-out evaluation.** 40 messages written by a separate agent that never saw the rules (`eval/`). This turned the "keyword mock will be brittle" risk into a measured number: 55% accuracy, 0 confidently wrong.
- **Clarified: no persistence.** Review state stays in the browser's memory; nothing is stored, to avoid keeping candidate data. The page warns before review work is lost.
- **Clarified: confidence** is a high/medium/low band, never a number.
- Success criteria above are tracked with evidence in `docs/submission-checklist.md`; the Loom recording is outstanding.
