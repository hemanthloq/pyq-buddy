import hashlib
import json
import re

import pdfplumber

DEFAULT_QUESTION_NUMBER_PATTERN = r'\d\.[a-z]\.'
DEFAULT_MARKS_PATTERN = r'(\d+\.\d+) Marks'
DEFAULT_CLEAN_PATTERN = r'\(\d+\.\d+ Marks\)'
MIN_MATCHES_REQUIRED = 3

# Keyed by a hash of the sample text sent to Groq, so re-uploading the exact
# same file never asks the LLM twice: temperature=0 alone doesn't guarantee
# bit-identical output run-to-run (batching/hardware nondeterminism is a
# known LLM-serving caveat), but this discovered pattern controls how the
# WHOLE document gets split into papers, so identical input must always
# produce the identical split. Module-level, not persisted - fine, since the
# worst case on a process restart is one extra Groq call per distinct file.
_DISCOVERY_CACHE = {}


def extract_questions_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        pages_text = [page.extract_text() for page in pdf.pages]
    pages_text = [t for t in pages_text if t is not None]

    full_text = "\n".join(pages_text)

    question_number_pattern = DEFAULT_QUESTION_NUMBER_PATTERN
    marks_pattern = DEFAULT_MARKS_PATTERN
    clean_pattern = DEFAULT_CLEAN_PATTERN

    if _matches_count(question_number_pattern, full_text) < MIN_MATCHES_REQUIRED:
        # Default numbering convention doesn't fit this paper - ask Groq, once,
        # for the whole document, to discover the actual format.
        sample = pages_text[0][:1500] if pages_text else ""
        discovered = _discover_patterns_via_groq(sample)

        if discovered is None or _matches_count(discovered[0], full_text) < MIN_MATCHES_REQUIRED:
            return [{
                "header_text": pages_text[0][:200] if pages_text else "",
                "questions": [],
                "parse_failed": True,
            }]

        question_number_pattern, marks_pattern = discovered
        # No dedicated "clean" regex exists for a discovered format; fall back
        # to stripping whatever the marks pattern itself matched.
        clean_pattern = None

    return _extract_papers(pages_text, question_number_pattern, marks_pattern, clean_pattern)


def _extract_papers(pages_text, question_number_pattern, marks_pattern, clean_pattern):
    papers = []
    current_questions = None
    seen_max = None

    split_pattern = f'({question_number_pattern})'

    for page_text in pages_text:
        pieces = re.split(split_pattern, page_text)
        page_leading_text = pieces[0]

        for i in range(1, len(pieces), 2):
            marker = pieces[i]
            chunk = pieces[i + 1]

            match = re.search(marks_pattern, chunk)
            if not match:
                # Can't determine marks for this fragment - skip it rather
                # than crash the whole document's extraction.
                continue
            try:
                marks = int(float(match.group(1)))
            except (ValueError, IndexError):
                continue

            if clean_pattern:
                clean_text = re.sub(clean_pattern, '', chunk)
            else:
                clean_text = re.sub(marks_pattern, '', chunk)

            leading_int = _leading_int(marker)

            # Strict "<" (not "<=") is required here: sibling sub-parts of the
            # same question share a leading integer (1.a. -> 1.b. -> 1.c. is
            # 1, 1, 1), which would otherwise falsely trip a boundary. A real
            # paper restart is a genuine decrease (... 5.d. -> 1.a. is 5 -> 1).
            is_new_paper = (
                current_questions is None
                or leading_int is None
                or seen_max is None
                or leading_int < seen_max
            )

            if is_new_paper:
                # header_text is only recoverable when the new paper's first
                # question is also the first marker on its page - text before
                # a mid-page boundary is fused into the prior question's chunk.
                header_text = page_leading_text if i == 1 else ""
                current_questions = []
                papers.append({"header_text": header_text, "questions": current_questions})
                seen_max = leading_int
            elif leading_int is not None:
                seen_max = max(seen_max, leading_int)

            current_questions.append((marker, clean_text.strip(), marks))

    return papers


def _leading_int(marker):
    match = re.search(r'\d+', marker)
    return int(match.group()) if match else None


def _matches_count(pattern, text):
    try:
        return len(re.findall(pattern, text))
    except re.error:
        return 0


def _discover_patterns_via_groq(sample_text):
    from groq_client import call_groq

    cache_key = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
    if cache_key in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[cache_key]

    prompt = f"""A default question-numbering regex failed to find enough matches
in an exam paper PDF. The default style is "1.a." (digit, dot, lowercase letter,
dot - e.g. "4.d.") for question numbers, with marks annotated like
"(6.0 Marks)" (regex: (\\d+\\.\\d+) Marks).

This paper uses a different format. Here is a text sample from its first page:

\"\"\"
{sample_text}
\"\"\"

Identify the actual question-numbering and marks-annotation formats used and
return ONLY a JSON object, Python `re`-compatible, in this exact shape:
{{"question_number_pattern": "<regex as a string>", "marks_pattern": "<regex as a string, with a capturing group around the numeric marks value>"}}"""

    try:
        # temperature=0: this discovers the regex used to split the WHOLE
        # document into questions/papers, so it must be reproducible - any
        # sampling variance here means identical input can produce a
        # different discovered pattern (and therefore a different question
        # count/paper split) on every re-upload of the same file.
        content = call_groq(
            messages=[{"role": "user", "content": prompt}],
            json_mode=True,
            temperature=0,
        )
        data = json.loads(content)
        question_number_pattern = data["question_number_pattern"]
        marks_pattern = data["marks_pattern"]
    except Exception:
        # Any failure here (missing key, network error, bad JSON, missing
        # fields) means discovery failed - the caller treats None as "give up"
        # rather than propagating a crash out of a best-effort fallback.
        return None

    if not question_number_pattern or not marks_pattern:
        return None

    result = (question_number_pattern, marks_pattern)
    _DISCOVERY_CACHE[cache_key] = result
    return result
