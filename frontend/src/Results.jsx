import React, { useState } from 'react';
import { downloadText, resultsCsv } from './export.mjs';

export function Status({ value }) {
  return <span className={`result-badge ${value}`}><span aria-hidden="true">{value === 'match' ? '✓' : value === 'review' ? '!' : '—'}</span>{value === 'match' ? 'Match' : value === 'review' ? 'Review needed' : 'Not checked'}</span>;
}

function Value({ value, long = false }) {
  if (long) return <details className="value-detail"><summary>Read full statement</summary><p>{value}</p></details>;
  return <span className="cell-value">{value}</span>;
}

export default function Results({ result, exportEnabled = true }) {
  const [onlyReview, setOnlyReview] = useState(false);
  const checks = onlyReview ? result.checks.filter(c => c.status === 'review') : result.checks;
  return <section className="panel results-panel" aria-label="Verification results" data-testid="results">
    <div className="panel-heading align-items-start">
      <div><div className="eyebrow">03 / REVIEW FINDINGS</div><h2>What needs your attention</h2><p className="subtle mb-0">{result.application_id} · {result.filenames.length} label image{result.filenames.length === 1 ? '' : 's'}</p></div>
      {exportEnabled && <button className="btn btn-outline-secondary btn-sm" type="button" onClick={() => downloadText(resultsCsv([{ result }]), 'label-review-results.csv')}>Export results</button>}
    </div>
    <div className="result-summary" aria-live="polite">
      <div><strong className="summary-green">{result.matches}</strong><span>Matches</span></div>
      <div><strong className="summary-red">{result.reviews}</strong><span>Review needed</span></div>
      <div><strong>{result.not_checked}</strong><span>Not checked</span></div>
      <div className="timing"><strong>{((result.browser_elapsed_ms ?? result.elapsed_ms) / 1000).toFixed(2)}s</strong><span>{result.mode === 'demo' ? 'Sample run · not AI latency' : 'End-to-end response time'}</span></div>
    </div>
    {result.mode === 'demo' && <div className="notice sample-note">Sample-mode results use known fixture transcriptions, not live image recognition. These timings do not measure AI performance.</div>}
    {result.mode === 'openai' && result.browser_elapsed_ms > 5000 && <div className="notice">This request exceeded the five-second target. Results are shown, but the latency target was not met.</div>}
    <div className="table-toolbar"><p className="mb-0">Green = a matching check. Red = reviewer attention. Neither is an approval.</p><label className="form-check"><input className="form-check-input" type="checkbox" checked={onlyReview} onChange={e => setOnlyReview(e.target.checked)} /><span className="form-check-label">Only review needed</span></label></div>
    <div className="table-responsive"><table className="table comparison-table"><caption className="visually-hidden">Expected application values compared with text extracted from supplied images</caption><thead><tr><th scope="col">Check</th><th scope="col">Application / requirement</th><th scope="col">Label evidence</th><th scope="col">Result</th></tr></thead><tbody>{checks.map(check => <tr key={check.key} data-testid={`check-${check.key}`}>
      <th scope="row">{check.label}</th><td><Value value={check.expected} long={check.key === 'warning_text'} /></td><td><Value value={check.observed} long={check.key === 'warning_text'} /><div className="source-label">{check.image_indices.map(i => `Image ${i}`).join(' · ')}</div></td><td><Status value={check.status} /><p className="reason">{check.reason}</p></td>
    </tr>)}</tbody></table></div>
    {result.checks.some(c => c.key === 'warning_text' && c.status === 'review') && <details className="warning-comparison"><summary>Inspect government warning differences</summary><p className="subtle">Deleted or changed words and punctuation appear below. This is a text comparison, not a second transcription.</p><div className="row g-3"><div className="col-md-6"><h3>Required wording</h3><p>{result.warning_diff.map((part,i) => <React.Fragment key={i}>{part.expected && <span className={part.kind !== 'equal' ? 'diff-mark' : ''}>{part.expected} </span>}</React.Fragment>)}</p></div><div className="col-md-6"><h3>Transcribed wording</h3><p>{result.warning_diff.map((part,i) => <React.Fragment key={i}>{part.observed && <span className={part.kind !== 'equal' ? 'diff-mark' : ''}>{part.observed} </span>}</React.Fragment>)}</p></div></div></details>}
    {result.issues.length > 0 && <div className="extraction-notes"><h3>Extraction notes</h3>{result.issues.map((issue,i) => <p key={i}>{issue}</p>)}</div>}
    <details className="limitations"><summary>Scope and limitations</summary>{result.limitations.map((text,i) => <p key={i}>{text}</p>)}<p>Rules: {result.policy_version} · Extractor: {result.model}</p></details>
  </section>;
}
