import threading

import db
from sentence_transformers import SentenceTransformer, util
import numpy as np
import torch

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


question_vectors = np.load('question_vectors.npy')
question_ids = np.load('question_ids.npy')
questions = db.get_all_questions()


def retrieve(query, k=5):
    query_vector = _get_model().encode(query)

    with _lock:
        scores = util.cos_sim(query_vector, question_vectors)
        flat_scores = scores[0]
        top_k_indices = torch.argsort(flat_scores, descending=True)[:k]
        ids_snapshot = question_ids
        rows_snapshot = questions

    results = []
    for i in top_k_indices:
        qid = ids_snapshot[i]
        matching_row = None
        for row in rows_snapshot:
            if row['question_id'] == qid:
                matching_row = row
                break
        results.append({
            "question_id": int(qid),
            "score": float(flat_scores[i]),
            "text": matching_row['question_text']
        })

    return results


def add_questions(rows):
    """Embed newly inserted questions and append them to the in-memory and
    on-disk vector store, in-process - reusing the same model singleton
    retrieve() already uses instead of spinning up a second process/model
    copy (the subprocess approach that caused the upload-time OOM).

    rows: list of dicts/rows with 'question_id' and 'question_text'.
    """
    global question_vectors, question_ids, questions

    if not rows:
        return

    new_texts = [row['question_text'] for row in rows]
    new_ids = np.array([row['question_id'] for row in rows], dtype=question_ids.dtype)
    new_vectors = _get_model().encode(new_texts)

    with _lock:
        question_vectors = np.vstack([question_vectors, new_vectors])
        question_ids = np.concatenate([question_ids, new_ids])
        questions = questions + list(rows)

        np.save('question_vectors.npy', question_vectors)
        np.save('question_ids.npy', question_ids)


def remove_questions(remove_ids):
    """Remove questions (e.g. an expired upload session) from the in-memory
    and on-disk vector store, by question_id.
    """
    global question_vectors, question_ids, questions

    if not remove_ids:
        return

    remove_set = set(remove_ids)

    with _lock:
        keep_mask = np.array([qid not in remove_set for qid in question_ids], dtype=bool)

        question_vectors = question_vectors[keep_mask]
        question_ids = question_ids[keep_mask]
        questions = [row for row in questions if row['question_id'] not in remove_set]

        np.save('question_vectors.npy', question_vectors)
        np.save('question_ids.npy', question_ids)


if __name__ == "__main__":
    for r in retrieve("how does the OS keep multiple processes from corrupting shared data"):
        print(r)
