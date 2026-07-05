from groq_client import call_groq


def generate_summary(query: str, retrieved_questions: list) -> str:
    """Summarize the underlying concept behind a set of already-retrieved questions.

    Runs after retrieve() - retrieved_questions is the list of dicts it returns
    (question_id, score, text). Consumes that output; doesn't replace retrieval.
    """
    numbered_list = "\n".join(
        f"{i + 1}. {q['text']}" for i, q in enumerate(retrieved_questions)
    )

    prompt = (
        f'Here are exam questions retrieved for the search "{query}":\n'
        f"{numbered_list}\n\n"
        "In 3-4 sentences, summarize the underlying concept these questions are testing."
    )

    return call_groq(messages=[{"role": "user", "content": prompt}])
