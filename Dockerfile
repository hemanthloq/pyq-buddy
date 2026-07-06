# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend, serving the built frontend ----
FROM python:3.11-slim

# HF Spaces containers run as UID 1000. Per HF's own documented pattern
# (https://huggingface.co/docs/hub/spaces-sdks-docker, "Permissions"
# section, checked 2026-07-06): switch to the non-root user BEFORE running
# pip, not after - HF's docs explicitly warn that running pip as root then
# switching users can cause permission issues with Python.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

RUN pip install --no-cache-dir --upgrade pip

COPY --chown=user requirements.txt .
# CPU-only torch first, same reasoning as the Render deploy: the default
# PyPI Linux wheel bundles CUDA (~530MB) for no benefit on a CPU box and
# was the single biggest contributor to earlier OOM crashes.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r requirements.txt

# Backend code, schema, and the pre-seeded pyqbuddy.db + question_vectors.npy/
# question_ids.npy - committed to the repo on purpose, same reasoning as
# Render: this filesystem is also ephemeral and resets on restart, so a
# fresh container always needs to start from real, already-embedded data
# rather than re-parsing a PDF or hitting Groq's format-discovery fallback
# on every cold start.
COPY --chown=user . .

# Built frontend from stage 1, replacing the frontend/ source copied above
# with just the production build main.py actually serves.
COPY --chown=user --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
