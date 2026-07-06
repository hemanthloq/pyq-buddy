// Renders a similarity score as a stamped grade circle - the same visual
// language as a teacher's red-pen mark on a graded paper, reused to show
// AI-match confidence instead of a graded score.
export default function GradeBadge({ score, questionId, delayMs = 0 }) {
  const pct = Math.round(score * 100);
  const seed = questionId ?? pct;
  const rotation = ((seed * 37) % 13) - 6; // -6..6deg, deterministic per question

  return (
    <div
      className="grade-badge"
      style={{
        // Set as a variable, not a direct transform: the stamp-in animation
        // needs to compose its own scale keyframes with this fixed per-badge
        // tilt, and a plain inline transform would get clobbered by (or
        // fight with) the animated one.
        '--rotation': `${rotation}deg`,
        animationDelay: `${delayMs}ms`,
      }}
      role="img"
      aria-label={`${pct} percent match`}
    >
      <span className="grade-badge-value mono">{pct}%</span>
    </div>
  );
}
