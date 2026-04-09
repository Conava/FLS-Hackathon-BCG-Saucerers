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
