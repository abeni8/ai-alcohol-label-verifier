import React, { useEffect, useRef, useState } from 'react';
import { api, checkFiles, sampleFiles, verify } from './api.mjs';
import { downloadText, resultsCsv } from './export.mjs';
import { runQueue } from './queue.mjs';
import Results from './Results.jsx';

export default function Batch({ config, token, setActive }) {
  const [manifest, setManifest] = useState(null);
  const [files, setFiles] = useState([]);
  const [items, setItems] = useState([]);
  const [errors, setErrors] = useState([]);
  const [error, setError] = useState('');
  const [unused, setUnused] = useState([]);
  const [busy, setBusy] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [selected, setSelected] = useState(null);
  const controller = useRef(null);
  const detailRef = useRef(null);
  const csvInput = useRef(null);
  const imageInput = useRef(null);
  useEffect(() => { setActive(busy || preparing); }, [busy, preparing, setActive]);
  useEffect(() => () => controller.current?.abort(), []);
  function invalidate() { setItems([]); setErrors([]); setError(''); setUnused([]); setSelected(null); }
  function chooseFiles(next) {
    const problem = checkFiles(next, 900);
    invalidate();
    if (problem) { setFiles([]); setError(problem); return; }
    setFiles(next);
  }
  async function loadSampleBatch() {
    setPreparing(true); invalidate();
    try {
      const catalog = await api('/api/samples');
      const names = [...new Set(catalog.filter(item => ['old-tom','wrong-abv','warning-typo','import'].includes(item.id)).flatMap(item => item.filenames))];
      const response = await fetch('/api/sample-files/batch-sample.csv');
      if (!response.ok) throw new Error('The sample CSV could not be loaded.');
      const csvFile = new File([await response.blob()], 'batch-sample.csv', { type: 'text/csv' });
      const imageFiles = await sampleFiles(names);
      setManifest(csvFile); setFiles(imageFiles);
      // Keep native file-picker labels consistent with the loaded sample.
      if (typeof DataTransfer !== 'undefined') {
        const csvTransfer = new DataTransfer(); csvTransfer.items.add(csvFile);
        const imageTransfer = new DataTransfer(); imageFiles.forEach(file => imageTransfer.items.add(file));
        if (csvInput.current) csvInput.current.files = csvTransfer.files;
        if (imageInput.current) imageInput.current.files = imageTransfer.files;
      }
    } catch(e) { setError(e.message); }
    finally { setPreparing(false); }
  }
  async function validateManifest() {
    setError(''); setErrors([]); setItems([]); setSelected(null);
    if (!manifest) { setError('Choose a CSV manifest first.'); return; }
    if (manifest.size > 1000000) { setError('CSV files must be 1 MB or smaller.'); return; }
    const problem = checkFiles(files, 900);
    if (problem) { setError(problem); return; }
    setPreparing(true);
    try {
      const body = new FormData(); body.append('manifest', manifest); body.append('filenames', JSON.stringify(files.map(f => f.name)));
      const data = await api('/api/batch/validate', { method: 'POST', body, headers: token ? { 'X-Review-Token': token } : {} });
      if (!data.valid) { setErrors(data.errors); return; }
      setUnused(data.unused_files);
      setItems(data.rows.map(row => ({ ...row, state: 'pending', result: null, error: '' })));
    } catch(e) { setError(e.message); }
    finally { setPreparing(false); }
  }
  async function start(retry = false) {
    const indices = items.map((item,i) => ({ item,i })).filter(({item}) => retry ? ['failed','cancelled'].includes(item.state) : item.state === 'pending');
    if (!indices.length) return;
    setBusy(true); setError('');
    controller.current = new AbortController();
    const byName = new Map(files.map(file => [file.name, file]));
    try {
      await runQueue(indices.map(({item}) => item), async (item, signal) => {
        const images = item.filenames.map(name => byName.get(name));
        if (images.some(image => !image)) throw new Error('A mapped image is no longer available. Validate the manifest again.');
        return verify(item.application, images, token, signal);
      }, (position, update) => {
        const actual = indices[position].i;
        setItems(old => old.map((row,i) => i === actual ? { ...row, ...update } : row));
      }, { concurrency: 2, signal: controller.current.signal });
    } catch(e) { setError(e.message); }
    finally { setBusy(false); }
  }
  const done = items.filter(item => item.state === 'completed').length;
  const failed = items.filter(item => item.state === 'failed').length;
  const cancelled = items.filter(item => item.state === 'cancelled').length;
  const processing = items.filter(item => item.state === 'processing').length;
  const processed = done + failed + cancelled;
  const hasResults = items.some(item => item.result);
  return <>
    <div className="sample-bar"><div><strong>Review a queue, not one file at a time</strong><span>One CSV row per application; up to three images per row.</span></div><button className="btn btn-outline-primary" type="button" disabled={busy || preparing} onClick={loadSampleBatch}>Load sample batch</button></div>
    {error && <div className="alert alert-danger" role="alert">{error}</div>}
    <section className="panel batch-setup"><div className="panel-heading"><div><div className="eyebrow">01 / PREPARE THE QUEUE</div><h2>Connect application values to images</h2><p className="subtle mb-0">Validation happens before any image analysis. Use exact filenames, separated by <code>|</code> for multiple images.</p></div><a className="btn btn-outline-secondary btn-sm" href="/api/sample-files/batch-template.csv" download>CSV template ↓</a></div>
      <fieldset disabled={busy || preparing} className="panel-body border-0"><div className="row g-4"><div className="col-md-6"><label className="form-label" htmlFor="batch-csv">CSV manifest</label><input className="form-control" id="batch-csv" ref={csvInput} type="file" accept=".csv,text/csv" onChange={e => { invalidate(); setManifest(e.target.files[0] || null); }} /><p className="form-text">UTF-8 CSV · up to 300 applications · 1 MB maximum</p>{manifest && <div className="selected-file">✓ {manifest.name}</div>}</div><div className="col-md-6"><label className="form-label" htmlFor="batch-images">All referenced label images</label><input className="form-control" id="batch-images" ref={imageInput} type="file" accept="image/png,image/jpeg" multiple onChange={e => chooseFiles(Array.from(e.target.files))} /><p className="form-text">JPEG / PNG only · unique filenames · 5 MB per image</p>{files.length > 0 && <div className="selected-file">✓ {files.length} images selected</div>}</div></div><div className="batch-validate"><button className="btn btn-primary" type="button" onClick={validateManifest} disabled={!manifest || !files.length || (config.requires_access_code && !token)}>{preparing ? 'Checking…' : 'Validate CSV & image mapping'}</button><span>No image-service calls are made during validation.</span></div></fieldset>
    </section>
    {errors.length > 0 && <section className="panel manifest-errors" role="alert"><h2>Fix the CSV before starting</h2><p>No applications were submitted for verification.</p><div className="table-responsive"><table className="table"><thead><tr><th>CSV line</th><th>Problem</th></tr></thead><tbody>{errors.map((e,i) => <tr key={i}><td>{e.line}</td><td>{e.message}</td></tr>)}</tbody></table></div></section>}
    {unused.length > 0 && <div className="notice mt-3">{unused.length} selected image(s) are not referenced and will not be sent: {unused.join(', ')}</div>}
    {items.length > 0 && <section className="panel batch-queue" data-testid="batch-queue"><div className="panel-heading"><div><div className="eyebrow">02 / REVIEW QUEUE</div><h2>{busy ? 'Reviewing your batch' : processed === items.length ? (failed || cancelled ? 'Batch finished — attention needed' : 'Batch review complete') : `${items.length} applications ready`}</h2><p className="subtle mb-0">Two applications at a time. Keep this tab open; the queue is not saved.</p></div><div className="queue-actions">{busy ? <button className="btn btn-outline-danger" type="button" onClick={() => controller.current.abort()}>Stop queue</button> : <>{items.some(item => item.state === 'pending') && <button className="btn btn-primary" type="button" disabled={!config.ready || (config.requires_access_code && !token)} onClick={() => start(false)}>Start batch</button>}{(failed > 0 || cancelled > 0) && <button className="btn btn-outline-primary" type="button" onClick={() => start(true)}>Retry unfinished</button>}</>}{(processed > 0 || hasResults) && <button className="btn btn-outline-secondary" type="button" onClick={() => downloadText(resultsCsv(items), 'batch-review-results.csv')}>Export batch CSV</button>}</div></div>
      <div className="queue-progress"><div><strong>{processed} / {items.length} finished</strong><span>{done} completed · {failed} failed · {cancelled} stopped{processing ? ` · ${processing} processing` : ''}</span></div><div className="progress" role="progressbar" aria-label="Batch completion" aria-valuenow={processed} aria-valuemin={0} aria-valuemax={items.length}><div className="progress-bar" style={{ width: `${processed / items.length * 100}%` }} /></div></div>
      <div className="table-responsive"><table className="table queue-table"><caption className="visually-hidden">Batch applications and individual verification results</caption><thead><tr><th scope="col">Application</th><th scope="col">Images</th><th scope="col">Progress / result</th><th scope="col">Details</th></tr></thead><tbody>{items.map((item,i) => <tr key={item.application.application_id} data-testid="batch-row"><th scope="row">{item.application.application_id}<span className="subtle d-block fw-normal">{item.application.brand_name}</span></th><td>{item.filenames.map(name => <span className="filename-line" key={name}>{name}</span>)}</td><td>{item.state === 'completed' ? <><span className="result-badge review">! {item.result.reviews} review needed</span><span className="subtle d-block mt-1">{item.result.matches} matches · {(item.result.browser_elapsed_ms/1000).toFixed(2)}s{item.result.mode === 'demo' ? ' · sample' : ''}</span></> : <><span className={`queue-state ${item.state}`}>{item.state === 'processing' && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}{item.state[0].toUpperCase() + item.state.slice(1)}</span>{item.error && <p className="reason text-danger">{item.error}</p>}</>}</td><td>{item.result && <button className="btn btn-outline-primary btn-sm" type="button" onClick={() => { setSelected(i); setTimeout(() => detailRef.current?.scrollIntoView({ behavior:'smooth' }), 50); }}>Review findings<span className="visually-hidden"> for {item.application.application_id}</span></button>}</td></tr>)}</tbody></table></div>
      <div className="queue-footer">Stopping cancels browser requests; an AI request already sent may still finish and incur usage. Completed results are retained in this tab.</div>
    </section>}
    <div ref={detailRef} className="results-anchor">{selected !== null && items[selected]?.result && <Results key={items[selected].application.application_id} result={items[selected].result} />}</div>
  </>;
}
