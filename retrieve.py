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


def retrieve(query, k=5, allowed_exam_ids=None):
    """allowed_exam_ids: if given (even an empty list), restricts the
    candidate pool to questions from those exam_ids BEFORE computing top-k -
    not after, since filtering after top-k risks returning fewer than k
    in-scope results if higher-scoring out-of-scope questions crowd them out.
    None means unrestricted (used for internal/offline calls, not the live
    /ask endpoint, which always scopes to a session).
    """
    query_vector = _get_model().encode(query)

    with _lock:
        rows_snapshot = questions

        if allowed_exam_ids is None:
            candidate_vectors = question_vectors
            candidate_ids = question_ids
        else:
            # Matched by question_id via a dict, not by trusting that
            # `questions` is positionally aligned with `question_ids` - the
            # row lookup below already doesn't trust that alignment (it does
            # a linear search by id), so the filter shouldn't either.
            allowed = set(allowed_exam_ids)
            exam_id_by_qid = {row['question_id']: row['exam_id'] for row in questions}
            mask = np.array(
                [exam_id_by_qid.get(int(qid)) in allowed for qid in question_ids],
                dtype=bool,
            )
            candidate_vectors = question_vectors[mask]
            candidate_ids = question_ids[mask]

        if len(candidate_ids) == 0:
            return []

        scores = util.cos_sim(query_vector, candidate_vectors)
        flat_scores = scores[0]
        top_k = min(k, len(candidate_ids))
        top_k_indices = torch.argsort(flat_scores, descending=True)[:top_k]
        ids_snapshot = candidate_ids

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

    rows: list of dicts/rows with 'question_id', 'question_text', and
    'exam_id' (exam_id is needed for session-scoped search filtering).
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
