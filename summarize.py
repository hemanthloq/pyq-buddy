from groq_client import call_groq


def generate_summary(query: str, retrieved_questions: list) -> str:
    """Answer the user's actual query, grounded in (but not restating) a set
    of already-retrieved questions.

    Runs after retrieve() - retrieved_questions is the list of dicts it returns
    (question_id, score, text). Consumes that output; doesn't replace retrieval.
    The question texts themselves aren't repeated in the summary since the
    caller displays the actual question cards alongside it.
    """
    numbered_list = "\n".join(
        f"{i + 1}. {q['text']}" for i, q in enumerate(retrieved_questions)
    )

    prompt = (
        f'A student searched for: "{query}"\n\n'
        "Answer their question directly and clearly, in 3-4 sentences, as you'd "
        "explain it to help them actually understand the concept.\n\n"
        "End with one short sentence pointing to the real exam questions on this "
        "topic shown below (don't repeat the question text itself).\n\n"
        "For grounding/context only (don't quote these back verbatim):\n"
        f"{numbered_list}"
    )

    return call_groq(messages=[{"role": "user", "content": prompt}])
