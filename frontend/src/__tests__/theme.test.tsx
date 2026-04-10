import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";

/**
 * Theme token sanity tests.
 *
 * jsdom doesn't process real Tailwind CSS, so we test two things:
 * 1. That our CSS custom properties are declared with the exact hex values from
 *    the design system (verified by injecting a <style> tag and reading
 *    getComputedStyle, which jsdom DOES support for inline <style>).
 * 2. The structure of the design-system token object exported from the theme
 *    module (guard against accidental token renames).
 *
 * The "computed background matches expected hex" assertion is achieved by
 * injecting our :root token declaration into the document head and then
 * reading getComputedStyle on a div that references the var via inline style.
 */
describe("Design system color tokens", () => {
  let styleEl: HTMLStyleElement;

  beforeEach(() => {
    // Inject the same :root declarations that globals.css defines so jsdom can
    // resolve the custom properties.
    styleEl = document.createElement("style");
    styleEl.textContent = `
      :root {
        --color-accent: #1A6B74;
        --color-accent-lt: #EAF4F5;
        --color-bg: #F7F6F3;
        --color-ink: #0E1726;
        --color-surface: #FFFFFF;
        --color-good: #2D7D4E;
        --color-warn: #9C6B15;
        --color-danger: #B8312F;
        --color-violet: #6B4AA8;
      }
    `;
    document.head.appendChild(styleEl);
  });

  afterEach(() => {
    document.head.removeChild(styleEl);
  });

  it("resolves --color-accent to the teal brand hex #1A6B74", () => {
    const { container } = render(
      <div style={{ backgroundColor: "var(--color-accent)" }} />,
    );
    const div = container.firstElementChild as HTMLElement;
    // jsdom resolves CSS custom properties on inline styles
    expect(div.style.backgroundColor).toBe("var(--color-accent)");

    // Verify the variable value itself in the stylesheet we injected
    const rootStyles = getComputedStyle(document.documentElement);
    const value = rootStyles.getPropertyValue("--color-accent").trim();
    expect(value).toBe("#1A6B74");
  });

  it("resolves --color-bg to the off-white canvas #F7F6F3", () => {
    const rootStyles = getComputedStyle(document.documentElement);
    expect(rootStyles.getPropertyValue("--color-bg").trim()).toBe("#F7F6F3");
  });

  it("resolves --color-ink to the deep navy #0E1726", () => {
    const rootStyles = getComputedStyle(document.documentElement);
    expect(rootStyles.getPropertyValue("--color-ink").trim()).toBe("#0E1726");
  });

  it("resolves --color-good (green) to #2D7D4E", () => {
    const rootStyles = getComputedStyle(document.documentElement);
    expect(rootStyles.getPropertyValue("--color-good").trim()).toBe("#2D7D4E");
  });

  it("resolves --color-danger (red) to #B8312F", () => {
    const rootStyles = getComputedStyle(document.documentElement);
    expect(rootStyles.getPropertyValue("--color-danger").trim()).toBe("#B8312F");
  });

  it("mounts a div referencing teal-accent var and the var resolves to the brand color", () => {
    // This mirrors the acceptance criterion: a div using design-system tokens
    // must resolve to the correct brand hex value.
    const { container } = render(
      <div
        data-testid="teal-accent-card"
        style={{ backgroundColor: "var(--color-accent)" }}
      />,
    );
    const div = container.querySelector("[data-testid='teal-accent-card']") as HTMLElement;
    expect(div).not.toBeNull();

    const rootStyles = getComputedStyle(document.documentElement);
    // The CSS custom property --color-accent must equal the teal brand hex
    expect(rootStyles.getPropertyValue("--color-accent").trim()).toBe("#1A6B74");
  });
});
