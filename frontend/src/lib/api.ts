/* Thin fetch wrappers over same-origin relative paths.
 *
 * Never build an absolute URL and never read a base-URL env var: relative paths are
 * what make dev (proxied by Vite to localhost:8000) and production (served by
 * FastAPI's own StaticFiles mount) behave identically. Ports the discipline from
 * web/assets/app.js's loadJSON(), which throws on a non-ok response rather than
 * returning a broken value.
 */

async function fetchAndCheck<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${path}: ${res.status}`);
  }
  return (await res.json()) as T;
}

/** Fetch a JSON file served under the /data prefix (web/data/*.json via the proxy/mount). */
export function fetchJson<T>(path: string): Promise<T> {
  return fetchAndCheck<T>(path);
}

/** Fetch a JSON response from an /api/* FastAPI route. */
export function fetchApi<T>(path: string): Promise<T> {
  return fetchAndCheck<T>(path);
}

/** Mirrors web/data/meta.json's fields (see api/main.py's export contract). */
export interface MetaResponse {
  gw: number;
  horizon: number;
  deadline_utc: string;
  generated_utc: string;
  model_mtime_utc: string;
  season: string;
}
