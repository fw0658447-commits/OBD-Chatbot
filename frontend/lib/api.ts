function inferCodespacesBackendUrl(): string | null {
  if (typeof window === 'undefined') return null;

  const { protocol, hostname } = window.location;

  if (hostname.includes('.app.github.dev') && hostname.includes('-3000.')) {
    return `${protocol}//${hostname.replace('-3000.', '-8000.')}`;
  }

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  return null;
}

/**
 * Frontend API base.
 *
 * v1.5 default: same-origin Next.js proxy `/api/backend`.
 * This is much more reliable in GitHub Codespaces/iPadOS than calling
 * `localhost:8000` from Safari. The proxy runs inside the frontend container
 * and forwards requests to `http://backend:8000` on the Docker network.
 *
 * Override only when needed with NEXT_PUBLIC_API_BASE_URL.
 */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (configured && configured.length > 0 && configured !== 'auto') {
    return configured;
  }

  if (typeof window !== 'undefined') {
    return '/api/backend';
  }

  return configured || inferCodespacesBackendUrl() || 'http://localhost:8000';
}

export function getApiDisplayUrl(): string {
  const base = getApiBaseUrl();
  if (base === '/api/backend') return 'Codespaces Proxy: /api/backend -> backend:8000';
  return base;
}

async function errorPayload<T>(response: Response, fallback: T): Promise<T> {
  try {
    const data = await response.json();
    return { ...(fallback as any), status: 'error', error: true, http_status: response.status, detail: data?.detail ?? data?.message ?? data } as T;
  } catch {
    return { ...(fallback as any), status: 'error', error: true, http_status: response.status, detail: response.statusText } as T;
  }
}

function networkErrorPayload<T>(fallback: T, error: unknown): T {
  return { ...(fallback as any), status: 'error', error: true, detail: error instanceof Error ? error.message : String(error) } as T;
}

export async function apiGet<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, { cache: 'no-store' });
    if (!response.ok) return await errorPayload(response, fallback);
    return (await response.json()) as T;
  } catch (error) {
    return networkErrorPayload(fallback, error);
  }
}

export async function apiPost<T>(path: string, body: unknown, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store'
    });
    if (!response.ok) return await errorPayload(response, fallback);
    return (await response.json()) as T;
  } catch (error) {
    return networkErrorPayload(fallback, error);
  }
}

export async function apiDelete<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, { method: 'DELETE', cache: 'no-store' });
    if (!response.ok) return await errorPayload(response, fallback);
    return (await response.json()) as T;
  } catch (error) {
    return networkErrorPayload(fallback, error);
  }
}

export function q(value: string) {
  return encodeURIComponent(value);
}

export async function apiPatch<T>(path: string, body: unknown, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store'
    });
    if (!response.ok) return await errorPayload(response, fallback);
    return (await response.json()) as T;
  } catch (error) {
    return networkErrorPayload(fallback, error);
  }
}
