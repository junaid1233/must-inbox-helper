// Thin client for the backend. Only reads and classifies; there is nothing here that sends a reply.

export type Confidence = "high" | "medium" | "low";

export interface CandidateMessage {
  message_id: string;
  candidate?: string;
  text: string;
  application_status?: string;
  context?: string;
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

export interface Health {
  status: string;
  provider: string;
  demo_mode: boolean;
  sends_messages: boolean;
}

export class ApiError extends Error {}

interface ValidationIssue {
  loc: (string | number)[];
  msg: string;
}

// FastAPI 422 bodies list one issue per field; turn them into readable lines.
function describeValidation(detail: unknown): string {
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
  if (response.status === 422) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(describeValidation(body.detail));
  }
  if (!response.ok) {
    throw new ApiError(`The backend returned an error (HTTP ${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const getHealth = () => request<Health>("/api/health");

export const getIntentLabels = () => request<Record<string, string>>("/api/intents");

export const processMessage = (message: CandidateMessage) =>
  request<MessageResult>("/api/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message),
  });
