import "server-only";

import type {
  AppBootstrap,
  AppointmentListOut,
  EHRRecordListOut,
  HealthResponse,
  InsightsListOut,
  PatientProfileOut,
  VitalityOut,
  WearableSeriesOut,
} from "@/lib/contracts";
import { createDemoBootstrap } from "@/lib/demo-data";

const DEFAULT_BASE_URL = "http://localhost:8080";
const DEFAULT_PATIENT_ID = "PT0282";
const DEFAULT_API_KEY = "dev-api-key";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(url, {
      ...init,
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getAppBootstrap(): Promise<AppBootstrap> {
  const baseUrl = (process.env.BACKEND_BASE_URL ?? DEFAULT_BASE_URL).replace(
    /\/$/,
    "",
  );
  const patientId = process.env.DEMO_PATIENT_ID ?? DEFAULT_PATIENT_ID;
  const apiKey = process.env.BACKEND_API_KEY ?? DEFAULT_API_KEY;

  const demo = createDemoBootstrap(patientId);
  const health = await fetchJson<HealthResponse>(`${baseUrl}/healthz`);

  if (!health) {
    return {
      ...demo,
      patientId,
      health: null,
      backendStatus: {
        title: "Demo mode",
        detail: `Could not reach ${baseUrl}. The shell stays runnable by falling back to a local slice 1 snapshot.`,
        reachable: false,
        authenticated: false,
      },
    };
  }

  const headers = {
    "X-API-Key": apiKey,
  };
  const patientBase = `${baseUrl}/patients/${patientId}`;

  const [profile, vitality, wearable, records, insights, appointments] =
    await Promise.all([
      fetchJson<PatientProfileOut>(`${patientBase}/profile`, { headers }),
      fetchJson<VitalityOut>(`${patientBase}/vitality`, { headers }),
      fetchJson<WearableSeriesOut>(`${patientBase}/wearable`, { headers }),
      fetchJson<EHRRecordListOut>(`${patientBase}/records`, { headers }),
      fetchJson<InsightsListOut>(`${patientBase}/insights`, { headers }),
      fetchJson<AppointmentListOut>(`${patientBase}/appointments/`, { headers }),
    ]);

  if (
    !profile ||
    !vitality ||
    !wearable ||
    !records ||
    !insights ||
    !appointments
  ) {
    return {
      ...demo,
      patientId,
      health,
      backendStatus: {
        title: "Health check connected",
        detail:
          "The backend responded to /healthz, but at least one authenticated slice 1 route did not return data. Demo content is shown until the backend is reachable with the configured patient and API key.",
        reachable: true,
        authenticated: false,
      },
    };
  }

  return {
    patientId,
    source: "live",
    health,
    backendStatus: {
      title: "Connected to slice 1 backend",
      detail:
        "Live profile, vitality, wearable, records, insights, and appointments are loaded. Coach remains intentionally shallow until slice 2 exists.",
      reachable: true,
      authenticated: true,
    },
    profile,
    vitality,
    wearable,
    records,
    insights,
    appointments,
  };
}
