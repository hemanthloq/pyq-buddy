const EXAMPLES = [
  'deadlock',
  'why does paging exist',
  'difference between a process and a thread',
];

export default function ExampleChips({ onPick }) {
  return (
    <div className="example-chips" role="group" aria-label="Example searches">
      {EXAMPLES.map((example) => (
        <button
          key={example}
          type="button"
          className="chip"
          onClick={() => onPick(example)}
        >
          {example}
        </button>
      ))}
    </div>
  );
}
