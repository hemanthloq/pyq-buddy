import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import pdfext
import retrieve as retrieve_module
import seed
from groq_client import GroqConfigError
from summarize import generate_summary

BASE_DIR = Path(__file__).parent
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _regenerate_embeddings():
    """Re-run embeder.py as a subprocess so its (untouched) full-recompute
    logic picks up newly inserted questions, then reload retrieve.py's
    module-level caches (vectors/ids/questions) so /ask sees fresh data
    without restarting the server.
    """
    result = subprocess.run(
        [sys.executable, "embeder.py"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or "embeder.py failed")

    importlib.reload(retrieve_module)


def _enrich_results(results):
    """retrieve() only returns {question_id, score, text}. Join in the
    question_number/marks/exam context from the DB for display, without
    modifying retrieve.py itself.
    """
    if not results:
        return results

    conn = db._get_conn()
    try:
        ids = [r["question_id"] for r in results]
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"""
            SELECT Questions.question_id, Questions.question_number, Questions.marks,
                   Exams.exam_id, Exams.subject, Exams.month, Exams.year
            FROM Questions
            JOIN Exams ON Questions.exam_id = Exams.exam_id
            WHERE Questions.question_id IN ({placeholders})
            """,
            ids,
        ).fetchall()
    finally:
        conn.close()

    by_id = {row["question_id"]: dict(row) for row in rows}

    enriched = []
    for r in results:
        extra = by_id.get(r["question_id"], {})
        enriched.append({
            **r,
            "question_number": extra.get("question_number"),
            "marks": extra.get("marks"),
            "exam_id": extra.get("exam_id"),
            "subject": extra.get("subject"),
            "month": extra.get("month"),
            "year": extra.get("year"),
        })
    return enriched


@app.get("/stats")
def get_stats():
    conn = db._get_conn()
    try:
        exam_count = conn.execute("SELECT COUNT(*) FROM Exams").fetchone()[0]
        question_count = conn.execute("SELECT COUNT(*) FROM Questions").fetchone()[0]
    finally:
        conn.close()
    return {"exam_count": exam_count, "question_count": question_count}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={
            "error": "invalid_file_type",
            "message": "Only PDF files are supported.",
        })

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        try:
            papers = pdfext.extract_questions_from_pdf(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail={
                "error": "unreadable_pdf",
                "message": f"Couldn't read this file as a PDF: {e}",
            })
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    response_papers = []
    any_inserted = False

    for paper in papers:
        if paper.get("parse_failed"):
            response_papers.append({
                "exam_id": None,
                "subject": None,
                "month": None,
                "year": None,
                "questions": [],
                "flags": ["format_not_detected"],
            })
            continue

        subject, month, year = seed.extract_metadata(paper["header_text"])
        exam_id = db.insert_exam(subject, month, year)
        any_inserted = True

        questions_out = []
        for question_number, question_text, marks in paper["questions"]:
            question_id = db.insert_question(exam_id, question_number, question_text, marks)
            questions_out.append({
                "question_id": question_id,
                "question_number": question_number,
                "question_text": question_text,
                "marks": marks,
            })

        flags = []
        if month is None or year is None:
            flags.append("month_year_unknown")

        response_papers.append({
            "exam_id": exam_id,
            "subject": subject,
            "month": month,
            "year": year,
            "questions": questions_out,
            "flags": flags,
        })

    if any_inserted:
        try:
            _regenerate_embeddings()
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail={
                "error": "embedding_regeneration_failed",
                "message": str(e),
            })

    return {"papers": response_papers}


class AskRequest(BaseModel):
    query: str
    k: int = 5


@app.post("/ask")
def ask(payload: AskRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail={
            "error": "empty_query",
            "message": "Query can't be empty.",
        })

    k = max(1, min(payload.k, 20))
    results = _enrich_results(retrieve_module.retrieve(query, k))

    try:
        summary = generate_summary(query, results)
        summary_error = None
    except GroqConfigError as e:
        summary = None
        summary_error = {"error": "groq_key_missing", "message": str(e)}
    except Exception as e:
        summary = None
        summary_error = {"error": "summary_failed", "message": str(e)}

    return {"results": results, "summary": summary, "summary_error": summary_error}
