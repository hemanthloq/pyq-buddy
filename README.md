# PYQ Buddy

Upload a past exam paper, and search across every question it contains by *meaning* — not just exact keywords. Ask something like "why do two processes corrupt shared data" and get back the real exam questions testing that idea, even if they're phrased completely differently.

Built as part of a summer project series focused on shipping a full modern AI stack end-to-end: PDF parsing, a normalized SQL schema, sentence embeddings, semantic search, and LLM-assisted extraction — not just wiring up an API and calling it a day.

**Live demo:** https://huggingface.co/spaces/hemanthloq/pyq-buddy

## What it actually does

1. **Upload a PDF** of past exam papers — including combined, multi-year files. Paper-boundary detection automatically splits a single upload into its separate real exams, each with its own subject/month/year where extractable.
2. **Every question gets extracted automatically** — question number, full text, and marks. A regex tuned for the common numbering style handles most papers for free; when a paper uses a different format, an LLM (Groq) discovers the right pattern on the fly instead of failing — cached per document and run at zero temperature, so the same file is never re-parsed differently on a second upload.
3. **Search by meaning, not exact wording.** Every question becomes a 384-dimension embedding (`sentence-transformers`, `all-MiniLM-L6-v2`), and results are ranked by cosine similarity — a question sharing zero words with your search can still surface if it's conceptually related.
4. **Session-scoped, privacy-conscious by design.** Upload your own paper, or try the built-in sample dataset — either way, your search only sees what's relevant to your session, not a mix of every visitor's uploads. Session data is automatically deleted when you leave (via a browser beacon plus a backend safety-net sweep), so a shared public demo doesn't quietly accumulate data forever. The baseline sample dataset is structurally protected from ever being deleted this way.
5. **An AI-generated answer**, not just a category label — search results come with a real, direct answer to what you asked, grounded in the actual retrieved questions and shown alongside them, not a standalone chatbot response.

## Tech stack

- **Backend:** Python, FastAPI, SQLite
- **PDF parsing:** pdfplumber, regex, with Groq (`openai/gpt-oss-20b`) as a cost-gated fallback for unrecognized formats
- **Search:** sentence-transformers, cosine similarity (PyTorch, CPU-only build)
- **Generation:** Groq API
- **Frontend:** React (Vite)
- **Deployment:** Docker, Hugging Face Spaces (single container serving both frontend and backend — same origin, no cross-service CORS complexity)

## How it's structured

```
schema.sql       — 3NF schema: Exams, Questions, Topics, QuestionTopics, SessionScope
db.py            — all database access (parameterized queries, no raw SQL elsewhere)
pdfext.py        — PDF → structured questions, with paper-boundary detection,
                   Groq-based format discovery (cached, deterministic) for
                   papers that don't match the default pattern
groq_client.py   — shared Groq API handling (key loading, typed errors)
summarize.py     — RAG-style answer generation over retrieved questions
embeder.py       — standalone tool for a full manual re-seed of embeddings
retrieve.py      — cosine-similarity search, with add/remove functions for
                   incremental updates and per-session scoping
main.py          — FastAPI endpoints (/upload, /ask, /session/*, /stats),
                   also serves the built React frontend directly
frontend/        — React app: upload flow, session-scoped search, dark/light
                   themes, and the chalk-writing loading animation
Dockerfile       — multi-stage build (Node for the frontend, Python for the
                   backend), packaged for Hugging Face Spaces
```

## Setup (local development)

```bash
git clone <repo-url>
cd pyq-buddy
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com).

```bash
python init_db.py      # creates the database from schema.sql
python seed.py          # extracts and inserts questions from a PDF
python embeder.py       # generates embeddings for all stored questions
uvicorn main:app --reload   # starts the API (serves the frontend too, if built)
```

For the live version, deployment is via Docker on Hugging Face Spaces — see the `Dockerfile` for the exact build.

## Known limitations — worth being upfront about

Semantic search is a real improvement over exact keyword matching, but it isn't perfect, and I tested this rather than assuming it: two sentences describing the same underlying concept, phrased very differently, can sometimes score lower in similarity than intuition suggests — occasionally low enough to miss the top-5 results entirely. This isn't a bug in the implementation; it's an honest characteristic of the embedding model at this scale. The UI surfaces this directly rather than hiding it.

Automatic topic-tagging (e.g. clicking "Deadlock" to browse related questions) isn't implemented. Hardcoding a fixed topic list doesn't scale to arbitrary uploaded subjects, so the product relies on search instead of category browsing — a deliberate scope decision, not an oversight.

Month/year extraction is best-effort — it works when a paper's header matches a known format, and fails gracefully (rather than guessing) when it doesn't. Subject extraction follows the same pattern.

## Engineering notes

The live version originally ran on Render, split across two services (a FastAPI backend and a static frontend). It repeatedly hit Render's free-tier 512MB memory ceiling — first from `torch`'s default GPU-enabled build during install, then from a subprocess accidentally loading a second copy of the embedding model during uploads, then again from extracting larger real-world PDFs. Each was root-caused and fixed individually rather than just reaching for a bigger paid instance, but the pattern made clear that 512MB genuinely wasn't enough headroom for this stack. The app was restructured into a single Docker container and migrated to Hugging Face Spaces, whose free CPU tier provides 16GB — removing the constraint rather than continuing to patch around it. The migration also simplified the architecture: frontend and backend now share one origin, eliminating the CORS/cross-service URL wiring the two-service Render setup required.

## Why I built this

Studying from past-year papers is standard practice, but finding the right question when you only remember the *idea*, not the exact wording, is genuinely annoying. This was also a deliberate excuse to build every layer of a real RAG-adjacent system by hand — schema design, PDF parsing, embeddings, and LLM integration — rather than just calling a single API and shipping a wrapper.
