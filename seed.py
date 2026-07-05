import re
import sys

import db
from pdfext import extract_questions_from_pdf


def extract_metadata(header_text):
    month = None
    year = None
    subject = None

    month_year = re.search(r'ESA\)\s*-\s*(\w+)\s+(\d{4})', header_text)
    if month_year:
        month = month_year.group(1)
        year = int(month_year.group(2))

    subject_match = re.search(r'[A-Z0-9]+\s*-\s*([A-Za-z ]+)\n', header_text)
    if subject_match:
        subject = subject_match.group(1).strip()

    return subject, month, year


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "OS PYQs-1-6.pdf"

    papers = extract_questions_from_pdf(pdf_path)

    exam_ids = []
    for paper in papers:
        if paper.get("parse_failed"):
            print(f"Couldn't parse this paper's format, skipping: {paper['header_text']!r}")
            continue

        subject, month, year = extract_metadata(paper["header_text"])
        exam_id = db.insert_exam(subject, month, year)
        exam_ids.append(exam_id)

        for question_number, question_text, marks in paper["questions"]:
            db.insert_question(exam_id, question_number, question_text, marks)

    # ------------------------------------------------------------------
    # Spot-check: print results grouped by paper
    # ------------------------------------------------------------------
    print("=== All Questions ===")
    for row in db.get_all_questions():
        print(dict(row))

    print("\n=== Questions by Paper ===")
    for exam_id in exam_ids:
        rows = db.get_questions_by_exam(exam_id)
        total_marks = sum(row["marks"] for row in rows)
        print(f"\n-- exam_id={exam_id} | {len(rows)} questions | {total_marks} marks --")
        for row in rows:
            print(dict(row))


if __name__ == "__main__":
    main()
