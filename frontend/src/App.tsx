import { useEffect, useReducer, useState } from "react";
import { ApiError, BatchResponse, getHealth, Health } from "./api";
import { BatchView } from "./BatchView";
import { InputPanel } from "./InputPanel";
import { reviewCounts, reviewReducer } from "./review";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [review, dispatch] = useReducer(reviewReducer, {});

  useEffect(() => {
    getHealth().then(setHealth).catch((e: Error) => setError(e.message));
  }, []);

  // Review state lives only in memory (no candidate data is stored in the browser),
  // so warn before a reload or close throws away review work.
  const counts = reviewCounts(review);
  const hasWork = counts.approved + counts.rejected + counts.edited > 0;
  useEffect(() => {
    if (!hasWork) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasWork]);

  function run(job: () => Promise<BatchResponse>) {
    if (hasWork && !window.confirm("Processing new messages replaces the current review. Continue?")) return;
    setBusy(true);
    setError(null);
    job()
      .then((result) => {
        setBatch(result);
        dispatch({
          type: "init",
          drafts: Object.fromEntries(result.results.map((r) => [r.message_id, r.draft_reply])),
        });
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Something went wrong."))
      .finally(() => setBusy(false));
  }

  return (
    <div className="page">
      <header className="topbar">
        <h1>Inbox Helper</h1>
        {health && (
          <span className={`badge ${health.demo_mode ? "badge-demo" : ""}`}>
            {health.demo_mode ? "Demo mode · mock provider" : `Provider: ${health.provider}`}
          </span>
        )}
      </header>

      <p className="notice" role="note">
        Drafts are never sent automatically. Human review is required.
      </p>

      <InputPanel busy={busy} run={run} />

      {busy && (
        <p className="muted" role="status">
          Processing…
        </p>
      )}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {batch && <BatchView batch={batch} review={review} dispatch={dispatch} />}
    </div>
  );
}
