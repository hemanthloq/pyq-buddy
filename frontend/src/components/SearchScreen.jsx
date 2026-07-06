import { useRef } from 'react';
import ChalkLoader from './ChalkLoader';
import ExampleChips from './ExampleChips';
import GradeBadge from './GradeBadge';

const LOW_CONFIDENCE_THRESHOLD = 0.25;
const CHIP_TYPEWRITER_TOTAL_MS = 380;

const SEARCH_LOADING_PHRASES = [
  'Chalking up an answer…',
  'Digging through old papers…',
  'Sharpening our pencils…',
  'Consulting the syllabus…',
  'Flipping through past papers…',
  'Erasing the wrong turns…',
];

export default function SearchScreen({
  hasData,
  onGoUpload,
  input,
  onInputChange,
  onSubmit,
  activeQuery,
  loading,
  results,
  summary,
  summaryError,
  error,
}) {
  const typewriterToken = useRef(0);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(input);
  };

  // Echoes the loader's handwriting motif: the chip's text is "written"
  // into the box rather than dropped in instantly, then the search runs.
  const handleChipPick = (example) => {
    const token = ++typewriterToken.current;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reduceMotion) {
      onInputChange(example);
      onSubmit(example);
      return;
    }

    const stepMs = Math.max(12, CHIP_TYPEWRITER_TOTAL_MS / example.length);
    let i = 0;

    const tick = () => {
      if (typewriterToken.current !== token) return; // superseded by a newer pick
      i += 1;
      onInputChange(example.slice(0, i));
      if (i < example.length) {
        setTimeout(tick, stepMs);
      } else {
        onSubmit(example);
      }
    };

    tick();
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
        <div className="search-input-wrap">
          <input
            className="search-input"
            type="text"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="Ask it your way — we'll find where it's been asked before"
            aria-label="Search past exam questions"
          />
          <span className="search-input-underline" aria-hidden="true" />
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          Search
        </button>
      </form>

      {!hasSearched && <ExampleChips onPick={handleChipPick} />}

      {loading && <ChalkLoader phrases={SEARCH_LOADING_PHRASES} />}

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
              {results.map((r, i) => (
                <li
                  key={r.question_id}
                  className="result-card"
                  style={{ animationDelay: `${i * 70}ms` }}
                >
                  <GradeBadge score={r.score} questionId={r.question_id} delayMs={i * 70 + 200} />
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
