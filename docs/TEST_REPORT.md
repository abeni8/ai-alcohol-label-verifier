# Executed test report

## Result summary

| Suite | Executed result | What this establishes |
| --- | --- | --- |
| Initial single-application backend suite, before batch implementation | **92 passed** | Initial validation, upload handling, sample-mode behavior, and API safeguards |
| Final backend suite | **142 passed** | Deterministic comparisons, images, API errors/access controls, CSV validation, and mocked live-provider contract |
| Frontend JavaScript unit suite | **28 passed** | File validation, export escaping, bounded queue, cancellation, isolated failure, and 300-item scheduling |
| Browser acceptance | **19 checks passed; zero uncaught JavaScript errors** | Actual React UI interacting with the running local FastAPI service through the bridge described below |
| Controlled sample HTTP evaluation | **7 of 7 scenarios passed** | Full local upload-to-results workflow using known fixture transcriptions, NOT image-recognition accuracy |

Raw evidence: `evidence/initial-backend-tests.txt`, `backend-tests.txt`, `frontend-tests.txt`, `browser-tests.json`, `browser-tests.txt`, and `sample-evaluation.json`.

The final server was launched using the supplied `python scripts/run.py` entry point. Screenshots show the individual form/results, completed four-application batch, and 390-pixel mobile view.

## What was tested

**Comparison logic:** capitalization, apostrophes, whitespace, exact Decimal ABV, metric volume equivalence, inconsistent/ambiguous evidence, missing fields, uncertain extraction, exact warning wording/punctuation, title-case heading, visual flags, mandatory human printed-size review, and unsupported low-ABV scope.

**Uploads and API:** empty/corrupt/oversize files, content-type and real-format mismatches, duplicate images, path-like filenames, front/back evidence, metadata stripping, EXIF rotation, transparent images, downscaling, pixel limits, animated PNG, chunked request limits, access-code enforcement, external-origin rejection, per-minute limit, hidden fixture metadata, and no live-to-demo fallback.

**Provider contract:** the documented Responses payload, strict extraction schema, one request containing multiple images, no expected application data, `store:false`, valid source references, and rejection of incomplete/malformed/refused responses. Network timeouts, quota/rate failures, invalid credentials, and provider errors were simulated with an HTTP mock—not sent to the live provider.

**Batch and UI:** all-or-nothing CSV validation, exact filename mapping, quoted addresses, UTF-8/BOM, missing files, duplicate identifiers/headers, invalid flags, 300-row acceptance/301-row rejection, green/red findings, stale-result invalidation, review filtering, warning diffs, result export, mixed-success queue, stop/retry, and small-screen layout. Four batch requests actually reached the local backend. The 300-task check exercised in-memory scheduling, not 300 real inference calls.

## Browser method and build provenance

This environment's Chromium policy blocks URL navigation, including localhost. The test did not disable that policy. It rendered the **same React source** in memory and used an explicit Python localhost HTTP bridge for browser `fetch` requests. Multipart uploads were sent to the real running FastAPI API. That API used the explicitly labeled sample adapter. Only the resilience cases explicitly marked "simulated" injected failure/delay responses.

The browser report states `live_ai_tested:false` and `public_deployment_tested:false`. The normal browser-test path is also supplied for a connected machine/CI: it navigates to the served URL and uses standard HTTP. That normal-navigation path was not executable in this restricted browser environment.

The included static build was generated from `frontend/src` using TypeScript 5.8.3 and bundled React 19.1.1 / Bootstrap 5.3.6 assets. The normal Vite dependency installation/build was **not executed** because npm access was unavailable. `scripts/build_offline.cjs` and `scripts/build_browser_harness.cjs` preserve the source used for tests; third-party licenses are included. An automated static-asset check verifies that the served entry point's local imports/files resolve.

## Explicitly not verified

- Real vision extraction of new images, OCR accuracy, hallucination/false-pass rates on actual labels.
- Five-second live median/p95 performance, cold starts, provider throttling behavior, or 200–300 live-application throughput.
- Actual GitHub CI execution, Docker build, Render provisioning, HTTPS domain, or public evaluator access.
- Fresh dependency installation from registries, a complete transitive dependency lock, or a current vulnerability audit.
- Regulatory completeness, physical typography measurement, formal accessibility certification, security accreditation, or production readiness.

Do not reinterpret the short fixture timings as live AI latency, or the 7/7 fixture result as model accuracy. The live adapter, benchmark script, and deployment configuration are ready to exercise once credentials/network/hosting are supplied.

## Reproduce

```bash
python -m pytest -q
node --test frontend/tests/*.test.mjs
python scripts/run.py
# Separate terminal:
python scripts/evaluate.py --allow-demo --output reports/sample-smoke.json
python -m playwright install chromium
python scripts/browser_review.py
```

Restricted-environment reproduction additionally needs TypeScript 5.8+ resolvable by Node or `TYPESCRIPT_PATH`, then `node scripts/build_browser_harness.cjs` and `python scripts/browser_review.py --bridge --browser /path/to/chromium`. Ordinary users should use the standard browser path instead.
