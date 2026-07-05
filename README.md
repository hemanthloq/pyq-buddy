# PYQ Buddy

Upload a past exam paper, and search across every question it contains by *meaning* — not just exact keywords. Ask something like "why do two processes corrupt shared data" and get back the real exam questions testing that idea, even if they're phrased completely differently.

Built as part of a summer project series focused on shipping a full modern AI stack end-to-end: PDF parsing, a normalized SQL schema, sentence embeddings, semantic search, and LLM-assisted extraction — not just wiring up an API and calling it a day.

## What it actually does

1. **Upload a PDF** of past exam papers (supports multiple concatenated papers in one file — each one gets detected and stored separately, with its own subject/month/year where extractable).
2. **Every question gets extracted automatically** — question number, full text, and marks — using regex tuned for the common numbering style, with an LLM fallback (via Groq) that discovers the right pattern on the fly if a paper uses a different format.
3. **Search by meaning, not exact wording.** Every question gets converted into a 384-dimension embedding (`sentence-transformers`, `all-MiniLM-L6-v2`). A search query gets embedded the same way, and results are ranked by cosine similarity — so a question that shares zero words with your search can still surface if it's conceptually related.
4. **An AI-generated summary** of the underlying concept, grounded in the actual retrieved questions (via Groq) — not a standalone chatbot answer, always backed by real questions shown alongside it.

## Tech stack

- **Backend:** Python, FastAPI, SQLite
- **PDF parsing:** pdfplumber, regex, with Groq (`openai/gpt-oss-20b`) as a cost-gated fallback for unrecognized formats
- **Search:** sentence-transformers, cosine similarity (PyTorch)
- **Generation:** Groq API
- **Frontend:** React

## How it's structured

```
schema.sql       — 3NF schema: Exams, Questions, Topics, QuestionTopics
db.py            — all database access (parameterized queries, no raw SQL elsewhere)
pdfext.py        — PDF → structured questions, with paper-boundary detection
                   for combined multi-paper PDFs, and Groq-based format
                   discovery when the default regex doesn't match
groq_client.py   — shared Groq API handling (key loading, typed errors)
summarize.py     — RAG-style summary generation over retrieved questions
embeder.py       — generates and saves question embeddings
retrieve.py      — cosine-similarity search over saved embeddings
seed.py          — ties extraction + database insertion together
main.py          — FastAPI endpoints (/upload, /ask)
```

## Setup

```bash
git clone <repo-url>
cd pyq-buddy
pip install -r requirements.txt
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
uvicorn main:app --reload   # starts the API
```

## Known limitations — worth being upfront about

Semantic search is a real improvement over exact keyword matching, but it isn't perfect, and I tested this rather than assuming it: two sentences describing the same underlying concept, phrased very differently, can sometimes score lower in similarity than intuition suggests — occasionally low enough to miss the top-5 results entirely. This isn't a bug in the implementation; it's an honest characteristic of the embedding model at this scale. The UI surfaces this directly rather than hiding it.

Automatic topic-tagging (e.g. clicking "Deadlock" to browse related questions) isn't implemented. Hardcoding a fixed topic list doesn't scale to arbitrary uploaded subjects, so the product relies on search instead of category browsing — a deliberate scope decision, not an oversight.

Month/year extraction is best-effort — it works when a paper's header matches a known format, and fails gracefully (rather than guessing) when it doesn't.

## Why I built this

Studying from past-year papers is standard practice, but finding the right question when you only remember the *idea*, not the exact wording, is genuinely annoying. This was also a deliberate excuse to build every layer of a real RAG-adjacent system by hand — schema design, PDF parsing, embeddings, and LLM integration — rather than just calling a single API and shipping a wrapper.
