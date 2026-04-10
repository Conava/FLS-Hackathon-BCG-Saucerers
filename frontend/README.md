# Longevity Frontend

Next.js 15 App Router · React 19 · Tailwind v4 · TypeScript strict · pnpm

## Quick start

```bash
pnpm install
pnpm dev         # http://localhost:3000
```

## Available commands

| Command           | Description                          |
|-------------------|--------------------------------------|
| `pnpm dev`        | Start development server             |
| `pnpm build`      | Production build                     |
| `pnpm start`      | Start production server              |
| `pnpm lint`       | Run ESLint (next/core-web-vitals)    |
| `pnpm test`       | Run Vitest (single pass)             |
| `pnpm test:watch` | Run Vitest in watch mode             |
| `pnpm typecheck`  | TypeScript type-check (no emit)      |

## Environment

Copy `.env.example` to `.env.local` and set:

```
BACKEND_URL=http://localhost:8080
DEMO_PATIENT_IDS=rebecca@example.com:pt-0199
```

## Stack notes

- **Tailwind v4** — no `tailwind.config.js`. All tokens live in `src/app/globals.css` via `@theme`.
- **Next.js 15** — `params` and `searchParams` are async; always `await params`.
- **Tests** — Vitest + jsdom + @testing-library/react. Config in `vitest.config.ts`.

## Demo walkthrough

Use a phone-sized viewport (375 × 812) or Chrome DevTools mobile emulation.

### Demo accounts

| Label | Patient ID | Notes |
|---|---|---|
| Rebecca | PT0199 | Primary demo account — full seeded data |
| PT0282 | PT0282 | Secondary account |
| PT0001 | PT0001 | Minimal data (empty states demo) |

### 3-minute demo script

1. **Login** — open `/login`, tap "Rebecca (PT0199)" shortcut, tap Sign in → redirects to Today.
2. **Today** — observe vitality ring score + delta, outlook curve, streak badge, today's protocol list, macro rings (or empty state if no meal logged). Tap the vitality ring to open the Signals sheet.
3. **Protocol** — tap any protocol action checkbox to mark it complete (optimistic update).
4. **Coach** — tap the Coach tab. Tap a suggested chip or type a question. Watch the AI reply stream token by token. Verify the AI disclosure banner is visible.
5. **Records** — tap the Records tab. Ask a plain-language question in the Q&A box (e.g. "What are my latest cholesterol values?"). Observe the streamed answer with citations. Scroll down to see the EHR record cards.
6. **Insights** — tap the Insights tab. View the four longevity dimension signal cards. Drag the Future Self Simulator slider to see projected biological age change.
7. **Care** — tap the Care tab. View upcoming appointments and care pillars. Tap a care pillar card to open the booking bottom sheet.
8. **Meal Log** — tap the meal camera icon on Today ("Log a meal") or navigate to /meal-log. Tap "Choose from library", pick a food photo, tap "Analyze my meal". Observe AI macro analysis and longevity swap suggestion.
9. **Me / GDPR** — tap the Me tab. Verify profile name and ID load. Tap "Export my data" — observe confirmation toast. Toggle data source switches. Tap "Sign out" to return to login.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Coach SSE not streaming | Service Worker intercepting the `/api/proxy/coach/stream` request | Open DevTools → Application → Service Workers → tick "Bypass for network", then retry |
| `patient_id` cookie missing | httpOnly cookie not set after login | Check `/api/auth/login` response has `Set-Cookie` header with `HttpOnly; Path=/; SameSite=Lax` |
| Backend 404 on `/v1/patients/PT0199/...` | Backend not running or `BACKEND_URL` wrong | Run `uvicorn api.main:app --reload` in the `api/` directory; verify `.env.local` `BACKEND_URL` |
| Blank insights / empty signal cards | Backend insights endpoint returning empty | Seed data with `make seed` in the project root |
| Build fails with `tailwind.config.js` | An agent recreated the v3 config file | Delete `frontend/tailwind.config.js` — Tailwind v4 configures via `globals.css` only |
