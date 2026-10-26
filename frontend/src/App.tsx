import { FormEvent, useEffect, useState } from "react";
import {
  ApiError,
  CandidateMessage,
  getHealth,
  getIntentLabels,
  Health,
  MessageResult,
  processMessage,
} from "./api";
import { ResultCard } from "./ResultCard";

const EMPTY_FORM = { message_id: "msg-001", candidate: "", application_status: "", text: "" };

export default function App() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [health, setHealth] = useState<Health | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [result, setResult] = useState<MessageResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch((e: Error) => setError(e.message));
    getIntentLabels().then(setLabels).catch(() => {});
  }, []);

  const update = (field: keyof typeof EMPTY_FORM) => (value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    // Optional fields are omitted when blank so the backend never sees invented values.
    const message: CandidateMessage = { message_id: form.message_id, text: form.text };
    if (form.candidate.trim()) message.candidate = form.candidate;
    if (form.application_status.trim()) message.application_status = form.application_status;
    try {
      setResult(await processMessage(message));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
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

      <main className="layout">
        <form className="panel" onSubmit={onSubmit} aria-labelledby="input-heading">
          <h2 id="input-heading">Candidate message</h2>
          <div className="row">
            <label>
              Message ID
              <input value={form.message_id} onChange={(e) => update("message_id")(e.target.value)} />
            </label>
            <label>
              Candidate <span className="hint">(optional)</span>
              <input value={form.candidate} onChange={(e) => update("candidate")(e.target.value)} />
            </label>
          </div>
          <label>
            Known application status <span className="hint">(optional, only if verified)</span>
            <input
              value={form.application_status}
              onChange={(e) => update("application_status")(e.target.value)}
              placeholder="Leave blank if unknown"
            />
          </label>
          <label>
            Message text
            <textarea
              rows={7}
              value={form.text}
              onChange={(e) => update("text")(e.target.value)}
              placeholder="Paste the candidate's message here"
            />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Processing…" : "Classify and draft reply"}
          </button>
        </form>

        <section className="panel" aria-labelledby="result-heading" aria-live="polite">
          <h2 id="result-heading">Result</h2>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          {!error && !result && <p className="muted">Results appear here after processing.</p>}
          {result && <ResultCard key={result.message_id + result.reason} result={result} labels={labels} />}
        </section>
      </main>
    </div>
  );
}
