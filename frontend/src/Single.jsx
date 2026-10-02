import React, { useEffect, useRef, useState } from 'react';
import { api, checkFiles, sampleFiles, verify } from './api.mjs';
import Results from './Results.jsx';

const EMPTY = { application_id: '', beverage_type: 'distilled_spirits', imported: false, brand_name: '', class_type: '', abv: '', net_contents: '', producer_name: '', producer_address: '', country_of_origin: '' };
function TextField({ id, label, value, onChange, placeholder, required = true, type = 'text', maxLength = 250, help }) {
  return <div><label className="form-label" htmlFor={id}>{label}{!required && <span className="optional"> optional</span>}</label><input className="form-control" id={id} name={id} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} required={required} maxLength={maxLength} type={type} {...(type === 'number' ? { min: 0, max: 100, step: 'any' } : {})} />{help && <div className="form-text">{help}</div>}</div>;
}

export default function Single({ config, token, setActive }) {
  const [form, setForm] = useState(EMPTY);
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [sample, setSample] = useState('old-tom');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [drag, setDrag] = useState(false);
  const input = useRef(null);
  const abort = useRef(null);
  const resultsRef = useRef(null);
  useEffect(() => { let current = true; api('/api/samples').then(data => { if (current) setCatalog(data); }).catch(e => { if (current) setError(e.message); }); return () => { current = false; }; }, []);
  useEffect(() => {
    const next = files.map(file => ({ name: file.name, url: URL.createObjectURL(file), size: file.size }));
    setPreviews(next);
    return () => next.forEach(p => URL.revokeObjectURL(p.url));
  }, [files]);
  useEffect(() => {
    setActive(busy || loading);
    if (!busy) return;
    const start = performance.now();
    const timer = setInterval(() => setSeconds((performance.now() - start) / 1000), 100);
    return () => clearInterval(timer);
  }, [busy, loading, setActive]);
  useEffect(() => () => abort.current?.abort(), []);
  function field(name, value) { setForm(old => ({ ...old, [name]: value })); setResult(null); setError(''); }
  function addFiles(selected) {
    if (busy || loading) return;
    const error = checkFiles(selected);
    if (error) { setFiles([]); setResult(null); setError(error); return; }
    setFiles(selected); setResult(null); setError('');
  }
  async function loadSample() {
    const item = catalog.find(x => x.id === sample);
    if (!item) return;
    setLoading(true); setError(''); setResult(null);
    try { const images = await sampleFiles(item.filenames); setForm({ ...item.application }); setFiles(images); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  async function submit(event) {
    event.preventDefault();
    const problem = checkFiles(files);
    if (problem) { setError(problem); return; }
    setBusy(true); setSeconds(0); setError(''); setResult(null);
    abort.current = new AbortController();
    try {
      const data = await verify({ ...form, application_id: form.application_id.trim() || 'Individual application' }, files, token, abort.current.signal);
      setResult(data);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
    } catch (e) { setError(e.name === 'AbortError' ? 'Verification stopped. No result was accepted.' : e.message); }
    finally { setBusy(false); }
  }
  return <>
    <div className="sample-bar"><div><strong>Try a controlled example</strong><span>Known text, deliberate errors, and front/back labels.</span></div><div className="sample-controls"><label className="visually-hidden" htmlFor="sample-choice">Sample scenario</label><select id="sample-choice" className="form-select" value={sample} disabled={busy || loading} onChange={e => setSample(e.target.value)}>{catalog.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select><button type="button" className="btn btn-outline-primary" disabled={busy || loading || !catalog.length} onClick={loadSample}>{loading ? 'Loading…' : 'Load sample'}</button></div></div>
    {error && <div className="alert alert-danger error-box" role="alert"><strong>Action needed. </strong>{error}</div>}
    <form onSubmit={submit}>
      <fieldset disabled={busy || loading} className="row g-4 border-0 p-0 m-0">
        <div className="col-lg-7 ps-lg-0">
          <section className="panel application-panel"><div className="panel-heading"><div><div className="eyebrow">01 / APPLICATION DETAILS</div><h2>What should the label say?</h2><p className="subtle mb-0">Enter the expected values from the application.</p></div></div>
            <div className="panel-body"><div className="row g-3">
              <div className="col-sm-6"><TextField id="application_id" label="Application ID" value={form.application_id} onChange={v => field('application_id', v)} placeholder="e.g. OLD-TOM-001" maxLength={100} required={false} /></div>
              <div className="col-sm-6"><label htmlFor="beverage_type" className="form-label">Beverage type</label><select id="beverage_type" className="form-select" value={form.beverage_type} onChange={e => field('beverage_type', e.target.value)}><option value="distilled_spirits">Distilled spirits</option><option value="wine">Wine</option><option value="malt_beverage">Malt beverage / beer</option></select></div>
              <div className="col-12"><TextField id="brand_name" label="Brand name" value={form.brand_name} onChange={v => field('brand_name',v)} placeholder="OLD TOM DISTILLERY" maxLength={200} /></div>
              <div className="col-12"><TextField id="class_type" label="Class / type designation" value={form.class_type} onChange={v => field('class_type',v)} placeholder="Kentucky Straight Bourbon Whiskey" /></div>
              <div className="col-sm-6"><TextField id="abv" label="Alcohol by volume (%)" value={form.abv} onChange={v => field('abv',v)} placeholder="45" type="number" required={form.beverage_type === 'distilled_spirits'} help="Enter 45 for 45% Alc./Vol. (90 Proof)." /></div>
              <div className="col-sm-6"><TextField id="net_contents" label="Net contents" value={form.net_contents} onChange={v => field('net_contents',v)} placeholder="750 mL" maxLength={60} /></div>
              <div className="col-12"><TextField id="producer_name" label="Bottler / producer name" value={form.producer_name} onChange={v => field('producer_name',v)} placeholder="Old Tom Distillery" /></div>
              <div className="col-12"><TextField id="producer_address" label="Bottler / producer address" value={form.producer_address} onChange={v => field('producer_address',v)} placeholder="Street, city, state / region, postal code" maxLength={400} /></div>
              <div className="col-12"><div className="import-row"><label className="form-check form-switch"><input id="imported" className="form-check-input" type="checkbox" checked={form.imported} onChange={e => { field('imported',e.target.checked); if (!e.target.checked) field('country_of_origin',''); }} /><span className="form-check-label">Imported product</span></label><span className="subtle">Enable country-of-origin comparison</span></div></div>
              {form.imported && <div className="col-12"><TextField id="country_of_origin" label="Country of origin" value={form.country_of_origin} onChange={v => field('country_of_origin',v)} placeholder="e.g. France" maxLength={100} /></div>}
            </div></div>
          </section>
        </div>
        <div className="col-lg-5 pe-lg-0">
          <section className="panel upload-panel"><div className="panel-heading"><div><div className="eyebrow">02 / LABEL ARTWORK</div><h2>Upload the complete label set</h2><p className="subtle mb-0">Include the back label and a clear warning crop as needed.</p></div></div>
            <div className="panel-body">
              <div className={`drop-zone ${drag ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); addFiles(Array.from(e.dataTransfer.files)); }}>
                <div className="upload-glyph" aria-hidden="true">↑</div><strong>Drop label images here</strong><span>or select them from your computer</span><button type="button" className="btn btn-outline-primary" onClick={() => input.current.click()}>Choose images</button><input ref={input} data-testid="single-files" className="visually-hidden" tabIndex={-1} aria-label="Choose label image files" type="file" accept="image/jpeg,image/png" multiple onChange={e => { addFiles(Array.from(e.target.files)); e.target.value = ''; }} /><small>JPEG or PNG · up to 3 images · 5 MB each</small>
              </div>
              {previews.length > 0 && <div className="previews">{previews.map((p,i) => <div className="preview-card" key={p.url}><a href={p.url} target="_blank" rel="noopener noreferrer" aria-label={`Open image ${i+1}: ${p.name}`}><img src={p.url} alt={`Image ${i+1}: ${p.name}`} /></a><div><strong>Image {i+1}</strong><span title={p.name}>{p.name}</span><small>{(p.size / 1024).toFixed(0)} KB</small></div><button className="remove-file" type="button" aria-label={`Remove ${p.name}`} onClick={() => { setFiles(old => old.filter((_,j) => j !== i)); setResult(null); }}>×</button></div>)}</div>}
              <div className="warning-hint"><strong>Government warning is checked automatically.</strong><p>We compare the wording and punctuation, then screen heading capitalization, boldness and legibility. Printed size still needs a reviewer.</p><details><summary>View required wording</summary><p>{config.warning}</p></details></div>
            </div>
          </section>
        </div>
      </fieldset>
      <div className="submit-bar"><p>No approval decisions. Uploaded images are processed for this review, not saved as application history.</p><button type="submit" className="btn btn-primary btn-verify" disabled={busy || loading || !config.ready || (config.requires_access_code && !token)}>{busy ? <><span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />Verifying… {seconds.toFixed(1)}s</> : 'Verify label'}<span aria-hidden="true"> →</span></button></div>
      {busy && <div className="processing-note" role="status">{seconds < 5 ? 'Reading the images and checking the application values…' : 'This is taking longer than the five-second target. No result has been assumed.'}<button type="button" className="btn btn-link btn-sm" onClick={() => abort.current?.abort()}>Stop</button></div>}
    </form>
    <div ref={resultsRef} className="results-anchor">{result && <Results result={result} />}</div>
  </>;
}
