const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function getSessionScope(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/scope`);
  if (!res.ok) throw new Error('Failed to load session status.');
  return res.json();
}

export async function uploadPdf(file, sessionId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', sessionId);
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail?.message || 'Upload failed.');
  }
  return data;
}

export async function useSample(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/use-sample`, { method: 'POST' });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail?.message || 'Could not load the sample paper.');
  }
  return data;
}

// Fired on pagehide - sendBeacon only supports POST, so cleanup is a POST
// endpoint rather than the more RESTful DELETE (also exposed on the backend
// for manual/programmatic use). No body needed; session_id is in the URL.
export function endSession(sessionId) {
  if (!sessionId) return;
  navigator.sendBeacon(`${API_BASE}/session/${sessionId}/end`);
}

export async function ask(query, sessionId, k = 5) {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k, session_id: sessionId }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail?.message || 'Search failed.');
  }
  return data;
}
