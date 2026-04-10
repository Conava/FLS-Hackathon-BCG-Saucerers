import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import ServiceWorkerRegister from "@/components/pwa/ServiceWorkerRegister";

describe("ServiceWorkerRegister", () => {
  const registerMock = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    registerMock.mockClear();
    // Provide a mock serviceWorker on navigator
    Object.defineProperty(navigator, "serviceWorker", {
      value: { register: registerMock },
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders null (no DOM nodes)", () => {
    const { container } = render(<ServiceWorkerRegister />);
    expect(container.firstChild).toBeNull();
  });

  it("calls navigator.serviceWorker.register with /sw.js in production", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(<ServiceWorkerRegister />);
    expect(registerMock).toHaveBeenCalledWith("/sw.js");
  });

  it("does not register the service worker outside production", () => {
    // NODE_ENV defaults to 'test' in vitest — no stub needed
    render(<ServiceWorkerRegister />);
    expect(registerMock).not.toHaveBeenCalled();
  });
});
