import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProtocolList } from "../ProtocolList";
import type { ProtocolActionOut } from "@/lib/api/schemas";

// ─── Mock API client ─────────────────────────────────────────────────────────
vi.mock("@/lib/api/client", () => ({
  completeProtocolAction: vi.fn().mockResolvedValue({ success: true }),
  skipProtocolAction: vi.fn().mockResolvedValue({ id: 1 }),
  reorderProtocolActions: vi.fn().mockResolvedValue(undefined),
}));

// ─── Mock next/navigation ─────────────────────────────────────────────────────
const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh }),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────
function makeAction(overrides: Partial<ProtocolActionOut> = {}): ProtocolActionOut {
  return {
    id: 1,
    protocol_id: 10,
    category: "Nutrition",
    title: "Drink 2L water",
    completed_today: false,
    streak_days: 0,
    dimension: null,
    rationale: null,
    target: null,
    sort_order: 0,
    skipped_today: false,
    skip_reason: null,
    ...overrides,
  };
}

describe("ProtocolList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── Checkbox (complete) ───────────────────────────────────────────────────

  it("renders action titles", () => {
    const actions = [makeAction({ title: "Drink 2L water" })];
    render(<ProtocolList actions={actions} />);
    expect(screen.getByText("Drink 2L water")).toBeInTheDocument();
  });

  it("calls completeProtocolAction and router.refresh when checkbox tapped", async () => {
    const { completeProtocolAction } = await import("@/lib/api/client");
    const actions = [makeAction({ id: 42, title: "Walk 30 min" })];
    render(<ProtocolList actions={actions} />);

    fireEvent.click(screen.getByRole("button", { name: /mark as complete/i }));

    await waitFor(() => {
      expect(completeProtocolAction).toHaveBeenCalledWith(42);
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  // ─── Skip ─────────────────────────────────────────────────────────────────

  it("renders a kebab/options button for each action", () => {
    const actions = [makeAction({ title: "Walk 30 min" })];
    render(<ProtocolList actions={actions} />);
    expect(screen.getByRole("button", { name: /skip options/i })).toBeInTheDocument();
  });

  it("opens skip sheet when kebab button is clicked", () => {
    const actions = [makeAction({ title: "Walk 30 min" })];
    render(<ProtocolList actions={actions} />);
    fireEvent.click(screen.getByRole("button", { name: /skip options/i }));
    expect(screen.getByText("Too busy")).toBeInTheDocument();
    expect(screen.getByText("Didn't feel like it")).toBeInTheDocument();
    expect(screen.getByText("Traveling")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
  });

  it("calls skipProtocolAction with selected reason and then router.refresh", async () => {
    const { skipProtocolAction } = await import("@/lib/api/client");
    const actions = [makeAction({ id: 7, title: "Cold shower" })];
    render(<ProtocolList actions={actions} />);

    fireEvent.click(screen.getByRole("button", { name: /skip options/i }));
    fireEvent.click(screen.getByRole("button", { name: /Too busy/i }));

    await waitFor(() => {
      expect(skipProtocolAction).toHaveBeenCalledWith(7, "Too busy");
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("shows Skipped chip for already-skipped actions", () => {
    const actions = [makeAction({ skipped_today: true, skip_reason: "Traveling" })];
    render(<ProtocolList actions={actions} />);
    expect(screen.getByText("Skipped")).toBeInTheDocument();
  });

  // ─── Reorder ──────────────────────────────────────────────────────────────

  it("renders up/down reorder buttons for each action", () => {
    const actions = [
      makeAction({ id: 1, title: "Action A", sort_order: 0 }),
      makeAction({ id: 2, title: "Action B", sort_order: 1 }),
    ];
    render(<ProtocolList actions={actions} />);
    // Each row should have up and down buttons
    const upButtons = screen.getAllByRole("button", { name: /move up/i });
    const downButtons = screen.getAllByRole("button", { name: /move down/i });
    expect(upButtons.length).toBeGreaterThanOrEqual(1);
    expect(downButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("calls reorderProtocolActions after clicking move down and then router.refresh", async () => {
    const { reorderProtocolActions } = await import("@/lib/api/client");
    const actions = [
      makeAction({ id: 1, title: "Action A", sort_order: 0 }),
      makeAction({ id: 2, title: "Action B", sort_order: 1 }),
    ];
    render(<ProtocolList actions={actions} />);

    // Click "Move down" on the first item
    const downButtons = screen.getAllByRole("button", { name: /move down/i });
    fireEvent.click(downButtons[0]!);

    await waitFor(() => {
      // After moving A down, order becomes [2, 1]
      expect(reorderProtocolActions).toHaveBeenCalledWith([2, 1]);
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("calls reorderProtocolActions after clicking move up and then router.refresh", async () => {
    const { reorderProtocolActions } = await import("@/lib/api/client");
    const actions = [
      makeAction({ id: 1, title: "Action A", sort_order: 0 }),
      makeAction({ id: 2, title: "Action B", sort_order: 1 }),
    ];
    render(<ProtocolList actions={actions} />);

    // Click "Move up" on the second item
    const upButtons = screen.getAllByRole("button", { name: /move up/i });
    fireEvent.click(upButtons[upButtons.length - 1]!);

    await waitFor(() => {
      // After moving B up, order becomes [2, 1]
      expect(reorderProtocolActions).toHaveBeenCalledWith([2, 1]);
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  // ─── Empty state ──────────────────────────────────────────────────────────

  it("renders empty state when actions array is empty", () => {
    render(<ProtocolList actions={[]} />);
    expect(screen.getByText(/no protocol yet/i)).toBeInTheDocument();
  });
});
