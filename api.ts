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

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  const inferred = inferCodespacesBackendUrl();

  if (inferred) return inferred;
  if (configured && configured.trim().length > 0) return configured;

  return 'http://localhost:8000';
}

export const API_BASE_URL = getApiBaseUrl();

export async function apiGet<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, { cache: 'no-store' });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
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
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function apiDelete<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, { method: 'DELETE', cache: 'no-store' });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
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
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}
