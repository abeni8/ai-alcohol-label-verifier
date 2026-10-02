import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles.css';
import { api } from './api.mjs';
import Single from './Single.jsx';
import Batch from './Batch.jsx';

function App() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('single');
  const [active, setActive] = useState(false);
  const [token, setToken] = useState('');
  useEffect(() => { api('/api/config').then(setConfig).catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (!active) return;
    const guard = event => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, [active]);
  return <>
    <a className="skip-link" href="#main-content">Skip to application</a>
    <header className="app-header"><div className="shell header-inner"><div className="brand"><img src="/favicon.svg" alt="" width="38" height="38" /><div><span>Label Review</span><small>Alcohol label verification</small></div></div><div className="header-right"><span className={`mode-pill ${config?.mode === 'openai' ? 'live' : ''}`}><span className="mode-dot" />{config ? config.mode === 'demo' ? 'SAMPLE MODE' : 'LIVE AI MODE' : 'CONNECTING'}</span><span className="prototype-label">Independent prototype</span></div></div></header>
    <main id="main-content" className="shell">
      <div className="page-intro"><div className="eyebrow">A CLEARER LABEL REVIEW WORKFLOW</div><h1>Check the label.<br className="mobile-break" /> See what needs review.</h1><p>Compare application details with label artwork, with the evidence beside every result.</p></div>
      {error && <div className="alert alert-danger" role="alert">{error}<button className="btn btn-link" type="button" onClick={() => window.location.reload()}>Reload</button></div>}
      {!config && !error && <div className="panel p-4" role="status">Connecting to the review service…</div>}
      {config && <>
        {config.mode === 'demo' && <div className="mode-notice"><span className="notice-symbol" aria-hidden="true">i</span><div><strong>Sample mode: explore the workflow without an API key.</strong><p>Only the bundled, unmodified sample images are recognized by their file hashes. Results use known transcriptions—not AI. Enable live mode on the server to review your own labels.</p></div></div>}
        {!config.ready && <div className="alert alert-danger" role="alert">Live AI is not configured. The operator must add an API key on the server before verification is available.</div>}
        {config.requires_access_code && <div className="access-box"><label htmlFor="access-code" className="form-label">Review access code</label><input className="form-control" id="access-code" type="password" autoComplete="off" value={token} disabled={active} onChange={e => setToken(e.target.value)} placeholder="Enter the code supplied by the operator" /><span className="form-text">Stored only in this tab's memory. Never enter an AI provider key here.</span></div>}
        <nav className="workspace-tabs" aria-label="Review workflows"><button type="button" aria-current={tab === 'single' ? 'page' : undefined} className={tab === 'single' ? 'active' : ''} disabled={active} onClick={() => setTab('single')}>Individual application</button><button type="button" aria-current={tab === 'batch' ? 'page' : undefined} className={tab === 'batch' ? 'active' : ''} disabled={active} onClick={() => setTab('batch')}>Batch review <span className="tab-count">CSV</span></button><span className="workspace-hint">Human review stays in control</span></nav>
        {tab === 'single' ? <Single config={config} token={token} setActive={setActive} /> : <Batch config={config} token={token} setActive={setActive} />}
      </>}
    </main>
    <footer className="shell app-footer"><p><strong>Review support, not regulatory approval.</strong> This prototype is not an official Treasury or TTB service.</p><details><summary>Privacy and scope</summary><p>Use synthetic or public label images. Expected application values stay on the review server and are not included in the vision-model request. In live mode, label images are sent to the configured AI provider; provider-side retention policies apply. Uploaded files may pass through temporary multipart buffers but are not saved as application history. Results live only in your browser tab unless you export them.</p><p>The prototype screens products at or above 0.5% ABV. Full category-specific compliance, printed measurements, COLA integration and production authorization are outside scope.</p></details><p className="footer-bottom">React + Bootstrap · FastAPI · Versioned comparison rules</p></footer>
  </>;
}

createRoot(document.getElementById('root')).render(<App />);
