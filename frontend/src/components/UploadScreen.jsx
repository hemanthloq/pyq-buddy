import { useState } from 'react';
import { uploadPdf, useSample } from '../api';
import { getSessionId } from '../session';
import ChalkLoader from './ChalkLoader';

const EXTRACTION_LOADING_PHRASES = [
  'Flipping through the pages…',
  'Circling every question…',
  'Counting up the marks…',
  'Sorting into piles…',
  'Reading between the lines…',
  'Cross-checking the total…',
];

export default function UploadScreen({ onUploadSuccess, activePapers = [], onRemovePaper }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [unparsedNotice, setUnparsedNotice] = useState(null);
  const [removingId, setRemovingId] = useState(null);

  const handleFile = async (file) => {
    if (!file) return;
    setFileName(file.name);
    setUploading(true);
    setError(null);
    setUnparsedNotice(null);

    try {
      const data = await uploadPdf(file, getSessionId());

      const unparsedCount = data.papers.filter((p) =>
        p.flags.includes('format_not_detected')
      ).length;
      if (unparsedCount > 0) {
        setUnparsedNotice(
          unparsedCount === 1
            ? "Couldn't detect one paper's question format — skipped."
            : `Couldn't detect ${unparsedCount} papers' question format — skipped.`
        );
      }

      const anySucceeded = data.papers.some((p) => !p.flags.includes('format_not_detected'));
      if (anySucceeded) {
        onUploadSuccess?.();
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleUseSample = async () => {
    setUploading(true);
    setError(null);
    setUnparsedNotice(null);

    try {
      await useSample(getSessionId());
      onUploadSuccess?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = async (examId) => {
    setRemovingId(examId);
    setError(null);

    try {
      await onRemovePaper?.(examId);
    } catch (e) {
      setError(e.message);
    } finally {
      setRemovingId(null);
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

      <p className="sample-prompt">
        Want to try it first?{' '}
        <button type="button" className="sample-link" onClick={handleUseSample}>
          Use this sample paper
        </button>
      </p>

      {uploading && <ChalkLoader phrases={EXTRACTION_LOADING_PHRASES} />}
      {error && <p className="error-note">{error}</p>}
      {unparsedNotice && <p className="paper-unparsed">{unparsedNotice}</p>}

      {activePapers.length > 0 && (
        <div className="active-papers">
          <h3 className="active-papers-heading">Currently active for this session</h3>
          <ul className="active-papers-list">
            {activePapers.map((paper) => (
              <li key={paper.exam_id} className="active-paper-row">
                <div className="active-paper-info">
                  <span className="active-paper-subject">
                    {paper.subject || 'Unknown subject'}
                  </span>
                  <span className="active-paper-meta mono">
                    {paper.question_count} question{paper.question_count === 1 ? '' : 's'}
                    {paper.month ? ` · ${paper.month} ${paper.year}` : ''}
                  </span>
                </div>
                <button
                  type="button"
                  className="remove-paper-btn"
                  onClick={() => handleRemove(paper.exam_id)}
                  disabled={removingId === paper.exam_id}
                  aria-label={`Remove ${paper.subject || 'this paper'} from your active search papers`}
                >
                  {removingId === paper.exam_id ? 'Removing…' : 'Remove'}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
