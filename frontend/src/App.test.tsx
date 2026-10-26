import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { BatchResponse } from "./api";

const message = (id: string, text: string) => ({ message_id: id, text, candidate: `Person ${id}` });

const BATCH: BatchResponse = {
  results: [
    {
      message_id: "s-1", row: 1, intent: "application_status", confidence: "high", reason: "status rules",
      draft_reply: "Hello,\n\nThanks for checking in.", needs_human_attention: false, warnings: [], provider: "mock",
      message: message("s-1", "Any update?"),
    },
    {
      message_id: "s-2", row: 2, intent: "other_or_unclear", confidence: "low", reason: "provider failed",
      draft_reply: null, needs_human_attention: true, provider: "mock",
      warnings: ["The AI provider timed out. No draft was generated; write a reply manually."],
      message: message("s-2", "Hmm"),
    },
  ],
  groups: [
    { intent: "application_status", label: "Application status inquiry", count: 1, needs_attention_count: 0, message_ids: ["s-1"] },
    { intent: "other_or_unclear", label: "Other or unclear", count: 1, needs_attention_count: 1, message_ids: ["s-2"] },
  ],
  errors: [{ row: 3, message_id: "bad", errors: ["text: String should have at least 1 character"] }],
  summary: { received: 3, processed: 2, rejected: 1 },
};

const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn((url: string) => {
    if (url === "/api/health") return json({ status: "ok", provider: "mock", demo_mode: true, sends_messages: false });
    if (url === "/api/sample") return json({ messages: [{ text: "Any update?" }] });
    if (url === "/api/process-batch") return json(BATCH);
    return json({ detail: "unexpected" }, 500);
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function loadSample() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("tab", { name: "Sample data" }));
  await user.click(screen.getByRole("button", { name: "Load sample dataset" }));
  await screen.findByText("Any update?");
  return user;
}

const card = (name: string) => screen.getByRole("article", { name });

describe("batch review workflow", () => {
  it("shows the no-send notice, groups, row errors and pending status", async () => {
    await loadSample();
    expect(screen.getByText("Drafts are never sent automatically. Human review is required.")).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Application status inquiry/ })).toBeTruthy();
    expect(screen.getByText(/Row 3/)).toBeTruthy();
    expect(within(card("Person s-1")).getByText("Pending review")).toBeTruthy();
  });

  it("approving, rejecting and reopening never make a network request", async () => {
    const user = await loadSample();
    const callsAfterLoad = fetchMock.mock.calls.length;
    const first = card("Person s-1");
    const draft = within(first).getByRole("textbox", { name: "Draft reply for s-1" });

    await user.type(draft, " Best, Sam");
    expect(within(first).getByText("Edited")).toBeTruthy();

    await user.click(within(first).getByRole("button", { name: /^Approve draft for/ }));
    expect(within(first).getByText("Approved")).toBeTruthy();
    expect(within(first).getByText(/Not sent/)).toBeTruthy();
    expect((draft as HTMLTextAreaElement).readOnly).toBe(true);

    await user.click(within(first).getByRole("button", { name: /^Reopen draft for/ }));
    await user.click(within(first).getByRole("button", { name: /^Reject draft for/ }));
    expect(within(first).getByText("Rejected")).toBeTruthy();
    await user.click(within(first).getByRole("button", { name: /^Reopen to revise draft for/ }));
    expect((draft as HTMLTextAreaElement).value).toBe("Hello,\n\nThanks for checking in. Best, Sam");

    expect(fetchMock.mock.calls.length).toBe(callsAfterLoad);
  });

  it("each action button names the message it acts on", async () => {
    await loadSample();
    expect(screen.getByRole("button", { name: "Approve draft for Person s-1 (s-1)" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Reject draft for Person s-2 (s-2)" })).toBeTruthy();
  });

  it("a missing draft cannot be approved until the reviewer writes one", async () => {
    const user = await loadSample();
    const second = card("Person s-2");
    const approve = within(second).getByRole("button", { name: /^Approve draft for/ }) as HTMLButtonElement;
    expect(approve.disabled).toBe(true);
    expect(within(second).getByText(/timed out/)).toBeTruthy();

    await user.type(within(second).getByRole("textbox", { name: "Draft reply for s-2" }), "Thanks, I'll check.");
    expect(approve.disabled).toBe(false);
    await user.click(approve);
    expect(within(second).getByText("Approved")).toBeTruthy();
  });

  it("review counts update and the attention filter hides calm messages", async () => {
    const user = await loadSample();
    await user.click(within(card("Person s-1")).getByRole("button", { name: /^Approve draft for/ }));
    expect(screen.getByText(/Review:/).textContent).toMatch(/1 pending · 1 approved · 0 rejected/);

    await user.click(screen.getByRole("checkbox", { name: /only messages that need attention/ }));
    expect(screen.queryByRole("article", { name: "Person s-1" })).toBeNull();
    expect(card("Person s-2")).toBeTruthy();
  });

  it("shows a backend 400 message from a bad CSV", async () => {
    fetchMock.mockImplementation((url: string) =>
      url === "/api/process-csv"
        ? json({ detail: "The CSV has no message text column." }, 400)
        : json({ status: "ok", provider: "mock", demo_mode: true, sends_messages: false }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: "Import CSV" }));
    const file = new File(["message_id,candidate\nx,y\n"], "bad.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("CSV file"), file);
    await user.click(screen.getByRole("button", { name: "Import and process" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("no message text column"));
  });
});
