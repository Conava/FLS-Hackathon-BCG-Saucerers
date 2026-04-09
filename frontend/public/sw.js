/**
 * Longevity PWA — Service Worker
 *
 * Cache strategy overview:
 *   - SSE endpoint (/api/proxy/coach/chat)  → BYPASS (never intercept)
 *   - All /api/* paths                       → BYPASS (mutations / live data)
 *   - HTML navigation requests              → network-first, cache fallback
 *   - Static assets (_next/static, icons)   → cache-first
 *
 * Cache name is versioned so a redeployment invalidates the old shell.
 */

const CACHE_NAME = "longevity-v1";

/** App-shell URLs to precache on install. */
const APP_SHELL_URLS = [
  "/",
  "/today",
  "/coach",
  "/records",
  "/insights",
  "/care",
  "/me",
  "/login",
  "/onboarding",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-512-maskable.png",
];

// ---------------------------------------------------------------------------
// Install — precache the app shell
// ---------------------------------------------------------------------------
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

// ---------------------------------------------------------------------------
// Activate — claim clients and evict stale caches
// ---------------------------------------------------------------------------
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Fetch — routing logic
// ---------------------------------------------------------------------------
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. BYPASS: SSE coach chat stream — critical, must never be intercepted.
  //    Returning without calling event.respondWith() lets the browser handle it.
  if (url.pathname.includes("/api/proxy/") && url.pathname.includes("/coach/chat")) {
    return;
  }

  // 2. BYPASS: all other API calls (mutations, live data).
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // 3. Only handle same-origin requests.
  if (url.origin !== self.location.origin) {
    return;
  }

  // 4. Only handle GET requests.
  if (request.method !== "GET") {
    return;
  }

  // 5. Static assets — cache-first.
  if (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/icons/")
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            return response;
          })
      )
    );
    return;
  }

  // 6. HTML navigation (and all other same-origin GET) — network-first,
  //    fall back to cached version or cached /today as app-shell.
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful HTML responses for future offline use.
        if (response.ok && request.headers.get("accept")?.includes("text/html")) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() =>
        caches
          .match(request)
          .then((cached) => cached || caches.match("/today"))
      )
  );
});
