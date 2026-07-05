// A dashed underline that draws itself left-to-right beneath the query text,
// like a teacher underlining a phrase while reading, looping gently until
// the summary streams in. Respects prefers-reduced-motion (see index.css).
export default function UnderlineLoader({ query }) {
  return (
    <p className="underline-loader-wrap" aria-live="polite">
      <span className="underline-loader">
        Reading “{query}”…
      </span>
    </p>
  );
}
