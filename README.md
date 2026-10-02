# AI-Powered Alcohol Label Verifier

A standalone prototype that compares alcohol label images with application data and flags discrepancies for human review. The application combines AI-based image extraction with deterministic validation, displaying the expected value, observed text, explanation, and source-image references for each check.

This is a review assistant, not an automated regulatory approval system.

## Application access

**Live application:** DEPLOYED_APPLICATION_URL  
**Source code:** [GitHub repository](https://github.com/abeni8/ai-alcohol-label-verifier)

The hosted application runs in the browser without a local installation. If access protection is enabled, enter the separately provided review access code. The AI provider key is configured on the server and is never entered in the browser.

The interface identifies the active processing mode:

- **LIVE AI:** analyzes uploaded JPEG/PNG label images through the configured AI provider.
- **SAMPLE MODE:** uses fixed transcriptions for the unmodified bundled sample images. It performs no image recognition and rejects unfamiliar images.

## Features

- **Individual review:** manual entry of application values with up to three front, back, or detail label images.
- **Field comparisons:** brand, class/type, alcohol content, net contents, producer name/address, and country of origin for imports.
- **Warning checks:** wording, punctuation, heading capitalization, and provisional visual checks for boldness, paragraph separation, and legibility. A text difference view highlights warning discrepancies.
- **Clear results:** green **Match**, red **Review needed**, and gray **Not checked**, with explanations rather than color alone. Normalized matches are explicitly identified.
- **Batch review:** CSV-to-image mapping, up to 300 application rows, two concurrent application requests, progress tracking, cancellation, retry of unfinished rows, and CSV export.

![Individual review results in sample mode](evidence/02-individual-results.png)

## Using the application

### Individual review

Enter the beverage category, import status, and expected label fields. For example, the bundled distilled-spirits sample uses **OLD TOM DISTILLERY**, **Kentucky Straight Bourbon Whiskey**, **45% ABV**, and **750 mL**. Enter the producer details and country of origin where applicable.

Attach one to three JPEG or PNG images, then select **Verify label**. Review the comparison rows and source images. **Load sample** provides controlled examples including an ABV mismatch, warning punctuation error, title-case heading, incomplete image evidence, and an imported product.

Images are limited to **5 MiB and 24 megapixels each**. PDF, HEIC, GIF, animated PNG, and ZIP uploads are not supported. Printed type size always requires manual review, so even a label with matching text can have a red finding.

### Batch review

Open **Batch review**, load the sample batch or download the CSV template, and select the referenced images. Select **Validate CSV & image mapping**, then **Start batch**. Image analysis begins only after validation and an explicit start.

Each CSV row represents one application and names its associated images. Results appear as individual applications finish and can be exported to CSV. The browser tab must remain open; batch state does not survive a refresh. See [CSV format and examples](docs/CSV_FORMAT.md).

## Approach

**AI reads the label; Python checks the rules.** Extraction and comparison are separate so that matching logic remains transparent and independently testable.

1. **Validate inputs.** FastAPI accepts application data and images. Pydantic validates the data, while Pillow checks image limits and prepares images for extraction.
2. **Extract visible evidence.** One OpenAI Responses API request per application returns structured field observations, uncertainty flags, and source-image numbers. Expected application values are not sent to the extraction model. The model is instructed to transcribe visible text, not reconstruct missing text or follow instructions embedded in images.
3. **Compare deterministically.** Python functions compare the extracted values with the application and run the warning-specific checks. Missing, ambiguous, or unsupported evidence is not accepted as a match.
4. **Present findings.** React displays comparison rows, a warning-text diff, image references, and timing information. Results support a human decision rather than issuing an approval or rejection.

FastAPI keeps the backend focused on validation and API requests without adding a database, administrative interface, or account system. The frontend and API can be served together as a single service. No model training, vector database, autonomous agents, or orchestration framework is used.

## Tools used

| Tool | Role |
| --- | --- |
| Python 3.13, FastAPI, Uvicorn | Backend API, request handling, and application server |
| React, Bootstrap | Forms, image previews, comparison tables, and responsive styling |
| Vite | Frontend development server and build tooling |
| OpenAI Responses API | Structured image extraction; the default model is `gpt-4.1-mini`, configurable through the environment |
| Pydantic, pydantic-settings | Input and extraction-schema validation; environment configuration |
| HTTPX | Asynchronous server-side requests to the AI provider |
| Pillow | Image decoding, orientation correction, and preparation; not OCR |
| pytest, Node test runner, Playwright | Backend, frontend logic, and browser workflow tests |
| GitHub Actions, Render configuration, Docker | CI and deployment configuration |

## Comparison rules

| Check | Implemented behavior |
| --- | --- |
| Brand, class/type, producer, and origin | Normalize capitalization, whitespace, Unicode composition, and equivalent apostrophes. No fuzzy matching or inferred synonym/address equivalence. |
| Alcohol content | Compare an explicitly printed percentage numerically: `45` and `45.0` match. No percentage tolerance; proof alone is not converted into a missing ABV. |
| Net contents | Compare metric volume in mL, cL, or L: `0.75 L` and `750 mL` match. This does not certify the printed format or standards of fill. |
| Warning text | Compare wording, case, and punctuation against the configured reference after whitespace-only normalization. Body-case differences are conservative screening flags, not legal determinations. |
| Warning presentation | Check the case-sensitive `GOVERNMENT WARNING:` prefix and obtain provisional visual findings for bold heading, non-bold body, paragraph separation, and legibility. |
| Printed type size | Always **Review needed** because the images do not supply a reliable physical scale. |
| Optional comparisons | Display **Not checked** when an optional expected ABV is omitted or domestic origin is not requested. This is not an exemption decision. |

## Assumptions and limitations

**Scope.** Application values are entered manually or supplied in a CSV; application-form PDFs and COLA integration are outside scope. The form covers distilled spirits, wine, and malt beverages. Country of origin is required for imported products. Expected ABV is required for distilled spirits and optional for wine/malt-beverage comparisons. The warning workflow is scoped to beverage alcohol at or above 0.5% ABV; a supplied lower value is flagged for review.

**Evidence.** Missing text means it was not found in the supplied images, not necessarily that it is absent from the container. Glare, blur, small text, and angled photographs can prevent reliable extraction. Valid structured output does not guarantee an accurate transcription. Visual formatting findings require judgment and do not establish physical type size.

**Regulatory coverage.** The prototype does not determine all category-specific exceptions, class/type legality, appellation rules, standards of fill, character density, or claim substantiation. A matching field is not a finding of complete regulatory compliance.

**Performance.** About five seconds per application is a design target, not a demonstrated guarantee. Browser and server timings are exposed, and the evaluation script records latency and failures. The default 12-second provider timeout is a failure limit, not evidence of meeting the target. Sample-mode results do not measure live AI accuracy or latency; a 300-row queue test does not establish 300-application live throughput.

**State and access.** There is no database, saved application history, durable background queue, or user-account system. Batch state and the optional access code remain in the active tab. Canceling a browser request cannot guarantee cancellation of an upstream model request already in progress.

**Network and data.** Live extraction requires outbound HTTPS from the backend to the AI provider. The browser communicates with the application origin, and frontend assets are bundled. No persistent application/image store is implemented; live images are transmitted to the provider, whose own retention policies also apply. Use synthetic or otherwise shareable labels. This prototype is not a production security authorization.

Additional design details are in [Approach and assumptions](docs/APPROACH.md) and [Security](docs/SECURITY.md).

## Local setup and run instructions

Use **Python 3.13**. The included frontend build means Node is not required to run the application locally.

```bash
git clone https://github.com/abeni8/ai-alcohol-label-verifier.git label-review
cd label-review
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python scripts/run.py
```

For an existing checkout, start from its root directory and skip the clone command. Use the explicit Python version when creating the virtual environment; an older system interpreter can cause runtime errors.

Open **http://127.0.0.1:8000**. The default configuration uses sample mode and requires no API key. Select **Load sample**, then **Verify label**.

On Windows, use `py -3.13 -m venv .venv`, `.venv\Scripts\Activate.ps1`, and `Copy-Item .env.example .env`; the remaining Python commands are unchanged.

### Live AI configuration

Set the following in the local `.env` file or hosting environment, then restart the server:

```dotenv
PROVIDER=openai
OPENAI_API_KEY=your-server-side-key
OPENAI_MODEL=gpt-4.1-mini
REVIEW_ACCESS_TOKEN=your-separate-review-access-code
```

`REVIEW_ACCESS_TOKEN` is optional locally. When configured, its value is entered in the application's access-code field. It is separate from the OpenAI key. Never commit `.env` or credentials.

The interface displays **LIVE AI** when that provider is selected. Missing credentials, unavailable services, timeouts, and invalid responses produce explicit errors; live mode never falls back to sample answers. Live requests may incur provider usage charges. Remaining settings and defaults are documented in [.env.example](.env.example).

### Frontend development

Use **Node 22.12+**. With FastAPI running in a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to port 8000. After frontend changes, run `npm run build` in `frontend/`; the single-service application serves the generated `frontend/dist` directory.

The included frontend was built from the JSX source using the repository's offline build path and bundled React/Bootstrap assets. The standard Vite path and its validation status are documented in [the test report](docs/TEST_REPORT.md).

## Testing and evaluation

From the repository root, with the virtual environment active:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --test frontend/tests/*.test.mjs
```

With the server running in sample mode:

```bash
python scripts/evaluate.py --allow-demo --output reports/sample-smoke.json
```

Browser workflow tests also require Chromium:

```bash
python -m playwright install chromium
python scripts/browser_review.py
```

For live evaluation, run the server with `PROVIDER=openai`. If access protection is enabled, set `REVIEW_ACCESS_TOKEN` in the evaluator's shell, then run:

```bash
python scripts/evaluate.py --runs 3 --output reports/live-evaluation.json
```

The evaluator rejects sample mode unless `--allow-demo` is explicit. Reports include successful-request median/p95 latency, request failures, and selected false matches on controlled examples. A deployed endpoint can be selected with the script's `--url` option.

The checked-in [test report](docs/TEST_REPORT.md) records backend, frontend, browser, and controlled-sample results, including mocked provider calls and the browser bridge used in the development environment. Those results do not establish live-image accuracy or five-second performance.

## Deployment

The repository includes a single-service Render configuration and a Docker alternative. FastAPI serves both the API and the compiled frontend.

- **Build:** `pip install -r requirements.txt`
- **Start:** `python scripts/run.py --host 0.0.0.0` (reads the hosting platform's `PORT`)
- **Readiness endpoint:** `/api/ready`
- **Runtime configuration:** `PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and an optional `REVIEW_ACCESS_TOKEN`

The supplied `render.yaml` selects live mode and paid compute. `/api/ready` checks configuration presence; it does not validate provider quota, credentials, or successful inference. Deployment details and troubleshooting are in [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Repository structure

```text
backend/app/       API routes, schemas, image handling, extraction, and validation
backend/tests/     Backend and mocked-provider tests
frontend/src/      React forms, results, batch queue, exports, and styling
frontend/dist/     Included frontend build
frontend/tests/    Frontend logic tests
samples/           Synthetic labels, CSV examples, and sample-mode fixtures
scripts/           Run, build, browser-test, and evaluation utilities
docs/              Approach, CSV format, security, testing, and deployment notes
evidence/          Recorded test outputs and sample-mode screenshots
```

## References and licensing

Warning-reference sources used by the implementation: [TTB health warning guidance](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-health-warning) and [27 CFR Part 16](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16). Further technical references are listed in [APPROACH.md](docs/APPROACH.md).

See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
