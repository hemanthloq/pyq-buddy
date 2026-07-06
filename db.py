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

def insert_exam(subject: str, month: str | None, year: int | None, session_id: str | None = None) -> int:
    """Add a new exam record and return its auto-generated exam_id.

    Args:
        subject:    Name of the subject (e.g. "DBMS").
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


def get_stale_session_exam_ids(older_than_minutes: int) -> list:
    """Return exam_ids belonging to a session, uploaded more than
    older_than_minutes ago. Baseline exams (session_id IS NULL) are
    excluded by the WHERE clause, not just by convention.
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT exam_id FROM Exams
            WHERE session_id IS NOT NULL
              AND datetime(created_at) < datetime('now', ? || ' minutes')
            """,
            (f"-{older_than_minutes}",)
        ).fetchall()
        return [row["exam_id"] for row in rows]
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