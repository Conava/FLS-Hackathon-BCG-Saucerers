"use client";

/**
 * CarePillarsClient — renders the 3 care pillar cards (Clinics, Diagnostics,
 * Home Care) with tap-to-book interaction.
 *
 * Each PillarCard tap opens the BookAppointmentSheet for that pillar.
 */

import * as React from "react";
import { PillarCard } from "@/components/design/PillarCard";
import { BookAppointmentSheet } from "./BookAppointmentSheet";

interface Pillar {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

/** Icon: clinic/hospital */
function ClinicIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

/** Icon: diagnostics/lab */
function DiagnosticsIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v11" />
      <path d="M3 9h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" />
      <line x1="9" y1="9" x2="9" y2="21" />
    </svg>
  );
}

/** Icon: home care */
function HomeCareIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

const PILLARS: Pillar[] = [
  {
    id: "clinics",
    title: "Clinics",
    description: "Book specialist visits and consultations",
    icon: <ClinicIcon />,
  },
  {
    id: "diagnostics",
    title: "Diagnostics",
    description: "Schedule lab tests and imaging panels",
    icon: <DiagnosticsIcon />,
  },
  {
    id: "home-care",
    title: "Home Care",
    description: "Arrange wellness support at home",
    icon: <HomeCareIcon />,
  },
];

/**
 * Interactive pillar card grid. Tapping a card opens the booking sheet.
 */
export function CarePillarsClient() {
  const [activePillar, setActivePillar] = React.useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = React.useState(false);

  const handlePillarTap = (pillarId: string) => {
    setActivePillar(pillarId);
    setSheetOpen(true);
  };

  const handleSheetClose = () => {
    setSheetOpen(false);
  };

  const activePillarTitle =
    PILLARS.find((p) => p.id === activePillar)?.title ?? "Care";

  return (
    <>
      <div
        className="grid grid-cols-3 gap-3"
        role="list"
        aria-label="Care pillars"
      >
        {PILLARS.map((pillar) => (
          <div key={pillar.id} role="listitem">
            <PillarCard
              title={pillar.title}
              description={pillar.description}
              icon={pillar.icon}
              active={activePillar === pillar.id && sheetOpen}
              onClick={() => handlePillarTap(pillar.id)}
            />
          </div>
        ))}
      </div>

      <BookAppointmentSheet
        open={sheetOpen}
        onClose={handleSheetClose}
        pillar={activePillarTitle}
      />
    </>
  );
}
