# Label Review

A standalone alcohol-label comparison prototype: **React + Bootstrap** in the browser, **FastAPI** on the server, vision extraction through the **OpenAI Responses API**, and deterministic Python validation.

An agent enters application values or supplies a CSV, attaches label images, and receives **green Match** or **red Review needed** findings with the expected value, observed text, explanation, and source-image references. This is a review assistant, **not a TTB approval engine**.

## Delivery status

The source, prebuilt frontend, sample fixtures, automated tests, deployment configuration, and documentation are included. **No public deployment or GitHub repository has been created from this workspace.** The API integration has contract tests, but **live AI accuracy and five-second performance have not been measured** because no provider credentials were available. See [the actual test record](docs/TEST_REPORT.md).

The default **sample mode is an explicit simulation**, not OCR or AI. It only accepts the unchanged bundled synthetic images, identified by their full content hashes. Unknown images are rejected. Enable live mode before asking evaluators to upload their own labels.

## Run locally in a few minutes

Use **Python 3.13**. The included frontend build means Node is not needed just to review the app.

```bash
cd label-review
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python scripts/run.py
```

Open **http://127.0.0.1:8000**. Click **Load sample**, then **Verify label**. The sample selector includes an ABV mismatch, missing warning punctuation, title-case heading, front-only evidence, an unreadable back label, and an imported wine.

On Windows, use `py -3.13 -m venv .venv`, `.venv\Scripts\Activate.ps1`, and `Copy-Item .env.example .env`; the remaining Python commands are the same.

### Enable actual image extraction

Edit `.env` locally, or set these on the hosting service:

```dotenv
PROVIDER=openai
OPENAI_API_KEY=your-server-side-key
OPENAI_MODEL=gpt-4.1-mini
REVIEW_ACCESS_TOKEN=a-long-random-review-access-code
```

Restart the server. The UI now says **LIVE AI**. Share the review access code privately with the evaluators—not the OpenAI key. The reviewer supplies the access code in the interface. A missing or rejected AI key produces an explicit error; **live mode never falls back to simulated answers**. Provider calls can incur fees.

## Individual workflow

Enter the example fields from the assignment: brand, class/type, ABV, net contents, producer name/address, and country of origin for imports. Select the beverage category and imported flag. Upload one to three front/back/detail images, **JPEG or PNG, up to 5 MiB and 24 megapixels each**. PDF, HEIC, GIF, animated PNG, and ZIP input are intentionally unsupported.

The result table distinguishes discrepancies, uncertainty, and checks not performed. Capitalization/whitespace normalization and equivalent metric volumes are explained; numeric ABV differences are not tolerated. Warning text is compared separately, with a visible word/punctuation diff. Printed type size always needs human review because images have no physical scale.

## Batch workflow

Open **Batch review**, load the sample batch or download the CSV template, select the referenced images, and click **Validate CSV & image mapping**. Nothing is sent for image analysis until validation succeeds and you click **Start batch**.

The queue supports **up to 300 rows**, two concurrent application requests, progress, per-application findings, cancellation, retry of unfinished rows, and CSV export. The browser tab must remain open; jobs are not stored or resumed after refresh. A 300-row manifest/parser/queue test is **not** a claim that 300 live model calls were load-tested. See [CSV format](docs/CSV_FORMAT.md).

## Tests and evaluation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --test frontend/tests/*.test.mjs
# With the server running and sample mode enabled:
python scripts/evaluate.py --allow-demo --output reports/sample-smoke.json
```

Browser tests: install Chromium with `python -m playwright install chromium`, keep the app running, then run `python scripts/browser_review.py`. The report explains the in-memory rendering bridge used in the restricted development environment and the live-server calls behind it.

For live evaluation, switch the **server** to `PROVIDER=openai`, set any `REVIEW_ACCESS_TOKEN` in your shell, then run:

```bash
python scripts/evaluate.py --runs 3 --output reports/live-evaluation.json
```

This intentionally rejects sample mode unless `--allow-demo` is supplied. It records successful-request median/p95 latency, failures, and selected false matches on controlled examples. Add real, legally shareable images before making general accuracy claims.

## Edit the frontend

Use **Node 22.12+** and the normal Vite workflow:

```bash
cd frontend
npm install
npm run dev
# After changes:
npm run build
```

Keep FastAPI running separately. Vite proxies `/api` to port 8000. Vite is the development server/build tool, not another application framework. For the single-service deployment, the rebuilt `frontend/dist` is served by FastAPI.

Network access to npm was unavailable during development, so the provided build was produced from the same JSX using `scripts/build_offline.cjs` and bundled MIT-licensed React/Bootstrap assets. **The npm/Vite installation path has not been executed here.** A CI workflow is included to test the normal Vite build after import. Generate and commit `package-lock.json` on that first connected install, then change CI to `npm ci`.

## Repository guide

- `backend/app/`: input schemas, image handling, extraction adapter, comparison rules, and API routes.
- `frontend/src/`: individual form, results table, batch queue, exports, and responsive styling.
- `samples/`: controlled fictional labels, matching CSVs, and explicitly simulated extraction fixtures.
- `backend/tests/`, `frontend/tests/`, `scripts/browser_review.py`: reproducible tests.
- `docs/`: [approach and assumptions](docs/APPROACH.md), [security](docs/SECURITY.md), [test report](docs/TEST_REPORT.md), [deployment](docs/DEPLOYMENT.md), [submission checklist](docs/SUBMISSION_CHECKLIST.md).
- `Dockerfile`, `compose.yaml`, `render.yaml`, `.github/workflows/test.yml`: deployment and CI configuration; no account credentials.

## Deploy and submit

Follow [DEPLOYMENT.md](docs/DEPLOYMENT.md) to import the source into GitHub, configure Render, and validate the live URL. `render.yaml` selects **paid compute**; inspect the current cost before applying. The files do not activate or purchase hosting by themselves.

Do not submit a sample-only URL as a working arbitrary-image AI verifier. Complete the live-image and performance checks, then provide the real repository URL and deployed application URL to Treasury.

### Regulatory source

Warning wording/format references: [TTB health warning guidance](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-health-warning) and [27 CFR Part 16](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16). Field comparison is deliberately narrower than legal label approval. The [approach document](docs/APPROACH.md) separates the supplied assignment requirements from implementation assumptions.
