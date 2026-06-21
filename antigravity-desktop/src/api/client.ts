const API_BASE = 'http://127.0.0.1:8000';

async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json();
}

// ── State ───────────────────────────────────────────────────────────────────

export async function getState() {
  return request<Record<string, unknown>>('/api/state');
}

// ── Session ─────────────────────────────────────────────────────────────────

export async function resetSession() {
  return request<{ status: string }>('/api/session/reset', { method: 'POST' });
}

// ── History ─────────────────────────────────────────────────────────────────

export async function getHistory() {
  return request<{ prompts: string[] }>('/api/history');
}

// ── Models ──────────────────────────────────────────────────────────────────

export async function getModels() {
  return request<{ models: Array<{ id: string; name: string; provider: string }> }>('/api/models');
}

// ── Health ──────────────────────────────────────────────────────────────────

export async function getHealth() {
  return request<{ status: string; service: string }>('/api/health');
}

// ── Workspaces ──────────────────────────────────────────────────────────────

export async function getWorkspaces() {
  return request<{ workspaces: Array<Record<string, unknown>> }>('/api/workspaces');
}

export { API_BASE };
