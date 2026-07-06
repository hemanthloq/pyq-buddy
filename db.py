import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "pyqbuddy.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------------
# Insert helpers
# ------------------------------------------------------------------

def insert_exam(subject: str | None, month: str | None, year: int | None, session_id: str | None = None) -> int:
    """Add a new exam record and return its auto-generated exam_id.

    Args:
        subject:    Name of the subject (e.g. "DBMS"), if extractable. The
                    extraction regex is tuned for one header format and
                    doesn't match everything, so this is nullable the same
                    way month/year already are - a paper from an
                    unrecognized institution/layout shouldn't crash the
                    upload just because we can't label its subject.
        month:      Month the exam was held, if extractable.
        year:       Year the exam was held, if extractable.
        session_id: Browser session that uploaded this exam, or None for
                    baseline/seeded data that should never be auto-deleted.

    Returns:
        The integer primary key of the newly inserted row.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Exams (subject, month, year, session_id) VALUES (?, ?, ?, ?)",
            (subject, month, year, session_id)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_topic(name: str) -> int:
    """Add a new topic tag and return its auto-generated topic_id.

    Args:
        name: Topic label (e.g. "Normalization").

    Returns:
        The integer primary key of the newly inserted row.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
         
        cursor.execute(
            "INSERT INTO Topics (topic_name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return cursor.lastrowid
        pass
    finally:
        conn.close()


def insert_question(exam_id: int, question_number: str, question_text: str, marks: int) -> int:
    """Add a question linked to an existing exam and return its question_id.

    Args:
        exam_id:         FK referencing Exams.
        question_number: Label from the original paper (e.g. "1.a").
        question_text:   Full text of the question.
        marks:           Mark allocation for this question.

    Returns:
        The integer primary key of the newly inserted row.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Questions (question_number, question_text, exam_id, marks) VALUES (?, ?, ?, ?)",
            (question_number, question_text, exam_id, marks)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def link_question_topic(question_id: int, topic_id: int) -> None:
    """Create a many-to-many link between a question and a topic.

    Args:
        question_id: FK referencing Questions.
        topic_id:    FK referencing Topics.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO QuestionTopics (question_id, topic_id) VALUES (?, ?)", (question_id, topic_id))
        conn.commit()   
        
        pass
    finally:
        conn.close()


# ------------------------------------------------------------------
# Query helpers
# ------------------------------------------------------------------

def get_all_questions() -> list:
    """Return every question row in the database.

    Returns:
        List of sqlite3.Row objects (access columns by name).
    """
    conn = _get_conn()
    try:
       cursor = conn.cursor()
       cursor.execute("SELECT * FROM Questions")
       return cursor.fetchall()
    finally:
        conn.close()


def get_questions_by_topic(topic_name: str) -> list:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Questions.*
            FROM Questions
            JOIN QuestionTopics ON Questions.question_id = QuestionTopics.question_id
            JOIN Topics ON QuestionTopics.topic_id = Topics.topic_id
            WHERE Topics.topic_name = ?
            """,
            (topic_name,)
        )
        return cursor.fetchall()
    finally:
        conn.close()

def get_questions_by_exam(exam_id: int) -> list:
    """Return all questions belonging to a specific exam.

    Args:
        exam_id: PK of the exam to filter by.

    Returns:
        List of sqlite3.Row objects for that exam's questions.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM Questions WHERE exam_id = ?
            """,
            (exam_id,)
        )
        return cursor.fetchall()
    finally:
        conn.close()
        
def get_or_create_topic(name: str) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT topic_id FROM Topics WHERE topic_name = ?",
            (name,)
        ).fetchone()
        if row:
            return row[0]
        else:
            topic_id = insert_topic(name)
            return topic_id
    finally:
        conn.close()


# ------------------------------------------------------------------
# Session cleanup helpers
#
# session_id is NULL for baseline/seeded exams, and a client-generated
# string for anything inserted via a live /upload call. Every query below
# filters on session_id explicitly (never a bare "delete everything"), so
# baseline data - which never has a session_id - can't be matched by either
# the exam of these two cleanup entry points, even if session_id lookup
# logic is bugged: NULL never equals a passed-in string in SQL.
# ------------------------------------------------------------------

def get_exam_ids_by_session(session_id: str) -> list:
    """Return exam_ids uploaded under a given browser session."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT exam_id FROM Exams WHERE session_id = ?",
            (session_id,)
        ).fetchall()
        return [row["exam_id"] for row in rows]
    finally:
        conn.close()


def get_stale_session_ids(older_than_minutes: int) -> list:
    """Return session_ids that have gone quiet for more than
    older_than_minutes - checking BOTH sessions that own uploaded exams
    (Exams.session_id/created_at) AND sessions that only ever pointed at
    shared data like the sample (SessionScope.created_at), since a
    sample-only session owns no exam and wouldn't show up in the first check.
    Baseline exams (session_id IS NULL) can't appear via either path.
    """
    conn = _get_conn()
    try:
        threshold = (f"-{older_than_minutes}",)
        by_owned_exam = conn.execute(
            """
            SELECT DISTINCT session_id FROM Exams
            WHERE session_id IS NOT NULL
              AND datetime(created_at) < datetime('now', ? || ' minutes')
            """,
            threshold,
        ).fetchall()
        by_scope = conn.execute(
            """
            SELECT DISTINCT session_id FROM SessionScope
            WHERE datetime(created_at) < datetime('now', ? || ' minutes')
            """,
            threshold,
        ).fetchall()
        ids = {row["session_id"] for row in by_owned_exam} | {row["session_id"] for row in by_scope}
        return list(ids)
    finally:
        conn.close()


def get_baseline_exam_ids() -> list:
    """Return exam_ids for baseline/seeded data (never owned by a session)."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT exam_id FROM Exams WHERE session_id IS NULL").fetchall()
        return [row["exam_id"] for row in rows]
    finally:
        conn.close()


def add_session_scope(session_id: str, exam_ids: list) -> None:
    """Make the given exam_ids searchable by this session. Used both for a
    real upload's own new exam(s) and for "try the sample" pointing at the
    existing baseline exam(s) - the latter without touching Exams.session_id,
    so baseline ownership/deletability is unaffected.
    """
    if not exam_ids:
        return

    conn = _get_conn()
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO SessionScope (session_id, exam_id) VALUES (?, ?)",
            [(session_id, exam_id) for exam_id in exam_ids],
        )
        conn.commit()
    finally:
        conn.close()


def get_session_scope_exam_ids(session_id: str) -> list:
    """Return the exam_ids this session is allowed to search."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT exam_id FROM SessionScope WHERE session_id = ?",
            (session_id,)
        ).fetchall()
        return [row["exam_id"] for row in rows]
    finally:
        conn.close()


def get_session_scope_details(session_id: str) -> list:
    """Per-exam detail (subject/month/year/question_count) for everything in
    this session's scope - the "currently active papers" list. Ordered by
    exam_id so newly added papers land at the end.
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT Exams.exam_id, Exams.subject, Exams.month, Exams.year,
                   COUNT(Questions.question_id) AS question_count
            FROM SessionScope
            JOIN Exams ON SessionScope.exam_id = Exams.exam_id
            LEFT JOIN Questions ON Questions.exam_id = Exams.exam_id
            WHERE SessionScope.session_id = ?
            GROUP BY Exams.exam_id
            ORDER BY Exams.exam_id
            """,
            (session_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def remove_session_scope_entry(session_id: str, exam_id: int) -> None:
    """Remove a single (session_id, exam_id) scope pointer - e.g. a user
    explicitly removing one paper from their active list, as opposed to
    delete_session_scope's full teardown of every pointer a session has.
    """
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM SessionScope WHERE session_id = ? AND exam_id = ?",
            (session_id, exam_id)
        )
        conn.commit()
    finally:
        conn.close()


def count_questions_for_exams(exam_ids: list) -> int:
    """Count of Questions belonging to any of the given exam_ids."""
    if not exam_ids:
        return 0

    conn = _get_conn()
    try:
        placeholders = ",".join("?" * len(exam_ids))
        return conn.execute(
            f"SELECT COUNT(*) FROM Questions WHERE exam_id IN ({placeholders})",
            exam_ids,
        ).fetchone()[0]
    finally:
        conn.close()


def delete_session_scope(session_id: str) -> None:
    """Remove a session's scope entries. Only ever removes SessionScope rows
    (pure visibility pointers) - never touches Exams/Questions, so this is
    always safe to call regardless of what the session pointed at.
    """
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM SessionScope WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def delete_exams(exam_ids: list) -> list:
    """Delete the given exams and their questions (cascading manually -
    SQLite FKs aren't enforced here by default). Returns the question_ids
    that were removed, so the caller can sync the in-memory vector store.

    Refuses to do anything if exam_ids is empty, so an accidental empty
    list can never turn into a mistaken bulk operation.
    """
    if not exam_ids:
        return []

    conn = _get_conn()
    try:
        placeholders = ",".join("?" * len(exam_ids))
        question_ids = [
            row["question_id"] for row in conn.execute(
                f"SELECT question_id FROM Questions WHERE exam_id IN ({placeholders})",
                exam_ids,
            ).fetchall()
        ]

        if question_ids:
            qplaceholders = ",".join("?" * len(question_ids))
            conn.execute(
                f"DELETE FROM QuestionTopics WHERE question_id IN ({qplaceholders})",
                question_ids,
            )
            conn.execute(
                f"DELETE FROM Questions WHERE question_id IN ({qplaceholders})",
                question_ids,
            )

        conn.execute(f"DELETE FROM Exams WHERE exam_id IN ({placeholders})", exam_ids)
        conn.commit()
        return question_ids
    finally:
        conn.close()