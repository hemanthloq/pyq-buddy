export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={onToggle}
      aria-pressed={isDark}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      <span aria-hidden="true" className="theme-toggle-icon">{isDark ? '☾' : '☀'}</span>
      <span className="theme-toggle-label">{isDark ? 'Chalkboard' : 'Answer booklet'}</span>
    </button>
  );
}
