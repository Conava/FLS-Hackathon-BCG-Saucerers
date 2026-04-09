import type { AppBootstrap, TabKey } from "@/lib/contracts";
import { ROUTE_GROUPS } from "@/lib/contracts";
import {
  DATE_TIME_FORMATTER,
  LONG_DATE_FORMATTER,
  SHORT_DATE_FORMATTER,
  describeRecord,
  formatRecordType,
  getInitials,
} from "@/lib/display";
import {
  MetricCard,
  SeverityBadge,
  StatusPill,
  SurfaceCard,
} from "@/components/ui-shell";

export function TodayScreen({
  bootstrap,
  firstName,
}: {
  bootstrap: AppBootstrap;
  firstName: string;
}) {
  const latestWearableDay = bootstrap.wearable.days[0];

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted">
            {LONG_DATE_FORMATTER.format(new Date())}
          </p>
          <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
            Good morning, {firstName}
          </h1>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-accent text-sm font-semibold text-white shadow-[0_8px_18px_rgba(26,107,116,0.28)]">
          {getInitials(bootstrap.profile.name)}
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        <StatusPill tone={bootstrap.source === "live" ? "good" : "neutral"}>
          {bootstrap.backendStatus.title}
        </StatusPill>
        <StatusPill tone="accent">{bootstrap.profile.patient_id}</StatusPill>
        <StatusPill tone="neutral">
          {bootstrap.health?.status === "ok" ? "Healthz ok" : "Healthz pending"}
        </StatusPill>
      </div>

      <SurfaceCard>
        <div className="flex items-center gap-4">
          <div className="flex h-24 w-24 shrink-0 flex-col items-center justify-center rounded-[28px] bg-accent-soft text-accent">
            <span className="text-[10px] font-semibold uppercase tracking-[0.18em]">
              Vitality
            </span>
            <span className="text-4xl font-semibold tracking-[-0.04em]">
              {Math.round(bootstrap.vitality.score)}
            </span>
          </div>

          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted">Light mobile framework</p>
            <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-ink">
              The shell is ready for the current read API
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              {bootstrap.backendStatus.detail}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3">
          <MetricCard
            label="Sleep"
            value={
              latestWearableDay?.sleep_duration_hrs != null
                ? `${latestWearableDay.sleep_duration_hrs.toFixed(1)}h`
                : "n/a"
            }
          />
          <MetricCard
            label="Steps"
            value={
              latestWearableDay?.steps != null
                ? latestWearableDay.steps.toLocaleString("en-GB")
                : "n/a"
            }
          />
          <MetricCard
            label="Insight flags"
            value={String(bootstrap.insights.risk_flags.length)}
          />
        </div>
      </SurfaceCard>

      <SurfaceCard>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
          Live backend structure
        </p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {Object.entries(bootstrap.vitality.subscores).map(([key, value]) => (
            <div key={key} className="rounded-2xl bg-panel px-4 py-3">
              <p className="text-xs font-medium capitalize text-muted">{key}</p>
              <p className="mt-1 text-lg font-semibold text-ink">
                {Math.round(value)}
              </p>
            </div>
          ))}
        </div>
      </SurfaceCard>

      <ContractCard tab="today" />
    </div>
  );
}

export function CoachScreen() {
  return (
    <div className="space-y-4">
      <header>
        <p className="text-sm text-muted">AI disclosure first</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
          Coach
        </h1>
      </header>

      <div className="rounded-[28px] border border-[#d5cefc] bg-[#f2f0fe] p-4">
        <p className="text-sm leading-6 text-[#3d3580]">
          You&apos;re talking to AI. This tab must keep the wellness framing and
          disclosure, but it should stay shallow until slice 2 backend routes
          really exist.
        </p>
      </div>

      <SurfaceCard>
        <p className="text-sm font-semibold text-accent">Reserved for later</p>
        <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-ink">
          No chat or protocol backend is shipped yet
        </h2>
        <p className="mt-3 text-sm leading-6 text-muted">
          The repo already documents Coach, records Q&amp;A, meal vision, and
          protocol generation as slice 2 work. This shell keeps the tab, visual
          rhythm, and disclosure in place without inventing unsupported API
          behavior.
        </p>
      </SurfaceCard>

      <ContractCard tab="coach" />
    </div>
  );
}

export function RecordsScreen({ bootstrap }: { bootstrap: AppBootstrap }) {
  return (
    <div className="space-y-4">
      <header>
        <p className="text-sm text-muted">Provider-backed data</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
          Records
        </h1>
      </header>

      {bootstrap.records.records.map((record) => (
        <SurfaceCard key={record.id}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
                {formatRecordType(record.record_type)}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-ink">
                {describeRecord(record)}
              </h2>
            </div>
            <StatusPill tone="neutral">
              {SHORT_DATE_FORMATTER.format(new Date(record.recorded_at))}
            </StatusPill>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted">
            Source: {record.source}
          </p>
        </SurfaceCard>
      ))}

      <SurfaceCard>
        <p className="text-sm leading-6 text-muted">
          Records stays grounded in provider data. The Q&amp;A layer from the
          mockup is intentionally deferred until the slice 2 AI backend exists.
        </p>
      </SurfaceCard>

      <ContractCard tab="records" />
    </div>
  );
}

export function InsightsScreen({ bootstrap }: { bootstrap: AppBootstrap }) {
  return (
    <div className="space-y-4">
      <header>
        <p className="text-sm text-muted">Derived wellness signals</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
          Insights
        </h1>
      </header>

      {bootstrap.insights.insights.map((insight) => (
        <SurfaceCard key={`${insight.kind}-${insight.message}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
                {insight.kind}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-ink">
                {insight.message}
              </h2>
            </div>
            <SeverityBadge severity={insight.severity} />
          </div>

          <div className="mt-4 grid gap-2">
            {insight.prevention_signals.map((signal) => (
              <div
                key={signal}
                className="rounded-2xl bg-accent-soft px-4 py-3 text-sm text-accent"
              >
                {signal}
              </div>
            ))}
          </div>
        </SurfaceCard>
      ))}

      <ContractCard tab="insights" />
    </div>
  );
}

export function CareScreen({ bootstrap }: { bootstrap: AppBootstrap }) {
  return (
    <div className="space-y-4">
      <header>
        <p className="text-sm text-muted">Appointments in slice 1</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
          Care
        </h1>
      </header>

      {bootstrap.appointments.appointments.map((appointment) => (
        <SurfaceCard key={appointment.id}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
                {appointment.provider}
              </p>
              <h2 className="mt-1 text-lg font-semibold text-ink">
                {appointment.title}
              </h2>
            </div>
            {appointment.covered_percent != null ? (
              <StatusPill tone="good">
                {appointment.covered_percent}% covered
              </StatusPill>
            ) : null}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <MetricCard
              label="When"
              value={DATE_TIME_FORMATTER.format(new Date(appointment.starts_at))}
              compact
            />
            <MetricCard label="Location" value={appointment.location} compact />
          </div>

          {appointment.price_eur != null ? (
            <p className="mt-3 text-sm text-muted">
              Out-of-pocket from EUR {appointment.price_eur.toFixed(0)}
            </p>
          ) : null}
        </SurfaceCard>
      ))}

      <ContractCard tab="care" />
    </div>
  );
}

export function MeScreen({ bootstrap }: { bootstrap: AppBootstrap }) {
  return (
    <div className="space-y-4">
      <header>
        <p className="text-sm text-muted">Profile and privacy shell</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.03em] text-ink">
          Me
        </h1>
      </header>

      <SurfaceCard>
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent text-base font-semibold text-white">
            {getInitials(bootstrap.profile.name)}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-ink">
              {bootstrap.profile.name}
            </h2>
            <p className="text-sm text-muted">
              {bootstrap.profile.country} - {bootstrap.profile.patient_id}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetricCard label="Age" value={String(bootstrap.profile.age)} compact />
          <MetricCard
            label="BMI"
            value={bootstrap.profile.bmi?.toFixed(1) ?? "n/a"}
            compact
          />
          <MetricCard
            label="Weight"
            value={
              bootstrap.profile.weight_kg != null
                ? `${bootstrap.profile.weight_kg} kg`
                : "n/a"
            }
            compact
          />
          <MetricCard
            label="Smoking"
            value={bootstrap.profile.smoking_status ?? "n/a"}
            compact
          />
        </div>
      </SurfaceCard>

      <SurfaceCard>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
          GDPR surfaces
        </p>
        <div className="mt-3 space-y-2 text-sm text-muted">
          <div className="rounded-2xl bg-panel px-4 py-3">
            Export bundles the profile, records, wearable data, and lifestyle
            survey.
          </div>
          <div className="rounded-2xl bg-panel px-4 py-3">
            Delete is still a scheduled acknowledgement in slice 1, not a hard
            destructive action.
          </div>
        </div>
      </SurfaceCard>

      <ContractCard tab="me" />
    </div>
  );
}

function ContractCard({ tab }: { tab: TabKey }) {
  const contract = ROUTE_GROUPS[tab];

  return (
    <SurfaceCard>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
        Backend contract
      </p>
      <h2 className="mt-1 text-lg font-semibold text-ink">{contract.title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted">{contract.note}</p>

      {contract.routes.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {contract.routes.map((route) => (
            <li
              key={route}
              className="rounded-2xl bg-panel px-4 py-3 font-mono text-xs text-ink"
            >
              {route}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-4 rounded-2xl bg-panel px-4 py-3 text-sm text-muted">
          No shipped route yet. Keep this tab limited to disclosure and layout
          until the backend grows.
        </div>
      )}
    </SurfaceCard>
  );
}
