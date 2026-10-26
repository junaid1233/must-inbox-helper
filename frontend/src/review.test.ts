import { describe, expect, it } from "vitest";
import { canApprove, isEdited, parsePastedMessages, reviewCounts, reviewReducer, ReviewState } from "./review";

const init = (drafts: Record<string, string | null>) => reviewReducer({}, { type: "init", drafts });

describe("reviewReducer", () => {
  it("starts every draft as pending and unedited", () => {
    const state = init({ a: "Hello", b: null });
    expect(state.a).toEqual({ status: "pending", original: "Hello", draft: "Hello" });
    expect(state.b).toEqual({ status: "pending", original: "", draft: "" });
    expect(isEdited(state.a)).toBe(false);
  });

  it("edit marks the draft as edited; revert restores the original", () => {
    let state = init({ a: "Hello" });
    state = reviewReducer(state, { type: "edit", id: "a", text: "Hello there" });
    expect(isEdited(state.a)).toBe(true);
    state = reviewReducer(state, { type: "revert", id: "a" });
    expect(state.a.draft).toBe("Hello");
    expect(isEdited(state.a)).toBe(false);
  });

  it("approve locks the text: edits after approval are ignored", () => {
    let state = init({ a: "Hello" });
    state = reviewReducer(state, { type: "approve", id: "a" });
    expect(state.a.status).toBe("approved");
    const after = reviewReducer(state, { type: "edit", id: "a", text: "sneaky change" });
    expect(after).toBe(state);
    expect(after.a.draft).toBe("Hello");
  });

  it("cannot approve an empty or whitespace-only draft", () => {
    let state = init({ a: null, b: "Hi" });
    expect(reviewReducer(state, { type: "approve", id: "a" })).toBe(state);
    state = reviewReducer(state, { type: "edit", id: "b", text: "   \n " });
    expect(canApprove(state.b)).toBe(false);
    expect(reviewReducer(state, { type: "approve", id: "b" })).toBe(state);
  });

  it("a manually written reply for a missing draft can be approved", () => {
    let state = init({ a: null });
    state = reviewReducer(state, { type: "edit", id: "a", text: "Thanks, I'll check and reply." });
    state = reviewReducer(state, { type: "approve", id: "a" });
    expect(state.a.status).toBe("approved");
  });

  it("reject, then reopen keeps the edited text so it can be revised", () => {
    let state = init({ a: "Hello" });
    state = reviewReducer(state, { type: "edit", id: "a", text: "Hello, revised" });
    state = reviewReducer(state, { type: "reject", id: "a" });
    expect(state.a.status).toBe("rejected");
    expect(reviewReducer(state, { type: "edit", id: "a", text: "x" })).toBe(state);
    state = reviewReducer(state, { type: "reopen", id: "a" });
    expect(state.a).toEqual({ status: "pending", original: "Hello", draft: "Hello, revised" });
  });

  it("an approved draft can be reopened and revised", () => {
    let state = init({ a: "Hello" });
    state = reviewReducer(state, { type: "approve", id: "a" });
    state = reviewReducer(state, { type: "reopen", id: "a" });
    state = reviewReducer(state, { type: "edit", id: "a", text: "Hello again" });
    expect(state.a.status).toBe("pending");
    expect(state.a.draft).toBe("Hello again");
  });

  it("ignores invalid transitions and unknown ids", () => {
    const state = init({ a: "Hello" });
    expect(reviewReducer(state, { type: "reopen", id: "a" })).toBe(state);
    expect(reviewReducer(state, { type: "revert", id: "a" })).toBe(state);
    expect(reviewReducer(state, { type: "approve", id: "missing" })).toBe(state);
    const rejected = reviewReducer(state, { type: "reject", id: "a" });
    expect(reviewReducer(rejected, { type: "approve", id: "a" })).toBe(rejected);
    expect(reviewReducer(rejected, { type: "reject", id: "a" })).toBe(rejected);
  });

  it("review of one message never changes another", () => {
    let state: ReviewState = init({ a: "A", b: "B" });
    state = reviewReducer(state, { type: "approve", id: "a" });
    expect(state.b).toEqual({ status: "pending", original: "B", draft: "B" });
  });
});

describe("reviewCounts", () => {
  it("counts statuses and edits", () => {
    let state = init({ a: "A", b: "B", c: "C" });
    state = reviewReducer(state, { type: "edit", id: "a", text: "A2" });
    state = reviewReducer(state, { type: "approve", id: "a" });
    state = reviewReducer(state, { type: "reject", id: "b" });
    expect(reviewCounts(state)).toEqual({ pending: 1, approved: 1, rejected: 1, edited: 1 });
  });
});

describe("parsePastedMessages", () => {
  it("splits on blank lines and trims", () => {
    expect(parsePastedMessages("First message\nstill first\n\n  Second  \n\n\n\nThird")).toEqual([
      { message_id: "paste-1", text: "First message\nstill first" },
      { message_id: "paste-2", text: "Second" },
      { message_id: "paste-3", text: "Third" },
    ]);
  });

  it("handles Windows line endings and whitespace-only separator lines", () => {
    expect(parsePastedMessages("One\r\n \r\nTwo")).toEqual([
      { message_id: "paste-1", text: "One" },
      { message_id: "paste-2", text: "Two" },
    ]);
  });

  it("returns nothing for blank input", () => {
    expect(parsePastedMessages("  \n\n \n")).toEqual([]);
  });
});
