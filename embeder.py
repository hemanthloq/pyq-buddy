import db
from sentence_transformers import SentenceTransformer
import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def main():
    rows = db.get_all_questions()
    question_texts = []
    question_ids = []
    for i in range(len(rows)):
        question_texts.append(rows[i]['question_text'])
        question_ids.append(rows[i]['question_id'])

    vectors = _get_model().encode(question_texts)

    np.save('question_vectors.npy', vectors)
    np.save('question_ids.npy', question_ids)

    print(vectors.shape)
    print(len(question_ids))


if __name__ == "__main__":
    main()
