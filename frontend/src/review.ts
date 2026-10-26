// Human review state for drafts. Pure functions only: nothing here talks to the
// network, so approving a draft can never send it anywhere.

export type ReviewStatus = "pending" | "approved" | "rejected";

export interface ReviewItem {
  status: ReviewStatus;
  original: string; // the generated draft ("" when none could be generated)
  draft: string; // current text, possibly edited by the reviewer
}

export type ReviewState = Record<string, ReviewItem>;

export type ReviewAction =
  | { type: "init"; drafts: Record<string, string | null> }
  | { type: "edit"; id: string; text: string }
  | { type: "revert"; id: string }
  | { type: "approve"; id: string }
  | { type: "reject"; id: string }
  | { type: "reopen"; id: string };

export const isEdited = (item: ReviewItem) => item.draft !== item.original;

// Approval needs a pending item with real text; an empty draft can't be approved.
export const canApprove = (item: ReviewItem) => item.status === "pending" && item.draft.trim() !== "";

export function reviewReducer(state: ReviewState, action: ReviewAction): ReviewState {
  if (action.type === "init") {
    const next: ReviewState = {};
    for (const [id, draft] of Object.entries(action.drafts)) {
      next[id] = { status: "pending", original: draft ?? "", draft: draft ?? "" };
    }
    return next;
  }

  const item = state[action.id];
  if (!item) return state;

  // Invalid transitions return the same state object, so callers can detect a no-op.
  switch (action.type) {
    case "edit":
      return item.status === "pending" ? { ...state, [action.id]: { ...item, draft: action.text } } : state;
    case "revert":
      return item.status === "pending" && isEdited(item)
        ? { ...state, [action.id]: { ...item, draft: item.original } }
        : state;
    case "approve":
      return canApprove(item) ? { ...state, [action.id]: { ...item, status: "approved" } } : state;
    case "reject":
      return item.status === "pending" ? { ...state, [action.id]: { ...item, status: "rejected" } } : state;
    case "reopen":
      return item.status !== "pending" ? { ...state, [action.id]: { ...item, status: "pending" } } : state;
  }
}

export function reviewCounts(state: ReviewState) {
  const counts = { pending: 0, approved: 0, rejected: 0, edited: 0 };
  for (const item of Object.values(state)) {
    counts[item.status] += 1;
    if (isEdited(item)) counts.edited += 1;
  }
  return counts;
}

// Pasted text: one message per paragraph, separated by one or more blank lines.
// Pasted text never has ids, so they are assigned here; the backend's "no message_id"
// warning is kept for imports where an id was expected, instead of flagging every paste.
export function parsePastedMessages(text: string): { message_id: string; text: string }[] {
  return text
    .split(/\r?\n\s*\r?\n/)
    .map((part) => part.trim())
    .filter((part) => part !== "")
    .map((part, index) => ({ message_id: `paste-${index + 1}`, text: part }));
}
