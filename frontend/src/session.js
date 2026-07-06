// One random ID per browser tab, for the tab's lifetime (sessionStorage is
// cleared when the tab closes, and persists across reloads within it). Used
// to tie uploads to "whoever's tab this is" so they can be cleaned up when
// that tab goes away - and reusable later for scoping search to a session.
const STORAGE_KEY = 'pyq-session-id';

export function getSessionId() {
  let id = sessionStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}
