/**
 * Tests for the CoachChat client component.
 *
 * Strategy: mock `@/lib/api/client` so `coachChat` yields a fixed chunk
 * sequence. Assert that the final assistant bubble shows the concatenated text.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mock the API client module
// ---------------------------------------------------------------------------
vi.mock("@/lib/api/client", () => ({
  coachChat: vi.fn(),
}));

import * as apiClient from "@/lib/api/client";
import { CoachChat } from "../chat";

/** Helper to create an async generator that yields the given chunks */
async function* makeChunkStream(chunks: Array<{ event: "token" | "done" | "error"; data: string }>) {
  for (const chunk of chunks) {
    yield chunk;
  }
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CoachChat", () => {
  it("renders the input placeholder", () => {
    vi.mocked(apiClient.coachChat).mockImplementation(() =>
      makeChunkStream([])
    );
    render(<CoachChat />);
    expect(
      screen.getByPlaceholderText(/ask me anything/i)
    ).toBeInTheDocument();
  });

  it("renders suggested chips when no messages", () => {
    vi.mocked(apiClient.coachChat).mockImplementation(() =>
      makeChunkStream([])
    );
    render(<CoachChat />);
    // At least one suggested chip visible
    const chips = screen.getAllByRole("button", { name: /.+/ });
    // There should be suggested chips + the send button
    expect(chips.length).toBeGreaterThan(1);
  });

  it("sends a message and appends it as a user bubble", async () => {
    vi.mocked(apiClient.coachChat).mockImplementation(() =>
      makeChunkStream([{ event: "done", data: "" }])
    );

    render(<CoachChat />);
    const input = screen.getByPlaceholderText(/ask me anything/i);
    await act(async () => {
      fireEvent.change(input, { target: { value: "How is my sleep?" } });
    });
    await act(async () => {
      fireEvent.submit(input.closest("form")!);
    });

    expect(screen.getByText("How is my sleep?")).toBeInTheDocument();
  });

  it("concatenates token chunks into the assistant bubble", async () => {
    const chunks = [
      { event: "token" as const, data: "Your " },
      { event: "token" as const, data: "sleep " },
      { event: "token" as const, data: "is great!" },
      { event: "done" as const, data: "" },
    ];
    vi.mocked(apiClient.coachChat).mockImplementation(() =>
      makeChunkStream(chunks)
    );

    render(<CoachChat />);
    const input = screen.getByPlaceholderText(/ask me anything/i);

    await act(async () => {
      fireEvent.change(input, { target: { value: "How is my sleep?" } });
    });
    await act(async () => {
      fireEvent.submit(input.closest("form")!);
    });

    await waitFor(() => {
      expect(screen.getByText("Your sleep is great!")).toBeInTheDocument();
    });
  });

  it("shows a TypingIndicator while waiting for first token", async () => {
    // Stream that never resolves immediately — use a delayed generator
    let resolve!: () => void;
    const waitPromise = new Promise<void>((r) => { resolve = r; });

    async function* slowStream() {
      await waitPromise;
      yield { event: "done" as const, data: "" };
    }
    vi.mocked(apiClient.coachChat).mockImplementation(() => slowStream());

    render(<CoachChat />);
    const input = screen.getByPlaceholderText(/ask me anything/i);

    await act(async () => {
      fireEvent.change(input, { target: { value: "Hello" } });
      fireEvent.submit(input.closest("form")!);
    });

    // TypingIndicator has aria-label="AI is typing"
    expect(screen.getByLabelText(/ai is typing/i)).toBeInTheDocument();

    // Cleanup
    act(() => { resolve(); });
  });

  it("shows an error bubble when coachChat throws", async () => {
    vi.mocked(apiClient.coachChat).mockImplementation(async function* () {
      throw new Error("Network error");
    });

    render(<CoachChat />);
    const input = screen.getByPlaceholderText(/ask me anything/i);

    await act(async () => {
      fireEvent.change(input, { target: { value: "Hello" } });
      fireEvent.submit(input.closest("form")!);
    });

    await waitFor(() => {
      expect(
        screen.getByText(/wasn't able to retrieve/i)
      ).toBeInTheDocument();
    });
  });

  it("prefills the input when a suggested chip is clicked", () => {
    vi.mocked(apiClient.coachChat).mockImplementation(() =>
      makeChunkStream([])
    );

    render(<CoachChat suggestions={["Tell me about sleep"]} />);
    const chip = screen.getByRole("button", { name: "Tell me about sleep" });
    fireEvent.click(chip);

    const input = screen.getByPlaceholderText(/ask me anything/i);
    expect((input as HTMLInputElement).value).toBe("Tell me about sleep");
  });

  it("clears the input after send", async () => {
    vi.mocked(apiClient.coachChat).mockImplementation(() =>
      makeChunkStream([{ event: "done", data: "" }])
    );

    render(<CoachChat />);
    const input = screen.getByPlaceholderText(/ask me anything/i);

    await act(async () => {
      fireEvent.change(input, { target: { value: "Clear me" } });
      fireEvent.submit(input.closest("form")!);
    });

    await waitFor(() => {
      expect((input as HTMLInputElement).value).toBe("");
    });
  });
});
