# Standalone full-recompute tool for (re)seeding question_vectors.npy /
# question_ids.npy from every row currently in the database - e.g. after a
# fresh `python seed.py` bulk import, or to rebuild the vector store from
# scratch if it's ever lost. NOT used by the live /upload flow anymore -
# that path calls retrieve.add_questions() in-process instead, since
# spinning up this whole script as a subprocess loaded a second independent
# copy of the model on top of the one already cached in the server process,
# which is what caused the upload-time OOM on Render.
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
