import { useState } from 'react';
import { uploadPdf } from '../api';

export default function UploadScreen({ onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [papers, setPapers] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);

  const handleFile = async (file) => {
    if (!file) return;
    setFileName(file.name);
    setUploading(true);
    setError(null);
    setPapers(null);

    try {
      const data = await uploadPdf(file);
      setPapers(data.papers);
      onUploaded?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-screen">
      <h2 className="upload-heading">Upload a past paper</h2>
      <p className="upload-sub">
        PDF only. We'll detect each paper inside it automatically, even if several years are
        combined into one file.
      </p>

      <label className="file-drop" htmlFor="pdf-input">
        <input
          id="pdf-input"
          type="file"
          accept="application/pdf"
          onChange={(e) => handleFile(e.target.files?.[0])}
          hidden
        />
        <span className="file-drop-label">{fileName || 'No file chosen'}</span>
        <span className="btn-secondary">Browse</span>
      </label>

      {uploading && <p className="upload-status">Extracting questions…</p>}
      {error && <p className="error-note">{error}</p>}

      {papers && (
        <div className="papers-list">
          {papers.map((paper, i) => (
            <div key={paper.exam_id ?? `unparsed-${i}`} className="paper-card">
              {paper.flags.includes('format_not_detected') ? (
                <p className="paper-unparsed">
                  Couldn't detect this paper's question format — skipped.
                </p>
              ) : (
                <>
                  <div className="paper-card-header">
                    <h3 className="paper-title">{paper.subject || 'Unknown subject'}</h3>
                    {paper.flags.includes('month_year_unknown') ? (
                      <span className="info-tag">month/year unknown</span>
                    ) : (
                      <span className="paper-date mono">
                        {paper.month} {paper.year}
                      </span>
                    )}
                  </div>
                  <ul className="question-list">
                    {paper.questions.map((q) => (
                      <li key={q.question_id} className="question-row">
                        <span className="question-number mono">{q.question_number}</span>
                        <span className="question-text">{q.question_text}</span>
                        <span className="question-marks mono">({q.marks} Marks)</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
