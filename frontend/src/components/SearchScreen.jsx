import { useState } from 'react';
import { ask } from '../api';
import ExampleChips from './ExampleChips';
import GradeBadge from './GradeBadge';
import UnderlineLoader from './UnderlineLoader';

const LOW_CONFIDENCE_THRESHOLD = 0.25;

export default function SearchScreen({ hasData, onGoUpload }) {
  const [input, setInput] = useState('');
  const [activeQuery, setActiveQuery] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState(null);
  const [error, setError] = useState(null);

  const runSearch = async (rawQuery) => {
    const query = rawQuery.trim();
    if (!query || loading) return;

    setActiveQuery(query);
    setLoading(true);
    setError(null);
    setSummary(null);
    setSummaryError(null);
    setResults(null);

    try {
      const data = await ask(query, 5);
      setResults(data.results);
      setSummary(data.summary);
      setSummaryError(data.summary_error);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    runSearch(input);
  };

  const handleChipPick = (example) => {
    setInput(example);
    runSearch(example);
  };

  if (hasData === null) {
    return <div className="search-screen" />;
  }

  if (hasData === false) {
    return (
      <div className="empty-state">
        <p className="empty-state-heading">No past papers here yet.</p>
        <p className="empty-state-body">Upload a past paper to start searching it.</p>
        <button type="button" className="btn-primary" onClick={onGoUpload}>
          Go to upload
        </button>
      </div>
    );
  }

  const hasSearched = activeQuery !== null;
  const lowConfidence =
    results && results.length > 0 && results.every((r) => r.score < LOW_CONFIDENCE_THRESHOLD);

  return (
    <div className="search-screen">
      <h2 className="search-heading">Find real exam questions on any topic.</h2>

      <form className="search-form" onSubmit={handleSubmit}>
        <input
          className="search-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask it your way — we'll find where it's been asked before"
          aria-label="Search past exam questions"
        />
        <button type="submit" className="btn-primary" disabled={loading}>
          Search
        </button>
      </form>

      {!hasSearched && <ExampleChips onPick={handleChipPick} />}

      {loading && <UnderlineLoader query={activeQuery} />}

      {error && <p className="error-note">{error}</p>}

      {!loading && results && (
        <div className="results-area">
          {summary && !summaryError && <p className="summary-text">{summary}</p>}
          {summaryError && (
            <p className="summary-unavailable">
              Summary unavailable right now — showing matched questions below.
            </p>
          )}

          {lowConfidence ? (
            <p className="empty-note">
              Nothing matched closely — try rephrasing or a different topic.
            </p>
          ) : (
            <ul className="result-list">
              {results.map((r) => (
                <li key={r.question_id} className="result-card">
                  <GradeBadge score={r.score} questionId={r.question_id} />
                  <div className="result-body">
                    <div className="result-meta mono">
                      {r.question_number && <span>{r.question_number}</span>}
                      {r.marks != null && <span>({r.marks} Marks)</span>}
                      {r.subject && (
                        <span className="result-exam">
                          {r.subject}
                          {r.month ? ` · ${r.month} ${r.year}` : ''}
                        </span>
                      )}
                    </div>
                    <p className="result-text">{r.text}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <p className="disclaimer">
            Results are ranked by how closely they match your question's meaning — not exact
            wording. A related question can occasionally miss the top 5. Try rephrasing if
            something feels missing.
          </p>
        </div>
      )}
    </div>
  );
}
