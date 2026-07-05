import { useCallback, useEffect, useState } from 'react';
import './App.css';
import { getStats } from './api';
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
  const [tab, setTab] = useState('search');
  const [stats, setStats] = useState(null);

  const refreshStats = useCallback(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats({ exam_count: 0, question_count: 0 }));
  }, []);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">PYQ Buddy</h1>
        <nav className="app-nav" aria-label="Screens">
          <button
            type="button"
            className={tab === 'search' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setTab('search')}
          >
            Search
          </button>
          <button
            type="button"
            className={tab === 'upload' ? 'nav-btn active' : 'nav-btn'}
            onClick={() => setTab('upload')}
          >
            Upload
          </button>
        </nav>
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </header>

      <main className="app-main">
        {tab === 'search' ? (
          <SearchScreen
            hasData={stats ? stats.question_count > 0 : null}
            onGoUpload={() => setTab('upload')}
          />
        ) : (
          <UploadScreen onUploaded={refreshStats} />
        )}
      </main>
    </div>
  );
}
