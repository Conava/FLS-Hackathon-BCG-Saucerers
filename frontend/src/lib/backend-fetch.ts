/**
 * Server-side helper for Server Components to call the FastAPI backend.
 *
 * Centralises BACKEND_URL resolution and injects the X-API-Key header from
 * BACKEND_API_KEY so every authenticated call works without duplicating
 * boilerplate. Only use from Server Components — never expose the key to
 * the browser.
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? "";

/**
 * Fetch a path on the backend with the shared API key attached.
 * `path` should start with `/v1/...`.
 */
export async function backendFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (BACKEND_API_KEY && !headers.has("X-API-Key")) {
    headers.set("X-API-Key", BACKEND_API_KEY);
  }
  return fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers,
    cache: init.cache ?? "no-store",
  });
}

export { BACKEND_URL };
