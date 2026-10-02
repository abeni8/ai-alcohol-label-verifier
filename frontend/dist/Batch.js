import React, { useEffect, useRef, useState } from './vendor/react.js';
import { api, checkFiles, sampleFiles, verify } from './api.mjs';
import { downloadText, resultsCsv } from './export.mjs';
import { runQueue } from './queue.mjs';
import Results from './Results.js';
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
        if (problem) {
            setFiles([]);
            setError(problem);
            return;
        }
        setFiles(next);
    }
    async function loadSampleBatch() {
        setPreparing(true);
        invalidate();
        try {
            const catalog = await api('/api/samples');
            const names = [...new Set(catalog.filter(item => ['old-tom', 'wrong-abv', 'warning-typo', 'import'].includes(item.id)).flatMap(item => item.filenames))];
            const response = await fetch('/api/sample-files/batch-sample.csv');
            if (!response.ok)
                throw new Error('The sample CSV could not be loaded.');
            const csvFile = new File([await response.blob()], 'batch-sample.csv', { type: 'text/csv' });
            const imageFiles = await sampleFiles(names);
            setManifest(csvFile);
            setFiles(imageFiles);
            // Keep native file-picker labels consistent with the loaded sample.
            if (typeof DataTransfer !== 'undefined') {
                const csvTransfer = new DataTransfer();
                csvTransfer.items.add(csvFile);
                const imageTransfer = new DataTransfer();
                imageFiles.forEach(file => imageTransfer.items.add(file));
                if (csvInput.current)
                    csvInput.current.files = csvTransfer.files;
                if (imageInput.current)
                    imageInput.current.files = imageTransfer.files;
            }
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setPreparing(false);
        }
    }
    async function validateManifest() {
        setError('');
        setErrors([]);
        setItems([]);
        setSelected(null);
        if (!manifest) {
            setError('Choose a CSV manifest first.');
            return;
        }
        if (manifest.size > 1000000) {
            setError('CSV files must be 1 MB or smaller.');
            return;
        }
        const problem = checkFiles(files, 900);
        if (problem) {
            setError(problem);
            return;
        }
        setPreparing(true);
        try {
            const body = new FormData();
            body.append('manifest', manifest);
            body.append('filenames', JSON.stringify(files.map(f => f.name)));
            const data = await api('/api/batch/validate', { method: 'POST', body, headers: token ? { 'X-Review-Token': token } : {} });
            if (!data.valid) {
                setErrors(data.errors);
                return;
            }
            setUnused(data.unused_files);
            setItems(data.rows.map(row => ({ ...row, state: 'pending', result: null, error: '' })));
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setPreparing(false);
        }
    }
    async function start(retry = false) {
        const indices = items.map((item, i) => ({ item, i })).filter(({ item }) => retry ? ['failed', 'cancelled'].includes(item.state) : item.state === 'pending');
        if (!indices.length)
            return;
        setBusy(true);
        setError('');
        controller.current = new AbortController();
        const byName = new Map(files.map(file => [file.name, file]));
        try {
            await runQueue(indices.map(({ item }) => item), async (item, signal) => {
                const images = item.filenames.map(name => byName.get(name));
                if (images.some(image => !image))
                    throw new Error('A mapped image is no longer available. Validate the manifest again.');
                return verify(item.application, images, token, signal);
            }, (position, update) => {
                const actual = indices[position].i;
                setItems(old => old.map((row, i) => i === actual ? { ...row, ...update } : row));
            }, { concurrency: 2, signal: controller.current.signal });
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setBusy(false);
        }
    }
    const done = items.filter(item => item.state === 'completed').length;
    const failed = items.filter(item => item.state === 'failed').length;
    const cancelled = items.filter(item => item.state === 'cancelled').length;
    const processing = items.filter(item => item.state === 'processing').length;
    const processed = done + failed + cancelled;
    const hasResults = items.some(item => item.result);
    return React.createElement(React.Fragment, null,
        React.createElement("div", { className: "sample-bar" },
            React.createElement("div", null,
                React.createElement("strong", null, "Review a queue, not one file at a time"),
                React.createElement("span", null, "One CSV row per application; up to three images per row.")),
            React.createElement("button", { className: "btn btn-outline-primary", type: "button", disabled: busy || preparing, onClick: loadSampleBatch }, "Load sample batch")),
        error && React.createElement("div", { className: "alert alert-danger", role: "alert" }, error),
        React.createElement("section", { className: "panel batch-setup" },
            React.createElement("div", { className: "panel-heading" },
                React.createElement("div", null,
                    React.createElement("div", { className: "eyebrow" }, "01 / PREPARE THE QUEUE"),
                    React.createElement("h2", null, "Connect application values to images"),
                    React.createElement("p", { className: "subtle mb-0" },
                        "Validation happens before any image analysis. Use exact filenames, separated by ",
                        React.createElement("code", null, "|"),
                        " for multiple images.")),
                React.createElement("a", { className: "btn btn-outline-secondary btn-sm", href: "/api/sample-files/batch-template.csv", download: true }, "CSV template \u2193")),
            React.createElement("fieldset", { disabled: busy || preparing, className: "panel-body border-0" },
                React.createElement("div", { className: "row g-4" },
                    React.createElement("div", { className: "col-md-6" },
                        React.createElement("label", { className: "form-label", htmlFor: "batch-csv" }, "CSV manifest"),
                        React.createElement("input", { className: "form-control", id: "batch-csv", ref: csvInput, type: "file", accept: ".csv,text/csv", onChange: e => { invalidate(); setManifest(e.target.files[0] || null); } }),
                        React.createElement("p", { className: "form-text" }, "UTF-8 CSV \u00B7 up to 300 applications \u00B7 1 MB maximum"),
                        manifest && React.createElement("div", { className: "selected-file" },
                            "\u2713 ",
                            manifest.name)),
                    React.createElement("div", { className: "col-md-6" },
                        React.createElement("label", { className: "form-label", htmlFor: "batch-images" }, "All referenced label images"),
                        React.createElement("input", { className: "form-control", id: "batch-images", ref: imageInput, type: "file", accept: "image/png,image/jpeg", multiple: true, onChange: e => chooseFiles(Array.from(e.target.files)) }),
                        React.createElement("p", { className: "form-text" }, "JPEG / PNG only \u00B7 unique filenames \u00B7 5 MB per image"),
                        files.length > 0 && React.createElement("div", { className: "selected-file" },
                            "\u2713 ",
                            files.length,
                            " images selected"))),
                React.createElement("div", { className: "batch-validate" },
                    React.createElement("button", { className: "btn btn-primary", type: "button", onClick: validateManifest, disabled: !manifest || !files.length || (config.requires_access_code && !token) }, preparing ? 'Checking…' : 'Validate CSV & image mapping'),
                    React.createElement("span", null, "No image-service calls are made during validation.")))),
        errors.length > 0 && React.createElement("section", { className: "panel manifest-errors", role: "alert" },
            React.createElement("h2", null, "Fix the CSV before starting"),
            React.createElement("p", null, "No applications were submitted for verification."),
            React.createElement("div", { className: "table-responsive" },
                React.createElement("table", { className: "table" },
                    React.createElement("thead", null,
                        React.createElement("tr", null,
                            React.createElement("th", null, "CSV line"),
                            React.createElement("th", null, "Problem"))),
                    React.createElement("tbody", null, errors.map((e, i) => React.createElement("tr", { key: i },
                        React.createElement("td", null, e.line),
                        React.createElement("td", null, e.message))))))),
        unused.length > 0 && React.createElement("div", { className: "notice mt-3" },
            unused.length,
            " selected image(s) are not referenced and will not be sent: ",
            unused.join(', ')),
        items.length > 0 && React.createElement("section", { className: "panel batch-queue", "data-testid": "batch-queue" },
            React.createElement("div", { className: "panel-heading" },
                React.createElement("div", null,
                    React.createElement("div", { className: "eyebrow" }, "02 / REVIEW QUEUE"),
                    React.createElement("h2", null, busy ? 'Reviewing your batch' : processed === items.length ? (failed || cancelled ? 'Batch finished — attention needed' : 'Batch review complete') : `${items.length} applications ready`),
                    React.createElement("p", { className: "subtle mb-0" }, "Two applications at a time. Keep this tab open; the queue is not saved.")),
                React.createElement("div", { className: "queue-actions" },
                    busy ? React.createElement("button", { className: "btn btn-outline-danger", type: "button", onClick: () => controller.current.abort() }, "Stop queue") : React.createElement(React.Fragment, null,
                        items.some(item => item.state === 'pending') && React.createElement("button", { className: "btn btn-primary", type: "button", disabled: !config.ready || (config.requires_access_code && !token), onClick: () => start(false) }, "Start batch"),
                        (failed > 0 || cancelled > 0) && React.createElement("button", { className: "btn btn-outline-primary", type: "button", onClick: () => start(true) }, "Retry unfinished")),
                    (processed > 0 || hasResults) && React.createElement("button", { className: "btn btn-outline-secondary", type: "button", onClick: () => downloadText(resultsCsv(items), 'batch-review-results.csv') }, "Export batch CSV"))),
            React.createElement("div", { className: "queue-progress" },
                React.createElement("div", null,
                    React.createElement("strong", null,
                        processed,
                        " / ",
                        items.length,
                        " finished"),
                    React.createElement("span", null,
                        done,
                        " completed \u00B7 ",
                        failed,
                        " failed \u00B7 ",
                        cancelled,
                        " stopped",
                        processing ? ` · ${processing} processing` : '')),
                React.createElement("div", { className: "progress", role: "progressbar", "aria-label": "Batch completion", "aria-valuenow": processed, "aria-valuemin": 0, "aria-valuemax": items.length },
                    React.createElement("div", { className: "progress-bar", style: { width: `${processed / items.length * 100}%` } }))),
            React.createElement("div", { className: "table-responsive" },
                React.createElement("table", { className: "table queue-table" },
                    React.createElement("caption", { className: "visually-hidden" }, "Batch applications and individual verification results"),
                    React.createElement("thead", null,
                        React.createElement("tr", null,
                            React.createElement("th", { scope: "col" }, "Application"),
                            React.createElement("th", { scope: "col" }, "Images"),
                            React.createElement("th", { scope: "col" }, "Progress / result"),
                            React.createElement("th", { scope: "col" }, "Details"))),
                    React.createElement("tbody", null, items.map((item, i) => React.createElement("tr", { key: item.application.application_id, "data-testid": "batch-row" },
                        React.createElement("th", { scope: "row" },
                            item.application.application_id,
                            React.createElement("span", { className: "subtle d-block fw-normal" }, item.application.brand_name)),
                        React.createElement("td", null, item.filenames.map(name => React.createElement("span", { className: "filename-line", key: name }, name))),
                        React.createElement("td", null, item.state === 'completed' ? React.createElement(React.Fragment, null,
                            React.createElement("span", { className: "result-badge review" },
                                "! ",
                                item.result.reviews,
                                " review needed"),
                            React.createElement("span", { className: "subtle d-block mt-1" },
                                item.result.matches,
                                " matches \u00B7 ",
                                (item.result.browser_elapsed_ms / 1000).toFixed(2),
                                "s",
                                item.result.mode === 'demo' ? ' · sample' : '')) : React.createElement(React.Fragment, null,
                            React.createElement("span", { className: `queue-state ${item.state}` },
                                item.state === 'processing' && React.createElement("span", { className: "spinner-border spinner-border-sm me-2", "aria-hidden": "true" }),
                                item.state[0].toUpperCase() + item.state.slice(1)),
                            item.error && React.createElement("p", { className: "reason text-danger" }, item.error))),
                        React.createElement("td", null, item.result && React.createElement("button", { className: "btn btn-outline-primary btn-sm", type: "button", onClick: () => { setSelected(i); setTimeout(() => detailRef.current?.scrollIntoView({ behavior: 'smooth' }), 50); } },
                            "Review findings",
                            React.createElement("span", { className: "visually-hidden" },
                                " for ",
                                item.application.application_id)))))))),
            React.createElement("div", { className: "queue-footer" }, "Stopping cancels browser requests; an AI request already sent may still finish and incur usage. Completed results are retained in this tab.")),
        React.createElement("div", { ref: detailRef, className: "results-anchor" }, selected !== null && items[selected]?.result && React.createElement(Results, { key: items[selected].application.application_id, result: items[selected].result })));
}
