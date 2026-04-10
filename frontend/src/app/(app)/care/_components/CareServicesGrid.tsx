"use client";

/**
 * CareServicesGrid — 2-column grid of bookable services.
 *
 * Tapping a card opens the BookAppointmentSheet pre-filled with that service.
 */

import * as React from "react";
import { BookAppointmentSheet } from "./BookAppointmentSheet";

interface Service {
  id: string;
  emoji: string;
  title: string;
  description: string;
}

const SERVICES: Service[] = [
  {
    id: "gp-visit",
    emoji: "🩺",
    title: "GP visit",
    description: "Same-day slots",
  },
  {
    id: "lab-panel",
    emoji: "🧪",
    title: "Lab panel",
    description: "Clinic or home draw",
  },
  {
    id: "imaging",
    emoji: "🫁",
    title: "Imaging",
    description: "DEXA · CIMT · MRI",
  },
  {
    id: "home-care",
    emoji: "🏠",
    title: "Home care",
    description: "Phlebotomy · nurse",
  },
];

/**
 * Interactive 2-column grid for booking care services.
 */
export function CareServicesGrid() {
  const [activeService, setActiveService] = React.useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = React.useState(false);

  const handleTap = (serviceId: string) => {
    setActiveService(serviceId);
    setSheetOpen(true);
  };

  const handleClose = () => {
    setSheetOpen(false);
  };

  const activePillar =
    SERVICES.find((s) => s.id === activeService)?.title ?? "Care";

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
        }}
        aria-label="Book a service"
      >
        {SERVICES.map((service) => (
          <button
            key={service.id}
            type="button"
            onClick={() => handleTap(service.id)}
            style={{
              padding: 14,
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: 14,
              textAlign: "left",
              cursor: "pointer",
              transition: "border-color 0.15s",
            }}
            aria-label={`Book ${service.title}`}
          >
            <div style={{ fontSize: 22 }} aria-hidden="true">
              {service.emoji}
            </div>
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 700,
                marginTop: 6,
                color: "var(--color-ink)",
              }}
            >
              {service.title}
            </div>
            <div
              style={{
                fontSize: 11,
                color: "var(--color-ink-3)",
                marginTop: 2,
              }}
            >
              {service.description}
            </div>
          </button>
        ))}
      </div>

      <BookAppointmentSheet
        open={sheetOpen}
        onClose={handleClose}
        pillar={activePillar}
      />
    </>
  );
}
