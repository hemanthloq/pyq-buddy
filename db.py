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

def insert_exam(subject: str, month: str | None, year: int | None) -> int:
    """Add a new exam record and return its auto-generated exam_id.

    Args:
        subject: Name of the subject (e.g. "DBMS").
        term:    Exam term/semester string (e.g. "Winter 2024").

    Returns:
        The integer primary key of the newly inserted row.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Exams (subject, month, year) VALUES (?, ?, ?)",
            (subject, month, year)
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