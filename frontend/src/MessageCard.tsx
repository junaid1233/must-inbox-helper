import { useState } from "react";
import { BatchMessageResult } from "./api";
import { canApprove, isEdited, ReviewAction, ReviewItem } from "./review";

interface Props {
  result: BatchMessageResult;
  review: ReviewItem;
  dispatch: (action: ReviewAction) => void;
}

const STATUS_LABEL = { pending: "Pending review", approved: "Approved", rejected: "Rejected" } as const;

export function MessageCard({ result, review, dispatch }: Props) {
  const [copyNote, setCopyNote] = useState<string | null>(null);
  const { message } = result;
  const id = result.message_id;
  const edited = isEdited(review);
  const pending = review.status === "pending";
  // Every card has the same buttons, so each accessible name says which message it acts on.
  const who = `${message.candidate || "unnamed candidate"} (${id})`;

  // The backend also flags low/medium confidence and unclear intent without adding a
  // warning, so say why here; a flag with no reason teaches reviewers to ignore it.
  const attentionReasons = [...result.warnings];
  if (result.confidence !== "high") {
    attentionReasons.push(`Classification confidence is ${result.confidence}; check the intent.`);
  }
  if (result.intent === "other_or_unclear") {
    attentionReasons.push("The request could not be matched to a known category.");
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(review.draft);
      setCopyNote("Copied to clipboard.");
    } catch {
      setCopyNote("Copy failed. Select the text and copy it manually.");
    }
  }

  return (
    <article className={`card card-${review.status}`} aria-labelledby={`card-${id}`}>
      <header className="card-head">
        <h4 id={`card-${id}`}>{message.candidate || "Unnamed candidate"}</h4>
        <span className="hint">
          {id} · row {result.row}
          {message.received_at ? ` · ${message.received_at}` : ""}
        </span>
        <span className="pills">
          <span className={`status-pill pill-${review.status}`}>{STATUS_LABEL[review.status]}</span>
          {edited && <span className="status-pill pill-edited">Edited</span>}
        </span>
      </header>

      <blockquote className="original">{message.text}</blockquote>
      {(message.application_status || message.context) && (
        <dl className="known">
          {message.application_status && (
            <div>
              <dt>Known status</dt>
              <dd>{message.application_status}</dd>
            </div>
          )}
          {message.context && (
            <div>
              <dt>Context</dt>
              <dd>{message.context}</dd>
            </div>
          )}
        </dl>
      )}

      <p className="reason">
        <span className={`conf conf-${result.confidence}`}>{result.confidence}</span>
        <span className="hint"> confidence (rule-based band, not a probability)</span> · {result.reason}
      </p>

      {result.needs_human_attention && (
        <div className="attention" role="status">
          <strong>Needs human attention</strong>
          <ul>
            {attentionReasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      <label className="draft-label">
        <span>Draft reply</span>
        <textarea
          rows={5}
          value={review.draft}
          readOnly={!pending}
          aria-label={`Draft reply for ${id}`}
          onChange={(e) => dispatch({ type: "edit", id, text: e.target.value })}
          placeholder={result.draft_reply === null ? "No draft could be generated. Write a reply manually." : ""}
        />
      </label>

      <div className="actions">
        {pending && (
          <>
            <button
              type="button"
              onClick={() => dispatch({ type: "approve", id })}
              disabled={!canApprove(review)}
              title={canApprove(review) ? undefined : "Write a reply before approving."}
              aria-label={`Approve draft for ${who}`}
            >
              Approve draft
            </button>
            <button type="button" className="secondary danger" onClick={() => dispatch({ type: "reject", id })} aria-label={`Reject draft for ${who}`}>
              Reject draft
            </button>
            {edited && (
              <button type="button" className="secondary" onClick={() => dispatch({ type: "revert", id })} aria-label={`Revert edits for ${who}`}>
                Revert edits
              </button>
            )}
          </>
        )}
        {review.status === "approved" && (
          <>
            <p className="approved-note">Approved for use. Not sent: copy it into your own email or messaging tool.</p>
            <button type="button" className="secondary" onClick={copy} aria-label={`Copy approved text for ${who}`}>
              Copy text
            </button>
            <button type="button" className="secondary" onClick={() => dispatch({ type: "reopen", id })} aria-label={`Reopen draft for ${who}`}>
              Reopen
            </button>
          </>
        )}
        {review.status === "rejected" && (
          <button type="button" className="secondary" onClick={() => dispatch({ type: "reopen", id })} aria-label={`Reopen to revise draft for ${who}`}>
            Reopen to revise
          </button>
        )}
      </div>
      {copyNote && (
        <p className="hint" role="status">
          {copyNote}
        </p>
      )}
    </article>
  );
}
