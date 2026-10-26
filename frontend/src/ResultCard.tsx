import { useState } from "react";
import { MessageResult } from "./api";

interface Props {
  result: MessageResult;
  labels: Record<string, string>;
}

// Approve / reject arrive on Day 2. Until then every draft stays "Pending review".
export function ResultCard({ result, labels }: Props) {
  const original = result.draft_reply ?? "";
  const [draft, setDraft] = useState(original);
  const edited = draft !== original;

  // The backend also flags low/medium confidence and unclear intent without adding a
  // warning, so say why here; a flag with no reason teaches reviewers to ignore it.
  const attentionReasons = [...result.warnings];
  if (result.confidence !== "high") {
    attentionReasons.push(`Classification confidence is ${result.confidence}; check the intent.`);
  }
  if (result.intent === "other_or_unclear") {
    attentionReasons.push("The request could not be matched to a known category.");
  }

  return (
    <article className="result">
      <dl className="facts">
        <div>
          <dt>Intent</dt>
          <dd>{labels[result.intent] ?? result.intent}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>
            <span className={`conf conf-${result.confidence}`}>{result.confidence}</span>
            <span className="hint"> (rule-based band, not a probability)</span>
          </dd>
        </div>
        <div>
          <dt>Message ID</dt>
          <dd>{result.message_id}</dd>
        </div>
      </dl>

      <p className="reason">
        <strong>Why:</strong> {result.reason}
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
        <span>
          Draft reply <span className="status-pill">Pending review</span>
          {edited && <span className="status-pill pill-edited">Edited</span>}
        </span>
        <textarea
          rows={6}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={result.draft_reply === null ? "No draft could be generated. Write a reply manually." : ""}
        />
      </label>
      {edited && (
        <button type="button" className="secondary" onClick={() => setDraft(original)}>
          Revert to generated draft
        </button>
      )}
    </article>
  );
}
