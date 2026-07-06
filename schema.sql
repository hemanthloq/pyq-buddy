CREATE TABLE Exams(
   exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
   subject TEXT NOT NULL,
   month TEXT,
   year INTEGER,
   session_id TEXT,
   created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE Questions(
   question_id INTEGER PRIMARY KEY AUTOINCREMENT,
   question_text TEXT NOT NULL,
   question_number TEXT NOT NULL,
   exam_id INTEGER NOT NULL,
   marks INTEGER NOT NULL,
   FOREIGN KEY (exam_id) REFERENCES Exams(exam_id),
   UNIQUE (question_number, exam_id)
);

CREATE TABLE Topics(
   topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
   topic_name TEXT NOT NULL UNIQUE
);

CREATE TABLE QuestionTopics(
   topic_id INTEGER,
   question_id INTEGER,
   PRIMARY KEY (question_id, topic_id),
   FOREIGN KEY (topic_id) REFERENCES Topics(topic_id),
   FOREIGN KEY (question_id) REFERENCES Questions(question_id)
);

-- Which exam(s) a browser session can search. Separate from Exams.session_id
-- (which tracks OWNERSHIP for deletion) because the "try the sample" flow
-- needs many different sessions to all see the same baseline exam(s) without
-- any of them owning it (owning it would make it deletable, and baseline
-- must never be deletable). A real upload's session_id in Exams still marks
-- ownership; its exam_id(s) also get a SessionScope row so it's searchable.
CREATE TABLE SessionScope(
   session_id TEXT NOT NULL,
   exam_id INTEGER NOT NULL,
   created_at TEXT DEFAULT (datetime('now')),
   PRIMARY KEY (session_id, exam_id),
   FOREIGN KEY (exam_id) REFERENCES Exams(exam_id)
);