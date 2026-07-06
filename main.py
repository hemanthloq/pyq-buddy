import asyncio
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import pdfext
import retrieve as retrieve_module
import seed
from groq_client import GroqConfigError
from summarize import generate_summary

STALE_SESSION_MINUTES = 60
STALE_SWEEP_INTERVAL_SECONDS = 600  # 10 minutes


def _delete_session_data(session_id: str):
    """Full teardown for one browser session: remove any exam(s) it owns
    (real uploads) plus its scope pointers (including any pointing at
    shared/baseline data via "use sample" - deleting those pointers never
    touches Exams/Questions, so baseline is unaffected either way).
    """
    exam_ids = db.get_exam_ids_by_session(session_id)
    removed_question_ids = db.delete_exams(exam_ids)
    retrieve_module.remove_questions(removed_question_ids)
    db.delete_session_scope(session_id)
    return {"exams_removed": len(exam_ids), "questions_removed": len(removed_question_ids)}


async def _stale_session_sweep_loop():
    """Backup cleanup for sessions whose sendBeacon never fired (hard crash,
    task-killed tab, etc). Checks immediately on startup, then periodically.
    Best-effort: a failed sweep is logged-and-skipped, never crashes the app.
    """
    while True:
        try:
            for session_id in db.get_stale_session_ids(STALE_SESSION_MINUTES):
                _delete_session_data(session_id)
        except Exception as e:
            print(f"stale session sweep failed: {e}")
        await asyncio.sleep(STALE_SWEEP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_stale_session_sweep_loop())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

# No CORS middleware: frontend and backend are served from the same origin
# in production (this process serves both, see the StaticFiles mount at the
# bottom of this file), and in local dev the Vite dev server proxies API
# paths to this backend (see frontend/vite.config.js) - the browser never
# makes a cross-origin request to this API in either case.


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


@app.get("/session/{session_id}/scope")
def get_session_scope(session_id: str):
    """What this session can currently search - used by the frontend to
    decide whether to show the search UI or the 'go upload' empty state
    (question_count), and to render the "currently active papers" list on
    the Upload tab (papers). Both are per-session, not a global fact about
    the database, and both need to survive tab switches, so the frontend
    keeps this in lifted state rather than re-deriving it from a single
    upload response.
    """
    papers = db.get_session_scope_details(session_id)
    exam_ids = [p["exam_id"] for p in papers]
    question_count = sum(p["question_count"] for p in papers)
    return {"exam_ids": exam_ids, "question_count": question_count, "papers": papers}


@app.post("/session/{session_id}/use-sample")
def use_sample(session_id: str):
    """Point a session at the existing baseline exam(s) without reprocessing
    anything - same searchable outcome as a real upload, no new data.
    """
    baseline_exam_ids = db.get_baseline_exam_ids()
    db.add_session_scope(session_id, baseline_exam_ids)
    question_count = db.count_questions_for_exams(baseline_exam_ids)
    return {"exam_ids": baseline_exam_ids, "question_count": question_count}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), session_id: str | None = Form(None)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={
            "error": "invalid_file_type",
            "message": "Only PDF files are supported.",
        })

    # Every upload gets tied to a session, so it's always eligible for
    # cleanup - never falls through as indistinguishable from baseline data
    # just because the frontend failed to send one.
    session_id = session_id or str(uuid.uuid4())

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
    newly_inserted = []
    new_exam_ids = []

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
        exam_id = db.insert_exam(subject, month, year, session_id=session_id)
        new_exam_ids.append(exam_id)

        questions_out = []
        for question_number, question_text, marks in paper["questions"]:
            question_id = db.insert_question(exam_id, question_number, question_text, marks)
            questions_out.append({
                "question_id": question_id,
                "question_number": question_number,
                "question_text": question_text,
                "marks": marks,
            })
            newly_inserted.append({
                "question_id": question_id,
                "question_text": question_text,
                "exam_id": exam_id,
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

    if newly_inserted:
        try:
            # In-process: reuses the same model singleton retrieve() already
            # caches, and only encodes the new questions from this upload -
            # not a subprocess (which loaded a second full model copy and
            # caused the upload-time OOM) and not a full recompute of every
            # question in the database.
            retrieve_module.add_questions(newly_inserted)
        except Exception as e:
            raise HTTPException(status_code=500, detail={
                "error": "embedding_generation_failed",
                "message": str(e),
            })

    if new_exam_ids:
        db.add_session_scope(session_id, new_exam_ids)

    return {"papers": response_papers, "session_id": session_id}


@app.post("/session/{session_id}/end")
def end_session(session_id: str):
    """sendBeacon can only issue POST, so this is the endpoint the frontend
    actually calls on pagehide. See also DELETE /session/{session_id} below
    for programmatic/manual use.
    """
    return _delete_session_data(session_id)


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    return _delete_session_data(session_id)


@app.delete("/session/{session_id}/papers/{exam_id}")
def remove_paper(session_id: str, exam_id: int):
    """Explicit user action ("Remove" on the active-papers list), as opposed
    to _delete_session_data's full session teardown. Reuses the same
    underlying delete logic: if this session owns the exam (a real upload),
    it's fully deleted (rows + embeddings); if not (e.g. the shared baseline
    sample), only this session's scope pointer to it goes - baseline itself
    is never touched, same protection _delete_session_data already relies on.
    """
    owned_exam_ids = db.get_exam_ids_by_session(session_id)
    if exam_id in owned_exam_ids:
        removed_question_ids = db.delete_exams([exam_id])
        retrieve_module.remove_questions(removed_question_ids)

    db.remove_session_scope_entry(session_id, exam_id)
    return {"removed_exam_id": exam_id}


class AskRequest(BaseModel):
    query: str
    k: int = 5
    session_id: str


@app.post("/ask")
def ask(payload: AskRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail={
            "error": "empty_query",
            "message": "Query can't be empty.",
        })

    k = max(1, min(payload.k, 20))
    allowed_exam_ids = db.get_session_scope_exam_ids(payload.session_id)
    results = _enrich_results(retrieve_module.retrieve(query, k, allowed_exam_ids=allowed_exam_ids))

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


# Serves the built React app (frontend/dist). Mounted at "/" LAST, after
# every API route above - Starlette matches routes in registration order,
# so the specific API paths above always win first and this only catches
# whatever they didn't. Only mounted if the build actually exists: locally,
# most people run the Vite dev server separately and never build dist, and
# StaticFiles raises at import time if its directory is missing.
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
