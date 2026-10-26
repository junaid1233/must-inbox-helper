// Thin client for the backend. Only reads and classifies; there is nothing here that sends a reply.

export type Confidence = "high" | "medium" | "low";

export interface CandidateMessage {
  message_id?: string;
  candidate?: string | null;
  text: string;
  received_at?: string | null;
  application_status?: string | null;
  context?: string | null;
}

export interface MessageResult {
  message_id: string;
  intent: string;
  confidence: Confidence;
  reason: string;
  draft_reply: string | null;
  needs_human_attention: boolean;
  warnings: string[];
  provider: string;
}

export interface BatchMessageResult extends MessageResult {
  row: number;
  message: CandidateMessage & { message_id: string };
}

export interface IntentGroup {
  intent: string;
  label: string;
  count: number;
  needs_attention_count: number;
  message_ids: string[];
}

export interface RowError {
  row: number;
  message_id: string | null;
  errors: string[];
}

export interface BatchResponse {
  results: BatchMessageResult[];
  groups: IntentGroup[];
  errors: RowError[];
  summary: { received: number; processed: number; rejected: number };
}

export interface Health {
  status: string;
  provider: string;
  demo_mode: boolean;
  sends_messages: boolean;
}

export const MAX_CSV_BYTES = 1_000_000;

export class ApiError extends Error {}

interface ValidationIssue {
  loc: (string | number)[];
  msg: string;
}

// FastAPI errors carry either a plain message or a list of per-field issues.
function describeError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return "The request was not valid.";
  return (detail as ValidationIssue[])
    .map((issue) => {
      const field = issue.loc.filter((part) => part !== "body").join(".");
      return field ? `${field}: ${issue.msg}` : issue.msg;
    })
    .join("\n");
}

const UNREACHABLE = "Could not reach the backend. Is it running on port 8000?";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(UNREACHABLE);
  }
  // In development the Vite proxy answers 502 when the backend is down, so fetch never throws.
  if ([502, 503, 504].includes(response.status)) {
    throw new ApiError(UNREACHABLE);
  }
  if (response.status === 400 || response.status === 422) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(describeError(body.detail));
  }
  if (!response.ok) {
    throw new ApiError(`The backend returned an error (HTTP ${response.status}).`);
  }
  return response.json() as Promise<T>;
}

const postJson = <T>(path: string, body: unknown) =>
  request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getHealth = () => request<Health>("/api/health");

export const getSample = () => request<{ messages: CandidateMessage[] }>("/api/sample");

export const processBatch = (messages: CandidateMessage[]) =>
  postJson<BatchResponse>("/api/process-batch", { messages });

export const processCsv = (csv: string) => postJson<BatchResponse>("/api/process-csv", { csv });
