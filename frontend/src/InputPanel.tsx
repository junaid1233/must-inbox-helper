import { ChangeEvent, useState } from "react";
import { BatchResponse, getSample, MAX_CSV_BYTES, processBatch, processCsv } from "./api";
import { parsePastedMessages } from "./review";

type Tab = "paste" | "csv" | "sample";

interface Props {
  busy: boolean;
  run: (job: () => Promise<BatchResponse>) => void;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "paste", label: "Paste messages" },
  { id: "csv", label: "Import CSV" },
  { id: "sample", label: "Sample data" },
];

export function InputPanel({ busy, run }: Props) {
  const [tab, setTab] = useState<Tab>("paste");
  const [pasted, setPasted] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const pastedMessages = parsePastedMessages(pasted);

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setFileError(null);
    if (file && file.size > MAX_CSV_BYTES) {
      setFileError("That file is larger than 1 MB. Split it into smaller files.");
      setCsvFile(null);
      return;
    }
    setCsvFile(file);
  }

  return (
    <section className="panel" aria-labelledby="input-heading">
      <h2 id="input-heading">Candidate messages</h2>
      <div className="tabs" role="tablist" aria-label="Input method">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`tabpanel-${id}`}
            className={tab === id ? "tab tab-active" : "tab"}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "paste" && (
        <div role="tabpanel" id="tabpanel-paste" aria-labelledby="tab-paste">
          <label>
            Messages
            <textarea
              rows={8}
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              placeholder={"Paste one or more messages.\n\nSeparate messages with a blank line."}
            />
          </label>
          <p className="hint">Separate messages with a blank line. Message IDs are assigned automatically.</p>
          <button
            type="button"
            disabled={busy || pastedMessages.length === 0}
            onClick={() => run(() => processBatch(pastedMessages))}
          >
            {pastedMessages.length === 1 ? "Process 1 message" : `Process ${pastedMessages.length} messages`}
          </button>
        </div>
      )}

      {tab === "csv" && (
        <div role="tabpanel" id="tabpanel-csv" aria-labelledby="tab-csv">
          <label>
            CSV file
            <input type="file" accept=".csv,text/csv,text/plain" onChange={onFile} />
          </label>
          <p className="hint">
            Needs a header row with a message column (<code>text</code>, <code>message</code> or <code>body</code>).
            Optional: <code>message_id</code>, <code>candidate</code>, <code>received_at</code>,{" "}
            <code>application_status</code>, <code>context</code>. Up to 200 rows, 1 MB.
          </p>
          {fileError && (
            <div className="error" role="alert">
              {fileError}
            </div>
          )}
          <button
            type="button"
            disabled={busy || !csvFile}
            onClick={() => csvFile && run(async () => processCsv(await csvFile.text()))}
          >
            Import and process
          </button>
        </div>
      )}

      {tab === "sample" && (
        <div role="tabpanel" id="tabpanel-sample" aria-labelledby="tab-sample">
          <p>
            15 synthetic messages covering every category, plus hard cases: a prompt-injection attempt, a
            vague message, a Spanish message, a duplicate and a message that contradicts its context.
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={() => run(async () => processBatch((await getSample()).messages))}
          >
            Load sample dataset
          </button>
        </div>
      )}
    </section>
  );
}
