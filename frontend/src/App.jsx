import { useCallback, useEffect, useState } from 'react';
import './App.css';
import { ask, endSession, getSessionScope } from './api';
import { getSessionId } from './session';
import SearchScreen from './components/SearchScreen';
import ThemeToggle from './components/ThemeToggle';
import UploadScreen from './components/UploadScreen';

function useTheme() {
  const [stored, setStored] = useState(() => localStorage.getItem('pyq-theme'));

  useEffect(() => {
    if (stored) {
      document.documentElement.setAttribute('data-theme', stored);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
  }, [stored]);

  const resolved =
    stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  const toggle = () => {
    const next = resolved === 'dark' ? 'light' : 'dark';
    localStorage.setItem('pyq-theme', next);
    setStored(next);
  };

  return [resolved, toggle];
}

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const [tab, setTab] = useState('upload');
  const [scope, setScope] = useState(null);

  // Search state lives here, not inside SearchScreen, so switching to the
  // Upload tab and back doesn't unmount-and-lose the previous query/results.
  const [searchInput, setSearchInput] = useState('');
  const [activeQuery, setActiveQuery] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState(null);
  const [searchError, setSearchError] = useState(null);

  const refreshScope = useCallback(() => {
    getSessionScope(getSessionId())
      .then(setScope)
      .catch(() => setScope({ exam_ids: [], question_count: 0 }));
  }, []);

  useEffect(() => {
    refreshScope();
  }, [refreshScope]);

  useEffect(() => {
    const sessionId = getSessionId();
    const handlePageHide = () => endSession(sessionId);
    window.addEventListener('pagehide', handlePageHide);
    return () => window.removeEventListener('pagehide', handlePageHide);
  }, []);

  const runSearch = useCallback(
    async (rawQuery) => {
      const query = rawQuery.trim();
      if (!query || searchLoading) return;

      setActiveQuery(query);
      setSearchLoading(true);
      setSearchError(null);
      setSummary(null);
      setSummaryError(null);
      setSearchResults(null);

      try {
        const data = await ask(query, getSessionId(), 5);
        setSearchResults(data.results);
        setSummary(data.summary);
        setSummaryError(data.summary_error);
      } catch (e) {
        setSearchError(e.message);
      } finally {
        setSearchLoading(false);
      }
    },
    [searchLoading]
  );

  const handleUploadSuccess = useCallback(() => {
    refreshScope();
    setTab('search');
  }, [refreshScope]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">PYQ Buddy</h1>
        <nav className="app-nav" aria-label="Screens">
          <button
            type="button"
            className={tab === 'upload' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setTab('upload')}
          >
            Upload
          </button>
          <button
            type="button"
            className={tab === 'search' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setTab('search')}
          >
            Search
          </button>
        </nav>
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </header>

      <main className="app-main">
        <div className="tab-panel" key={tab}>
          {tab === 'search' ? (
            <SearchScreen
              hasData={scope ? scope.question_count > 0 : null}
              onGoUpload={() => setTab('upload')}
              input={searchInput}
              onInputChange={setSearchInput}
              onSubmit={runSearch}
              activeQuery={activeQuery}
              loading={searchLoading}
              results={searchResults}
              summary={summary}
              summaryError={summaryError}
              error={searchError}
            />
          ) : (
            <UploadScreen onUploadSuccess={handleUploadSuccess} />
          )}
        </div>
      </main>
    </div>
  );
}
