import React, { useEffect, useRef, useState } from './vendor/react.js';
import { api, checkFiles, sampleFiles, verify } from './api.mjs';
import Results from './Results.js';
const EMPTY = { application_id: '', beverage_type: 'distilled_spirits', imported: false, brand_name: '', class_type: '', abv: '', net_contents: '', producer_name: '', producer_address: '', country_of_origin: '' };
function TextField({ id, label, value, onChange, placeholder, required = true, type = 'text', maxLength = 250, help }) {
    return React.createElement("div", null,
        React.createElement("label", { className: "form-label", htmlFor: id },
            label,
            !required && React.createElement("span", { className: "optional" }, " optional")),
        React.createElement("input", { className: "form-control", id: id, name: id, value: value, onChange: e => onChange(e.target.value), placeholder: placeholder, required: required, maxLength: maxLength, type: type, ...(type === 'number' ? { min: 0, max: 100, step: 'any' } : {}) }),
        help && React.createElement("div", { className: "form-text" }, help));
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
    useEffect(() => { let current = true; api('/api/samples').then(data => { if (current)
        setCatalog(data); }).catch(e => { if (current)
        setError(e.message); }); return () => { current = false; }; }, []);
    useEffect(() => {
        const next = files.map(file => ({ name: file.name, url: URL.createObjectURL(file), size: file.size }));
        setPreviews(next);
        return () => next.forEach(p => URL.revokeObjectURL(p.url));
    }, [files]);
    useEffect(() => {
        setActive(busy || loading);
        if (!busy)
            return;
        const start = performance.now();
        const timer = setInterval(() => setSeconds((performance.now() - start) / 1000), 100);
        return () => clearInterval(timer);
    }, [busy, loading, setActive]);
    useEffect(() => () => abort.current?.abort(), []);
    function field(name, value) { setForm(old => ({ ...old, [name]: value })); setResult(null); setError(''); }
    function addFiles(selected) {
        if (busy || loading)
            return;
        const error = checkFiles(selected);
        if (error) {
            setFiles([]);
            setResult(null);
            setError(error);
            return;
        }
        setFiles(selected);
        setResult(null);
        setError('');
    }
    async function loadSample() {
        const item = catalog.find(x => x.id === sample);
        if (!item)
            return;
        setLoading(true);
        setError('');
        setResult(null);
        try {
            const images = await sampleFiles(item.filenames);
            setForm({ ...item.application });
            setFiles(images);
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setLoading(false);
        }
    }
    async function submit(event) {
        event.preventDefault();
        const problem = checkFiles(files);
        if (problem) {
            setError(problem);
            return;
        }
        setBusy(true);
        setSeconds(0);
        setError('');
        setResult(null);
        abort.current = new AbortController();
        try {
            const data = await verify({ ...form, application_id: form.application_id.trim() || 'Individual application' }, files, token, abort.current.signal);
            setResult(data);
            setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
        }
        catch (e) {
            setError(e.name === 'AbortError' ? 'Verification stopped. No result was accepted.' : e.message);
        }
        finally {
            setBusy(false);
        }
    }
    return React.createElement(React.Fragment, null,
        React.createElement("div", { className: "sample-bar" },
            React.createElement("div", null,
                React.createElement("strong", null, "Try a controlled example"),
                React.createElement("span", null, "Known text, deliberate errors, and front/back labels.")),
            React.createElement("div", { className: "sample-controls" },
                React.createElement("label", { className: "visually-hidden", htmlFor: "sample-choice" }, "Sample scenario"),
                React.createElement("select", { id: "sample-choice", className: "form-select", value: sample, disabled: busy || loading, onChange: e => setSample(e.target.value) }, catalog.map(item => React.createElement("option", { key: item.id, value: item.id }, item.title))),
                React.createElement("button", { type: "button", className: "btn btn-outline-primary", disabled: busy || loading || !catalog.length, onClick: loadSample }, loading ? 'Loading…' : 'Load sample'))),
        error && React.createElement("div", { className: "alert alert-danger error-box", role: "alert" },
            React.createElement("strong", null, "Action needed. "),
            error),
        React.createElement("form", { onSubmit: submit },
            React.createElement("fieldset", { disabled: busy || loading, className: "row g-4 border-0 p-0 m-0" },
                React.createElement("div", { className: "col-lg-7 ps-lg-0" },
                    React.createElement("section", { className: "panel application-panel" },
                        React.createElement("div", { className: "panel-heading" },
                            React.createElement("div", null,
                                React.createElement("div", { className: "eyebrow" }, "01 / APPLICATION DETAILS"),
                                React.createElement("h2", null, "What should the label say?"),
                                React.createElement("p", { className: "subtle mb-0" }, "Enter the expected values from the application."))),
                        React.createElement("div", { className: "panel-body" },
                            React.createElement("div", { className: "row g-3" },
                                React.createElement("div", { className: "col-sm-6" },
                                    React.createElement(TextField, { id: "application_id", label: "Application ID", value: form.application_id, onChange: v => field('application_id', v), placeholder: "e.g. OLD-TOM-001", maxLength: 100, required: false })),
                                React.createElement("div", { className: "col-sm-6" },
                                    React.createElement("label", { htmlFor: "beverage_type", className: "form-label" }, "Beverage type"),
                                    React.createElement("select", { id: "beverage_type", className: "form-select", value: form.beverage_type, onChange: e => field('beverage_type', e.target.value) },
                                        React.createElement("option", { value: "distilled_spirits" }, "Distilled spirits"),
                                        React.createElement("option", { value: "wine" }, "Wine"),
                                        React.createElement("option", { value: "malt_beverage" }, "Malt beverage / beer"))),
                                React.createElement("div", { className: "col-12" },
                                    React.createElement(TextField, { id: "brand_name", label: "Brand name", value: form.brand_name, onChange: v => field('brand_name', v), placeholder: "OLD TOM DISTILLERY", maxLength: 200 })),
                                React.createElement("div", { className: "col-12" },
                                    React.createElement(TextField, { id: "class_type", label: "Class / type designation", value: form.class_type, onChange: v => field('class_type', v), placeholder: "Kentucky Straight Bourbon Whiskey" })),
                                React.createElement("div", { className: "col-sm-6" },
                                    React.createElement(TextField, { id: "abv", label: "Alcohol by volume (%)", value: form.abv, onChange: v => field('abv', v), placeholder: "45", type: "number", required: form.beverage_type === 'distilled_spirits', help: "Enter 45 for 45% Alc./Vol. (90 Proof)." })),
                                React.createElement("div", { className: "col-sm-6" },
                                    React.createElement(TextField, { id: "net_contents", label: "Net contents", value: form.net_contents, onChange: v => field('net_contents', v), placeholder: "750 mL", maxLength: 60 })),
                                React.createElement("div", { className: "col-12" },
                                    React.createElement(TextField, { id: "producer_name", label: "Bottler / producer name", value: form.producer_name, onChange: v => field('producer_name', v), placeholder: "Old Tom Distillery" })),
                                React.createElement("div", { className: "col-12" },
                                    React.createElement(TextField, { id: "producer_address", label: "Bottler / producer address", value: form.producer_address, onChange: v => field('producer_address', v), placeholder: "Street, city, state / region, postal code", maxLength: 400 })),
                                React.createElement("div", { className: "col-12" },
                                    React.createElement("div", { className: "import-row" },
                                        React.createElement("label", { className: "form-check form-switch" },
                                            React.createElement("input", { id: "imported", className: "form-check-input", type: "checkbox", checked: form.imported, onChange: e => { field('imported', e.target.checked); if (!e.target.checked)
                                                    field('country_of_origin', ''); } }),
                                            React.createElement("span", { className: "form-check-label" }, "Imported product")),
                                        React.createElement("span", { className: "subtle" }, "Enable country-of-origin comparison"))),
                                form.imported && React.createElement("div", { className: "col-12" },
                                    React.createElement(TextField, { id: "country_of_origin", label: "Country of origin", value: form.country_of_origin, onChange: v => field('country_of_origin', v), placeholder: "e.g. France", maxLength: 100 })))))),
                React.createElement("div", { className: "col-lg-5 pe-lg-0" },
                    React.createElement("section", { className: "panel upload-panel" },
                        React.createElement("div", { className: "panel-heading" },
                            React.createElement("div", null,
                                React.createElement("div", { className: "eyebrow" }, "02 / LABEL ARTWORK"),
                                React.createElement("h2", null, "Upload the complete label set"),
                                React.createElement("p", { className: "subtle mb-0" }, "Include the back label and a clear warning crop as needed."))),
                        React.createElement("div", { className: "panel-body" },
                            React.createElement("div", { className: `drop-zone ${drag ? 'dragging' : ''}`, onDragOver: e => { e.preventDefault(); setDrag(true); }, onDragLeave: () => setDrag(false), onDrop: e => { e.preventDefault(); setDrag(false); addFiles(Array.from(e.dataTransfer.files)); } },
                                React.createElement("div", { className: "upload-glyph", "aria-hidden": "true" }, "\u2191"),
                                React.createElement("strong", null, "Drop label images here"),
                                React.createElement("span", null, "or select them from your computer"),
                                React.createElement("button", { type: "button", className: "btn btn-outline-primary", onClick: () => input.current.click() }, "Choose images"),
                                React.createElement("input", { ref: input, "data-testid": "single-files", className: "visually-hidden", tabIndex: -1, "aria-label": "Choose label image files", type: "file", accept: "image/jpeg,image/png", multiple: true, onChange: e => { addFiles(Array.from(e.target.files)); e.target.value = ''; } }),
                                React.createElement("small", null, "JPEG or PNG \u00B7 up to 3 images \u00B7 5 MB each")),
                            previews.length > 0 && React.createElement("div", { className: "previews" }, previews.map((p, i) => React.createElement("div", { className: "preview-card", key: p.url },
                                React.createElement("a", { href: p.url, target: "_blank", rel: "noopener noreferrer", "aria-label": `Open image ${i + 1}: ${p.name}` },
                                    React.createElement("img", { src: p.url, alt: `Image ${i + 1}: ${p.name}` })),
                                React.createElement("div", null,
                                    React.createElement("strong", null,
                                        "Image ",
                                        i + 1),
                                    React.createElement("span", { title: p.name }, p.name),
                                    React.createElement("small", null,
                                        (p.size / 1024).toFixed(0),
                                        " KB")),
                                React.createElement("button", { className: "remove-file", type: "button", "aria-label": `Remove ${p.name}`, onClick: () => { setFiles(old => old.filter((_, j) => j !== i)); setResult(null); } }, "\u00D7")))),
                            React.createElement("div", { className: "warning-hint" },
                                React.createElement("strong", null, "Government warning is checked automatically."),
                                React.createElement("p", null, "We compare the wording and punctuation, then screen heading capitalization, boldness and legibility. Printed size still needs a reviewer."),
                                React.createElement("details", null,
                                    React.createElement("summary", null, "View required wording"),
                                    React.createElement("p", null, config.warning))))))),
            React.createElement("div", { className: "submit-bar" },
                React.createElement("p", null, "No approval decisions. Uploaded images are processed for this review, not saved as application history."),
                React.createElement("button", { type: "submit", className: "btn btn-primary btn-verify", disabled: busy || loading || !config.ready || (config.requires_access_code && !token) },
                    busy ? React.createElement(React.Fragment, null,
                        React.createElement("span", { className: "spinner-border spinner-border-sm me-2", "aria-hidden": "true" }),
                        "Verifying\u2026 ",
                        seconds.toFixed(1),
                        "s") : 'Verify label',
                    React.createElement("span", { "aria-hidden": "true" }, " \u2192"))),
            busy && React.createElement("div", { className: "processing-note", role: "status" },
                seconds < 5 ? 'Reading the images and checking the application values…' : 'This is taking longer than the five-second target. No result has been assumed.',
                React.createElement("button", { type: "button", className: "btn btn-link btn-sm", onClick: () => abort.current?.abort() }, "Stop"))),
        React.createElement("div", { ref: resultsRef, className: "results-anchor" }, result && React.createElement(Results, { result: result })));
}
