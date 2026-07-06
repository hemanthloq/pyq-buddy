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