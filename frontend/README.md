# Frontend Shell

Stack: Next.js 15 App Router + React 19 + TypeScript strict + Tailwind v4.

This workspace is the first frontend shell for Longevity+. It stays intentionally shallow:

- mobile-first app shell with a working bottom tab bar
- tabs aligned to the product language in `docs/07-features.md`
- slice 1 backend contracts wired for `Today`, `Records`, `Insights`, `Care`, and `Me`
- explicit placeholder state for `Coach`, because slice 2 backend routes do not exist yet

## Run locally

1. Install Node 20+ and `pnpm`.
2. Open a terminal in `frontend/`.
3. Run `pnpm install`.
4. Run `pnpm dev`.
5. Open [http://localhost:3000](http://localhost:3000).

## Optional backend wiring

Create `frontend/.env.local` if you want the shell to pull live slice 1 data:

```bash
BACKEND_BASE_URL=http://localhost:8080
BACKEND_API_KEY=dev-api-key
DEMO_PATIENT_ID=PT0282
```

If the backend is unavailable, the shell falls back to a local demo snapshot that matches the real slice 1 response shapes so the app still starts cleanly.
