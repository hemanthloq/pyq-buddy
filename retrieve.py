import db
from sentence_transformers import SentenceTransformer, util
import numpy as np
import torch

_model = None


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
    scores = util.cos_sim(query_vector, question_vectors)
    flat_scores = scores[0]
    top_k_indices = torch.argsort(flat_scores, descending=True)[:k]

    results = []
    for i in top_k_indices:
        qid = question_ids[i]
        matching_row = None
        for row in questions:
            if row['question_id'] == qid:
                matching_row = row
                break
        results.append({
            "question_id": int(qid),
            "score": float(flat_scores[i]),
            "text": matching_row['question_text']
        })

    return results


if __name__ == "__main__":
    for r in retrieve("how does the OS keep multiple processes from corrupting shared data"):
        print(r)