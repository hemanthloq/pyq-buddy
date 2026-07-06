import { useEffect, useRef, useState } from 'react';
import { CHALK_PATHS } from '../chalkPaths.generated.js';

// Tuned so a typical medium-length phrase (~2500 path units, see
// chalkPaths.generated.js) draws in a bit over a second, matching the feel
// of the previous fixed 1.6s sweep - but scaling with each phrase's actual
// traced length instead of forcing every phrase through the same duration
// regardless of how much there is to draw.
const DRAW_SPEED_UNITS_PER_MS = 1.7;
const MIN_DRAW_MS = 900;
const MAX_DRAW_MS = 2600;
const HOLD_MS = 550; // pause with the phrase fully drawn before erasing into the next one
const REDUCED_MOTION_CYCLE_MS = 1800;

const PARTICLE_INTERVAL_MS = 90;
const PARTICLE_LIFETIME_MS = 550;

// Rendered as a <g>, nested inside the phrase's own <svg viewBox="...">
// rather than a standalone icon svg - that way its transform can be set
// directly from getPointAtLength() output with no unit conversion between
// the path's coordinate space and CSS pixels. The chalk's contact point
// (the tip, where it "touches" the page) sits at the group's local origin;
// the body trails behind it, so rotating the group to the path's tangent
// direction naturally drags the body along behind the leading tip.
function ChalkIconGroup({ innerRef }) {
  return (
    <g ref={innerRef} className="chalk-loader-icon-group">
      <g transform="rotate(18)">
        <rect x="6" y="-4" width="30" height="8" rx="4" className="chalk-loader-chalk-body" />
        <rect x="-2" y="-4" width="11" height="8" rx="4" className="chalk-loader-chalk-tip" />
      </g>
    </g>
  );
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

// Cycles through `phrases`, tracing each one's real letterforms (see
// chalkPaths.generated.js - pre-generated from an actual handwriting font,
// not an approximation) with a chalk icon that follows the literal path
// geometry via getPointAtLength, then holds briefly before erasing into the
// next phrase. Loops for as long as `phrases` keeps being rendered (i.e.
// until the caller's loading state ends). Respects prefers-reduced-motion:
// phrases still rotate, but as plain static text with no path drawing, no
// icon, and no particles.
export default function ChalkLoader({ phrases }) {
  const [index, setIndex] = useState(0);
  const pathRef = useRef(null);
  const iconRef = useRef(null);
  const particleLayerRef = useRef(null);
  const rafRef = useRef(null);
  const lastParticleAtRef = useRef(0);

  const reduceMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Plain rotation, no drawing - the reduced-motion path never touches the
  // rAF/path-length machinery below at all.
  useEffect(() => {
    if (!reduceMotion) return undefined;
    setIndex(0);
    if (phrases.length <= 1) return undefined;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % phrases.length);
    }, REDUCED_MOTION_CYCLE_MS);
    return () => clearInterval(id);
  }, [phrases, reduceMotion]);

  useEffect(() => {
    if (reduceMotion) return undefined;
    setIndex(0);
    return undefined;
  }, [phrases, reduceMotion]);

  // Draws the current phrase, holds, then advances to the next - driven by
  // a single rAF loop so the stroke reveal and the chalk icon's position
  // are computed from the exact same elapsed-time -> length-along-path
  // value every frame, rather than two animations that merely happen to
  // look synced.
  useEffect(() => {
    if (reduceMotion) return undefined;

    const phrase = phrases[index % phrases.length];
    const entry = CHALK_PATHS[phrase];
    if (!entry) return undefined; // defensive: an un-generated phrase just skips animation for this cycle

    const pathEl = pathRef.current;
    const iconEl = iconRef.current;
    if (!pathEl || !iconEl) return undefined;

    const totalLength = pathEl.getTotalLength();
    const drawDurationMs = clamp(
      totalLength / DRAW_SPEED_UNITS_PER_MS,
      MIN_DRAW_MS,
      MAX_DRAW_MS
    );
    const cycleDurationMs = drawDurationMs + HOLD_MS;

    pathEl.style.strokeDasharray = `${totalLength}`;
    lastParticleAtRef.current = 0;

    let start = null;

    const spawnParticle = (x, y) => {
      const layer = particleLayerRef.current;
      if (!layer) return;
      const particle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      const jitterX = (Math.random() - 0.5) * 6;
      const jitterY = (Math.random() - 0.5) * 4;
      particle.setAttribute('cx', `${x + jitterX}`);
      particle.setAttribute('cy', `${y + jitterY}`);
      particle.setAttribute('r', `${1 + Math.random() * 1.2}`);
      particle.setAttribute('class', 'chalk-loader-particle');
      layer.appendChild(particle);
      window.setTimeout(() => particle.remove(), PARTICLE_LIFETIME_MS);
    };

    const tick = (timestamp) => {
      if (start === null) start = timestamp;
      const elapsed = timestamp - start;
      const drawFraction = clamp(elapsed / drawDurationMs, 0, 1);
      // Ease-out: fast start, gentle settle - matches the previous CSS
      // ease-out sweep's feel.
      const eased = 1 - (1 - drawFraction) ** 2;
      const lengthAlong = eased * totalLength;

      pathEl.style.strokeDashoffset = `${totalLength - lengthAlong}`;

      const point = pathEl.getPointAtLength(lengthAlong);
      const aheadPoint = pathEl.getPointAtLength(clamp(lengthAlong + 1, 0, totalLength));
      const angle = (Math.atan2(aheadPoint.y - point.y, aheadPoint.x - point.x) * 180) / Math.PI;
      iconEl.setAttribute('transform', `translate(${point.x} ${point.y}) rotate(${angle}) scale(0.62)`);

      if (drawFraction < 1 && elapsed - lastParticleAtRef.current > PARTICLE_INTERVAL_MS) {
        lastParticleAtRef.current = elapsed;
        spawnParticle(point.x, point.y);
      }

      if (elapsed < cycleDurationMs) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setIndex((i) => (i + 1) % phrases.length);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (particleLayerRef.current) particleLayerRef.current.replaceChildren();
    };
  }, [phrases, index, reduceMotion]);

  const phrase = phrases[index % phrases.length];
  const entry = CHALK_PATHS[phrase];

  return (
    <div className="chalk-loader" role="status" aria-live="polite">
      <span className="sr-only">{phrase}</span>

      {reduceMotion || !entry ? (
        <span className="chalk-loader-static-text" aria-hidden="true">
          {phrase}
        </span>
      ) : (
        <svg
          key={index}
          viewBox={entry.viewBox}
          className="chalk-loader-svg"
          style={{ aspectRatio: `${entry.width} / ${entry.height}` }}
          aria-hidden="true"
        >
          <path ref={pathRef} d={entry.d} className="chalk-loader-path" />
          <g ref={particleLayerRef} className="chalk-loader-particle-layer" />
          <ChalkIconGroup innerRef={iconRef} />
        </svg>
      )}
    </div>
  );
}
