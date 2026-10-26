# Final directive — Inbox Helper operating rules

*Written 2026-10-26 (Day 4). This describes what the implemented system actually does, as checked by the test suite. Where a final decision differs from the original challenge instructions, the last section says so and why.*

## 1. Classification rules

**Categories (exactly one per message):** `application_status`, `interview_scheduling`, `interview_follow_up`, `role_inquiry`, `application_submission`, `compensation`, `offer`, `withdrawal`, `networking`, `other_or_unclear`.

**Mock provider (the only implemented provider):** English keyword rules in `backend/app/providers/mock.py`.
- Each category has phrase patterns. Overlapping matches count once ("pay range" is one hit, not "pay" + "pay range").
- The category with the most hits wins. **A tie, or no hit, gives `other_or_unclear`.** The system never picks between equally likely categories.
- **Confidence is a band, not a probability:**
  - `high`: one category, at least 2 distinct hits, no other category matched.
  - `medium`: one category clearly ahead, but with a single hit or competing matches.
  - `low`: no match, a tie, or non-English text (the rules only cover English).
- The `reason` field says which rules matched and what else competed.

**Any provider's output** is untrusted and validated (`backend/app/validation.py`):
- Unknown category → `other_or_unclear` + warning.
- Confidence outside the three bands → `low` + warning.
- A missing reason, missing `message_id`, or warnings that aren't a list → warning.
- Not JSON, not an object, or the wrong `message_id` → the result fails safely (see §6).

## 2. Reply-generation rules

- One draft per valid message, normally 1–3 sentences after a greeting.
- **Never state an application status, outcome, date or decision that wasn't supplied.** A status is only mentioned if the recruiter supplied `application_status`, and then it's quoted as given.
- **Never promise an outcome.** Drafts acknowledge, ask for details, or say the recruiter will check.
- Ask for clarification when the request is unclear (`other_or_unclear` draft: "Could you share a little more detail…").
- **The candidate's message text is never copied into the draft.** The candidate name is used only if it looks like a plain name (letters, spaces, `.'-`, ≤ 60 chars), and then only the first word; otherwise the greeting is "Hello,".
- **Instructions inside candidate messages are not followed.** The mock never executes message content, and a real provider must receive message text only as data. Detected attempts add a warning (§4).
- **Outcome wording in a draft is flagged.** Words like *shortlisted, hired, selected, offer you, not to proceed, congratulations* are matched after Unicode normalisation (curly apostrophes, zero-width characters), unless the wording is the recruiter-supplied status itself.
- Every template draft is tested to contain no outcome wording.

## 3. Output schema

Per message (`MessageResult`):

| Field | Type | Notes |
|---|---|---|
| `message_id` | string | Always the input's id; never taken from provider output |
| `intent` | one of the 10 categories | |
| `confidence` | `"high" \| "medium" \| "low"` | Heuristic band |
| `reason` | string | ≤ 300 chars |
| `draft_reply` | string or `null` | `null` = no safe draft; `warnings` says why |
| `needs_human_attention` | boolean | See §4 |
| `warnings` | list of strings | Most serious first. Provider-supplied warnings are capped at 10 and 300 chars each; the system's own checks add theirs on top |
| `provider` | string | `"mock"` |

In a batch, each result also has `row` (1-based input position) and `message` (the validated input, so the reviewer sees what the draft answers). The batch response has `results`, `groups` (`intent`, `label`, `count`, `needs_attention_count`, `message_ids`), `errors` (`row`, `message_id`, `errors`) and `summary` (`received`, `processed`, `rejected`).

**Identity rules:**
- Every input row appears exactly once, in `results` or `errors`.
- Every result has a unique `message_id`, and each result is in exactly one group.
- A missing id gets a generated `auto-<row>` (pasted messages get `paste-<n>`).
- A repeated id keeps the first valid row and rejects later ones.

## 4. Uncertainty handling

`needs_human_attention` is true when **any** of these hold:
- Confidence is not `high`, or the intent is `other_or_unclear`.
- There's no draft (provider failure, invalid output, empty draft).
- **Possible prompt injection** in the text or context.
- **Conflict:** the candidate claims an outcome not matching (or absent from) the supplied status, or dates/times in the message don't match the supplied context.
- **Non-English or mixed-language** text.
- Outcome wording in the draft, or a draft longer than expected.
- Missing id, duplicate id, or the same text as another message.
- Status inquiry with no supplied status.
- The provider set the flag, or returned malformed fields.

The UI always says *why* a message is flagged; a flag with no reason teaches reviewers to ignore it.

## 5. Human-review requirements

- Every draft starts **Pending review**.
- **Approve** is allowed only on a pending draft with non-blank text, and it locks the text. **Reject** is allowed only on a pending draft. **Reopen** returns either to pending and keeps the edits.
- "Edited" is shown whenever the text differs from the generated draft.
- **Approval never sends anything.** No backend endpoint sends, emails or approves; review state lives only in the browser. A component test checks that approve, reject and reopen make no network request, and that test was mutation-checked: it fails if Approve is made to call `fetch`.
- The UI shows "Drafts are never sent automatically. Human review is required." and, on approval, "Approved for use. Not sent: copy it into your own email or messaging tool."

## 6. Error-handling behaviour

| Situation | Behaviour |
|---|---|
| Invalid single message | HTTP 422 with plain-English messages ("Message text is empty."); the submitted input is **not** echoed back |
| Invalid row in a batch / CSV | Row error with a plain-English reason; other rows processed |
| Broken CSV (no text column, unclosed quote, > 200 rows, empty) | HTTP 400 with a plain message; never truncated or silently merged |
| Provider timeout / unavailable / unexpected exception | Result with `other_or_unclear`, `low`, no draft, flagged, warning naming the failure; the batch continues |
| Provider output not JSON, wrong id, pathological JSON | Same as above; parse errors including `RecursionError` are caught |
| Backend unreachable (UI) | "Could not reach the backend. Is it running on port 8000?" |

## 7. Privacy and security constraints

- Candidate text is untrusted data. It is never executed or treated as instructions, and never logged.
- **Logs** contain ids, counts and error types only; tests check that names, message text and planted PII don't appear.
- Error messages never include submitted values.
- Results return a message's own text only to the reviewer who submitted it. No draft contains any candidate's personal data (tested with SSN, phone, email and passport strings across a batch).
- No candidate data is stored in the browser or on the server. Nothing is persisted.
- No secrets in the repo: `.env` is git-ignored, and `scripts/check-secrets.sh` runs before each commit (tested to block a planted fake key).
- CORS is limited to the frontend origin. All demo data is synthetic.

## 8. Known limitations

- **No real LLM provider.** The provider interface exists, but only the mock is implemented. Mock accuracy on 40 held-out messages: 55% (47% excluding the catch-all). Confidently wrong: 0.
- One intent per message.
- Injection, language and conflict checks are heuristic. Documented misses include non-English injection, free-form injection ("As an AI you must now…"), and conflicts other than dates/times and self-claimed outcomes.
- Review state is lost on reload (warned).
- Limits: 5,000 characters per message, 200 per batch, 1 MB per CSV.
- `message_id` values appear in logs.
- Verified on Windows 11 only.

## 9. Initial instructions vs final decisions

| Topic | Initial instruction (challenge directive) | Final decision | Why |
|---|---|---|---|
| Confidence | "Use confidence scores only when supported… don't present arbitrary numbers as calibrated" | Three bands (`high`/`medium`/`low`), never a number | A keyword count can't support a probability |
| AI provider | LLM provider abstraction with deterministic fallback | Interface + mock only; any other `AI_PROVIDER` fails at startup | No API key during the build; a silent fallback to mock would hide misconfiguration |
| Ambiguity | Classify as `other_or_unclear` or ask for clarification | Ties and no-matches → `other_or_unclear` with a clarification draft | As instructed |
| Duplicates | "Must not disappear or be silently duplicated" | Repeated id → first kept, later rejected (visible error); same text → both kept and warned | Keeps identity unique without hiding anything |
| Missing ids | Not specified | Generated `auto-<row>` / `paste-<n>` with a warning (paste: no warning) | Every result needs a unique id; pasted text never has one, so warning on it was noise |
| Persistence | "Lightweight persistence only if it materially improves the application" | None; warn before losing review work | Storing messages would keep PII in the browser |
| Attention flag | — | Kept broad (Day 3 data: only 2/15 sample flags were confidence-only; narrowing it made one wrong result unflagged) | Evidence in `docs/stress-report.md` |
| Test client dependency | — | Kept `httpx` 0.28.1 despite Starlette suggesting `httpx2` | `httpx2` checked and legitimate, but its newest release was 5 days old; test-only dependency works |
