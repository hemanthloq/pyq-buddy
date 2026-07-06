import { useEffect, useState } from 'react';

const CYCLE_MS = 1800;

// Plain rounded chalk stick, tilted as if actively writing. Colored via
// the theme's --accent token (red pen in light mode, chalk yellow in dark)
// rather than literal white, so it reads clearly on both backgrounds.
function ChalkIcon({ className }) {
  return (
    <svg viewBox="0 0 40 16" className={className} aria-hidden="true">
      <g transform="rotate(-35 20 8)">
        <rect x="4" y="4" width="30" height="8" rx="4" className="chalk-loader-chalk-body" />
        <rect x="4" y="4" width="10" height="8" rx="4" className="chalk-loader-chalk-tip" />
      </g>
    </svg>
  );
}

// Cycles through `phrases`, each one "written" left-to-right by a chalk
// icon tracking the leading edge, looping through the list for as long as
// `phrases` keeps being rendered (i.e. until the caller's loading state
// ends). Respects prefers-reduced-motion: the phrase rotation keeps going,
// but the writing sweep and chalk icon are replaced with plain static text
// (handled in CSS, see App.css).
export default function ChalkLoader({ phrases }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
    if (phrases.length <= 1) return undefined;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % phrases.length);
    }, CYCLE_MS);
    return () => clearInterval(id);
  }, [phrases]);

  const phrase = phrases[index % phrases.length];

  return (
    <div className="chalk-loader" role="status" aria-live="polite">
      <span className="chalk-loader-ghost" aria-hidden="true">
        {phrase}
      </span>
      <div className="chalk-loader-reveal" key={index}>
        <span className="chalk-loader-text">{phrase}</span>
        <ChalkIcon className="chalk-loader-icon" />
      </div>
    </div>
  );
}
