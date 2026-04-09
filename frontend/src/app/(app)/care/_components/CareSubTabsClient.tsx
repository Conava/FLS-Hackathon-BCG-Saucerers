"use client";

/**
 * CareSubTabsClient — horizontal scrollable pill tab bar for the Care screen.
 *
 * Active tab is highlighted with an accent underline / accent colour.
 * Clicking a tab scrolls the matching section into view (anchor-scroll).
 */

import * as React from "react";

interface Tab {
  id: string;
  label: string;
  /** id of the section element to scroll to */
  sectionId: string;
}

const TABS: Tab[] = [
  { id: "clinics", label: "Clinics", sectionId: "care-upcoming" },
  { id: "diagnostics", label: "Diagnostics", sectionId: "care-diagnostics" },
  { id: "home-care", label: "Home care", sectionId: "care-book" },
  { id: "messages", label: "Messages", sectionId: "care-messages" },
  { id: "referrals", label: "Referrals", sectionId: "care-upcoming" },
];

export function CareSubTabsClient() {
  const [active, setActive] = React.useState("clinics");

  const handleClick = (tab: Tab) => {
    setActive(tab.id);
    const el = document.getElementById(tab.sectionId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div
      role="tablist"
      aria-label="Care sections"
      style={{
        display: "flex",
        gap: 6,
        marginTop: 14,
        marginBottom: 12,
        overflowX: "auto",
        /* hide scrollbar */
        scrollbarWidth: "none",
        msOverflowStyle: "none",
      }}
    >
      {TABS.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => handleClick(tab)}
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              border: isActive
                ? "1.5px solid var(--color-accent)"
                : "1px solid var(--color-border)",
              background: isActive ? "var(--color-accent-lt)" : "var(--color-surface)",
              color: isActive ? "var(--color-accent)" : "var(--color-ink-2)",
              fontSize: 12,
              fontWeight: 600,
              whiteSpace: "nowrap",
              cursor: "pointer",
              transition: "all 0.15s",
              flexShrink: 0,
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
