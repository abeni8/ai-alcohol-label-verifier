import React, { useEffect, useState } from './vendor/react.js';
import { createRoot } from './vendor/react-dom.js';
import { api } from './api.mjs';
import Single from './Single.js';
import Batch from './Batch.js';
function App() {
    const [config, setConfig] = useState(null);
    const [error, setError] = useState('');
    const [tab, setTab] = useState('single');
    const [active, setActive] = useState(false);
    const [token, setToken] = useState('');
    useEffect(() => { api('/api/config').then(setConfig).catch(e => setError(e.message)); }, []);
    useEffect(() => {
        if (!active)
            return;
        const guard = event => { event.preventDefault(); event.returnValue = ''; };
        window.addEventListener('beforeunload', guard);
        return () => window.removeEventListener('beforeunload', guard);
    }, [active]);
    return React.createElement(React.Fragment, null,
        React.createElement("a", { className: "skip-link", href: "#main-content" }, "Skip to application"),
        React.createElement("header", { className: "app-header" },
            React.createElement("div", { className: "shell header-inner" },
                React.createElement("div", { className: "brand" },
                    React.createElement("img", { src: "/favicon.svg", alt: "", width: "38", height: "38" }),
                    React.createElement("div", null,
                        React.createElement("span", null, "Label Review"),
                        React.createElement("small", null, "Alcohol label verification"))),
                React.createElement("div", { className: "header-right" },
                    React.createElement("span", { className: `mode-pill ${config?.mode === 'openai' ? 'live' : ''}` },
                        React.createElement("span", { className: "mode-dot" }),
                        config ? config.mode === 'demo' ? 'SAMPLE MODE' : 'LIVE AI MODE' : 'CONNECTING'),
                    React.createElement("span", { className: "prototype-label" }, "Independent prototype")))),
        React.createElement("main", { id: "main-content", className: "shell" },
            React.createElement("div", { className: "page-intro" },
                React.createElement("div", { className: "eyebrow" }, "A CLEARER LABEL REVIEW WORKFLOW"),
                React.createElement("h1", null,
                    "Check the label.",
                    React.createElement("br", { className: "mobile-break" }),
                    " See what needs review."),
                React.createElement("p", null, "Compare application details with label artwork, with the evidence beside every result.")),
            error && React.createElement("div", { className: "alert alert-danger", role: "alert" },
                error,
                React.createElement("button", { className: "btn btn-link", type: "button", onClick: () => window.location.reload() }, "Reload")),
            !config && !error && React.createElement("div", { className: "panel p-4", role: "status" }, "Connecting to the review service\u2026"),
            config && React.createElement(React.Fragment, null,
                config.mode === 'demo' && React.createElement("div", { className: "mode-notice" },
                    React.createElement("span", { className: "notice-symbol", "aria-hidden": "true" }, "i"),
                    React.createElement("div", null,
                        React.createElement("strong", null, "Sample mode: explore the workflow without an API key."),
                        React.createElement("p", null, "Only the bundled, unmodified sample images are recognized by their file hashes. Results use known transcriptions\u2014not AI. Enable live mode on the server to review your own labels."))),
                !config.ready && React.createElement("div", { className: "alert alert-danger", role: "alert" }, "Live AI is not configured. The operator must add an API key on the server before verification is available."),
                config.requires_access_code && React.createElement("div", { className: "access-box" },
                    React.createElement("label", { htmlFor: "access-code", className: "form-label" }, "Review access code"),
                    React.createElement("input", { className: "form-control", id: "access-code", type: "password", autoComplete: "off", value: token, disabled: active, onChange: e => setToken(e.target.value), placeholder: "Enter the code supplied by the operator" }),
                    React.createElement("span", { className: "form-text" }, "Stored only in this tab's memory. Never enter an AI provider key here.")),
                React.createElement("nav", { className: "workspace-tabs", "aria-label": "Review workflows" },
                    React.createElement("button", { type: "button", "aria-current": tab === 'single' ? 'page' : undefined, className: tab === 'single' ? 'active' : '', disabled: active, onClick: () => setTab('single') }, "Individual application"),
                    React.createElement("button", { type: "button", "aria-current": tab === 'batch' ? 'page' : undefined, className: tab === 'batch' ? 'active' : '', disabled: active, onClick: () => setTab('batch') },
                        "Batch review ",
                        React.createElement("span", { className: "tab-count" }, "CSV")),
                    React.createElement("span", { className: "workspace-hint" }, "Human review stays in control")),
                tab === 'single' ? React.createElement(Single, { config: config, token: token, setActive: setActive }) : React.createElement(Batch, { config: config, token: token, setActive: setActive }))),
        React.createElement("footer", { className: "shell app-footer" },
            React.createElement("p", null,
                React.createElement("strong", null, "Review support, not regulatory approval."),
                " This prototype is not an official Treasury or TTB service."),
            React.createElement("details", null,
                React.createElement("summary", null, "Privacy and scope"),
                React.createElement("p", null, "Use synthetic or public label images. Expected application values stay on the review server and are not included in the vision-model request. In live mode, label images are sent to the configured AI provider; provider-side retention policies apply. Uploaded files may pass through temporary multipart buffers but are not saved as application history. Results live only in your browser tab unless you export them."),
                React.createElement("p", null, "The prototype screens products at or above 0.5% ABV. Full category-specific compliance, printed measurements, COLA integration and production authorization are outside scope.")),
            React.createElement("p", { className: "footer-bottom" }, "React + Bootstrap \u00B7 FastAPI \u00B7 Versioned comparison rules")));
}
createRoot(document.getElementById('root')).render(React.createElement(App, null));
