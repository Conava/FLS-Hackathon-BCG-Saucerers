import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VitalityRing } from "../VitalityRing";
import { ProtocolCard } from "../ProtocolCard";
import { ChatBubble } from "../ChatBubble";
import { AiDisclosureBanner } from "../AiDisclosureBanner";
import { FutureSelfSlider } from "../FutureSelfSlider";
import { BottomSheet } from "../BottomSheet";

// ─── VitalityRing ─────────────────────────────────────────────────────────────

describe("VitalityRing", () => {
  it("renders the score number", () => {
    render(<VitalityRing score={72} delta={3} label="Vitality Score" />);
    expect(screen.getByText("72")).toBeInTheDocument();
  });

  it("renders the label", () => {
    render(<VitalityRing score={72} delta={3} label="Vitality Score" />);
    expect(screen.getByText("Vitality Score")).toBeInTheDocument();
  });

  it("renders positive delta with arrow and label", () => {
    render(<VitalityRing score={72} delta={3} label="Score" />);
    // Delta span contains arrow, absolute value, and "vs last week" text
    expect(screen.getByText(/vs last week/)).toBeInTheDocument();
    expect(screen.getByText(/▲/)).toBeInTheDocument();
  });

  it("renders negative delta with arrow and label", () => {
    render(<VitalityRing score={60} delta={-5} label="Score" />);
    expect(screen.getByText(/vs last week/)).toBeInTheDocument();
    expect(screen.getByText(/▼/)).toBeInTheDocument();
  });

  it("omits delta element when delta is 0", () => {
    render(<VitalityRing score={50} delta={0} label="Score" />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("has an img role with accessible label", () => {
    render(<VitalityRing score={82} delta={1} label="Vitality" />);
    expect(
      screen.getByRole("img", { name: /vitality score 82/i })
    ).toBeInTheDocument();
  });

  it("renders two SVG circles (track + fill)", () => {
    const { container } = render(
      <VitalityRing score={50} delta={0} label="Score" />
    );
    const circles = container.querySelectorAll("circle");
    expect(circles).toHaveLength(2);
  });
});

// ─── ProtocolCard ─────────────────────────────────────────────────────────────

describe("ProtocolCard", () => {
  it("renders the action text", () => {
    render(
      <ProtocolCard
        action="Drink 2L of water"
        done={false}
        onToggle={vi.fn()}
      />
    );
    expect(screen.getByText("Drink 2L of water")).toBeInTheDocument();
  });

  it("calls onToggle when check button is tapped", () => {
    const onToggle = vi.fn();
    render(
      <ProtocolCard
        action="Take vitamins"
        done={false}
        onToggle={onToggle}
      />
    );
    fireEvent.click(
      screen.getByRole("button", { name: /mark as complete/i })
    );
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("shows 'mark as incomplete' label when done", () => {
    render(
      <ProtocolCard
        action="Take vitamins"
        done={true}
        onToggle={vi.fn()}
      />
    );
    expect(
      screen.getByRole("button", { name: /mark as incomplete/i })
    ).toBeInTheDocument();
  });

  it("shows rationale when provided", () => {
    render(
      <ProtocolCard
        action="Walk 30 min"
        rationale="Improves insulin sensitivity"
        done={false}
        onToggle={vi.fn()}
      />
    );
    expect(
      screen.getByText("Improves insulin sensitivity")
    ).toBeInTheDocument();
  });

  it("shows category tag when provided", () => {
    render(
      <ProtocolCard
        action="Eat salmon"
        category="Nutrition"
        done={false}
        onToggle={vi.fn()}
      />
    );
    expect(screen.getByText("Nutrition")).toBeInTheDocument();
  });

  it("strikes through the action text when done", () => {
    render(
      <ProtocolCard action="Sleep 8h" done={true} onToggle={vi.fn()} />
    );
    const text = screen.getByText("Sleep 8h");
    expect(text.className).toMatch(/line-through/);
  });
});

// ─── ChatBubble ───────────────────────────────────────────────────────────────

describe("ChatBubble", () => {
  it("renders the message content", () => {
    render(<ChatBubble role="ai" content="Hello, how can I help?" />);
    expect(screen.getByText("Hello, how can I help?")).toBeInTheDocument();
  });

  it("renders user bubble", () => {
    render(<ChatBubble role="user" content="What should I eat?" />);
    expect(screen.getByText("What should I eat?")).toBeInTheDocument();
  });

  it("shows streaming cursor when streaming=true and role=ai", () => {
    const { container } = render(
      <ChatBubble role="ai" content="Thinking..." streaming={true} />
    );
    // Cursor is an inline-block span with blink animation
    const cursor = container.querySelector("span[aria-hidden='true']");
    expect(cursor).toBeInTheDocument();
  });

  it("does not show streaming cursor for user bubbles", () => {
    const { container } = render(
      <ChatBubble role="user" content="Hello" streaming={true} />
    );
    const cursor = container.querySelector("span[aria-hidden='true']");
    expect(cursor).not.toBeInTheDocument();
  });
});

// ─── AiDisclosureBanner ───────────────────────────────────────────────────────

describe("AiDisclosureBanner", () => {
  it("renders the disclosure text", () => {
    render(<AiDisclosureBanner />);
    expect(
      screen.getByText(/you're talking to an ai/i)
    ).toBeInTheDocument();
  });

  it("has role=note", () => {
    render(<AiDisclosureBanner />);
    expect(screen.getByRole("note")).toBeInTheDocument();
  });

  it("shows the region label (EU-only by default)", () => {
    render(<AiDisclosureBanner />);
    expect(screen.getByText("EU-only")).toBeInTheDocument();
  });

  it("renders a custom region", () => {
    render(<AiDisclosureBanner region="DE" />);
    expect(screen.getByText("DE")).toBeInTheDocument();
  });
});

// ─── FutureSelfSlider ─────────────────────────────────────────────────────────

describe("FutureSelfSlider", () => {
  it("renders the label", () => {
    render(
      <FutureSelfSlider
        label="Sleep"
        value={7}
        min={4}
        max={12}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByText("Sleep")).toBeInTheDocument();
  });

  it("renders the current value", () => {
    render(
      <FutureSelfSlider
        label="Activity"
        value={45}
        min={0}
        max={120}
        unit=" min"
        onChange={vi.fn()}
      />
    );
    expect(screen.getByText("45 min")).toBeInTheDocument();
  });

  it("has an accessible slider role", () => {
    render(
      <FutureSelfSlider
        label="Alcohol"
        value={2}
        min={0}
        max={14}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByRole("slider")).toBeInTheDocument();
  });
});

// ─── BottomSheet ──────────────────────────────────────────────────────────────

describe("BottomSheet", () => {
  it("renders children when open", () => {
    render(
      <BottomSheet open={true} onClose={vi.fn()} title="My Sheet">
        <p>Sheet content</p>
      </BottomSheet>
    );
    expect(screen.getByText("Sheet content")).toBeInTheDocument();
  });

  it("renders the title when provided", () => {
    render(
      <BottomSheet open={true} onClose={vi.fn()} title="Profile">
        <p>Body</p>
      </BottomSheet>
    );
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("does not render content when closed", () => {
    render(
      <BottomSheet open={false} onClose={vi.fn()}>
        <p>Hidden content</p>
      </BottomSheet>
    );
    expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
  });

  it("calls onClose when dialog requests close", () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open={true} onClose={onClose} title="Sheet">
        <p>Content</p>
      </BottomSheet>
    );
    // Press Escape to close the Radix dialog
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
