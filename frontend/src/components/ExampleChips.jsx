// Curated example queries per known subject, keyed by a normalized
// (lowercased/trimmed) subject name plus any abbreviations we expect to see.
// Subjects not listed here (anything a user actually uploads that we haven't
// curated for) fall back to a generic, subject-name-templated query below -
// less illustrative than a curated one, but still genuinely about whatever
// is actually in this session's scope, which is the whole point: showing
// e.g. OS examples while only a DAA paper is active is actively misleading,
// so "generic but correct" beats "specific but wrong" every time.
const SUBJECT_EXAMPLES = {
  'operating systems': [
    'deadlock',
    'why does paging exist',
    'difference between a process and a thread',
  ],
  os: ['deadlock', 'why does paging exist', 'difference between a process and a thread'],
  'design and analysis of algorithms': [
    'time complexity of merge sort',
    "dijkstra's algorithm",
    'difference between greedy and dynamic programming',
  ],
  daa: [
    'time complexity of merge sort',
    "dijkstra's algorithm",
    'difference between greedy and dynamic programming',
  ],
};

const FALLBACK_EXAMPLES = [
  'a frequently repeated topic',
  'compare two related concepts',
  'a definition likely to be asked',
];

function examplesForSubject(subject) {
  const key = subject?.trim().toLowerCase();
  if (key && SUBJECT_EXAMPLES[key]) return SUBJECT_EXAMPLES[key];
  if (subject) return [`a key idea in ${subject}`, `a common ${subject} exam question`];
  return [];
}

// Builds up to 3 chips from whatever subjects are actually active in this
// session's scope, pulling from each in turn so multiple active subjects
// each get represented rather than one subject crowding out the rest.
function buildExamples(subjects) {
  const pools = subjects.length > 0 ? subjects.map(examplesForSubject) : [FALLBACK_EXAMPLES];
  const chosen = [];
  let round = 0;
  while (chosen.length < 3 && pools.some((pool) => round < pool.length)) {
    for (const pool of pools) {
      if (chosen.length >= 3) break;
      if (round < pool.length) chosen.push(pool[round]);
    }
    round += 1;
  }
  return chosen.length > 0 ? chosen : FALLBACK_EXAMPLES;
}

export default function ExampleChips({ onPick, subjects = [] }) {
  const examples = buildExamples(subjects);

  return (
    <div className="example-chips" role="group" aria-label="Example searches">
      {examples.map((example) => (
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
