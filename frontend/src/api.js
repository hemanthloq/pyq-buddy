// Relative paths: in production, FastAPI serves both the built frontend and
// the API from one origin (HF Spaces exposes a single port), so there's no
// separate API host to point at anymore. In local dev, Vite's dev server
// proxies these same paths to the backend (see vite.config.js) so this
// works unchanged in both environments.

export async function getSessionScope(sessionId) {
  const res = await fetch(`/session/${sessionId}/scope`);
  if (!res.ok) throw new Error('Failed to load session status.');
  return res.json();
}

export async function uploadPdf(file, sessionId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', sessionId);
  const res = await fetch('/upload', { method: 'POST', body: formData });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail?.message || 'Upload failed.');
  }
  return data;
}

export async function useSample(sessionId) {
  const res = await fetch(`/session/${sessionId}/use-sample`, { method: 'POST' });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail?.message || 'Could not load the sample paper.');
  }
  return data;
}

export async function removePaper(sessionId, examId) {
  const res = await fetch(`/session/${sessionId}/papers/${examId}`, { method: 'DELETE' });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data?.detail?.message || 'Could not remove that paper.');
  }
  return data;
}

// Fired on pagehide - sendBeacon only supports POST, so cleanup is a POST
// endpoint rather than the more RESTful DELETE (also exposed on the backend
// for manual/programmatic use). No body needed; session_id is in the URL.
export function endSession(sessionId) {
  if (!sessionId) return;
  navigator.sendBeacon(`/session/${sessionId}/end`);
}

export async function ask(query, sessionId, k = 5) {
  const res = await fetch('/ask', {
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
