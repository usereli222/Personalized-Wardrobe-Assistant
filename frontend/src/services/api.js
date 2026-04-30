// Thin fetch wrapper. All API calls go through here so a fresh Firebase
// ID token is attached uniformly and errors surface as Error objects.

import { fbGetIdToken } from './firebase';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const apiUrl = (path) => `${API_BASE}${path}`;

// Backend serves uploaded images at /uploads/<filename>; build a full URL
// the browser can <img src> directly.
export const fileUrl = (relativeOrAbsolute) => {
  if (!relativeOrAbsolute) return null;
  if (/^https?:/i.test(relativeOrAbsolute)) return relativeOrAbsolute;
  const origin = API_BASE.replace(/\/api\/?$/, '');
  return `${origin}${relativeOrAbsolute}`;
};

async function handle(res) {
  if (res.ok) {
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    if (res.status === 204) return null;
    return res;
  }
  let detail = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
  } catch {
    // body wasn't JSON
  }
  const err = new Error(detail);
  err.status = res.status;
  throw err;
}

async function authHeaders(extra = {}) {
  const token = await fbGetIdToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

export const api = {
  get: async (path) =>
    fetch(apiUrl(path), { headers: await authHeaders() }).then(handle),

  postJson: async (path, body) =>
    fetch(apiUrl(path), {
      method: 'POST',
      headers: await authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    }).then(handle),

  postForm: async (path, formData) =>
    fetch(apiUrl(path), {
      method: 'POST',
      headers: await authHeaders(),
      body: formData,
    }).then(handle),

  postFormBlob: async (path, formData) =>
    fetch(apiUrl(path), {
      method: 'POST',
      headers: await authHeaders(),
      body: formData,
    }).then(async (res) => {
      if (!res.ok) return handle(res);
      return res.blob();
    }),

  del: async (path) =>
    fetch(apiUrl(path), { method: 'DELETE', headers: await authHeaders() }).then(handle),
};
