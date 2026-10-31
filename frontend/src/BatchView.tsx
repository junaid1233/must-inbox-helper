import { useState } from "react";
import { BatchResponse } from "./api";
import { MessageCard } from "./MessageCard";
import { ReviewAction, reviewCounts, ReviewState } from "./review";

interface Props {
  batch: BatchResponse;
  review: ReviewState;
  dispatch: (action: ReviewAction) => void;
}

export function BatchView({ batch, review, dispatch }: Props) {
  const [attentionOnly, setAttentionOnly] = useState(false);
  const byId = new Map(batch.results.map((result) => [result.message_id, result]));
  const counts = reviewCounts(review);
  const { summary } = batch;

  const metrics = [
    { value: summary.received, label: "Received" },
    { value: summary.processed, label: "Processed" },
    { value: summary.rejected, label: "Row errors" },
    { value: counts.pending, label: "Pending" },
    { value: counts.approved, label: "Approved" },
    { value: counts.rejected, label: "Rejected" },
  ];

  return (
    <section aria-labelledby="results-heading" className="results">
      <div className="summary panel">
        <div className="summary-head">
          <h2 id="results-heading">Results</h2>
          <label className="inline">
            <input type="checkbox" checked={attentionOnly} onChange={(e) => setAttentionOnly(e.target.checked)} />
            Show only messages that need attention
          </label>
        </div>
        <div className="metrics">
          {metrics.map((metric) => (
            <div key={metric.label} className="metric">
              <span className="metric-value">{metric.value}</span>
              <span className="metric-label">{metric.label}</span>
            </div>
          ))}
        </div>
        <p className="review-line" aria-live="polite">
          Review: <strong>{counts.pending}</strong> pending · <strong>{counts.approved}</strong> approved ·{" "}
          <strong>{counts.rejected}</strong> rejected · {counts.edited} edited
        </p>
      </div>

      {batch.errors.length > 0 && (
        <section className="panel row-errors" aria-labelledby="row-errors-heading">
          <h3 id="row-errors-heading">Rows not processed ({batch.errors.length})</h3>
          <ul>
            {batch.errors.map((error) => (
              <li key={error.row}>
                <strong>Row {error.row}</strong>
                {error.message_id ? ` (${error.message_id})` : ""}: {error.errors.join(" ")}
              </li>
            ))}
          </ul>
        </section>
      )}

      {batch.groups.map((group) => {
        const members = group.message_ids
          .map((id) => byId.get(id))
          .filter((result) => result && (!attentionOnly || result.needs_human_attention));
        if (members.length === 0) return null;
        return (
          <section key={group.intent} className="group" aria-labelledby={`group-${group.intent}`}>
            <h3 id={`group-${group.intent}`}>
              {group.label} <span className="count">({group.count})</span>
              {group.needs_attention_count > 0 && (
                <span className="hint">
                  {" "}
                  · {group.needs_attention_count} {group.needs_attention_count === 1 ? "needs" : "need"} attention
                </span>
              )}
            </h3>
            {members.map(
              (result) =>
                result &&
                review[result.message_id] && (
                  <MessageCard
                    key={result.message_id}
                    result={result}
                    review={review[result.message_id]}
                    dispatch={dispatch}
                  />
                ),
            )}
          </section>
        );
      })}
    </section>
  );
}
