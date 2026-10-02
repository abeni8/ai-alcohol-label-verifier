# Approach, tools, and assumptions

## From the assignment to the application

| Supplied requirement | Implementation |
| --- | --- |
| Compare application values with artwork | Manual expected-value form; isolated extraction; explicit field-by-field comparison |
| Example distilled-spirits fields | Old Tom Distillery / Kentucky Straight Bourbon Whiskey / 45% / 750 mL sample |
| Similar capitalization should not be a discrepancy | Case folding, whitespace normalization, and curly/straight apostrophe normalization |
| Exact government warning and heading formatting | Separate text, capitals, boldness, body-weight, paragraph, and legibility checks |
| Results in about five seconds | One extraction call per application, asynchronous I/O, measured browser/server timing; live target remains unverified |
| Simple interface | Two clear workflows; numbered input panels; preview images; text plus red/green status |
| Batch importer submissions | CSV manifest validation, filename mapping, two-worker browser queue, progress and export |
| Poor images | Uncertain/missing findings, image preview, EXIF orientation handling; no invented text restoration |
| Restricted network / prototype scope | Fixed server-side provider endpoint; errors when unreachable; no COLA integration or accounts |

No stakeholder anecdotes, staff counts, or legacy-system dates are relied on as externally verified facts. They inform the usability/performance priorities in the supplied brief.

## Architecture

```text
React / Bootstrap
  manual application OR validated CSV row + 1–3 images
        |
        v
FastAPI /api/verify
  access code + origin + upload bounds
  Pydantic application validation
  decode image -> orient -> strip metadata -> JPEG
        |
        v
Extraction adapter (one request per application)
  OpenAI Responses + strict JSON schema, or explicitly labeled sample fixtures
  NO expected application values in the extraction request
        |
        v
Python validation functions
  expected vs observed values + warning-specific checks
        |
        v
Comparison rows, source image numbers, warning diff, timings, CSV
```

FastAPI was selected because the backend is a focused API without accounts, ORM models, or an admin interface. React/Bootstrap align with the applicant's experience. Vite is the usual frontend dev/build tool. `httpx` calls the provider's documented REST API directly, avoiding an extra SDK dependency. Pydantic is used for both application inputs and the returned extraction schema. Pillow validates and prepares images; it does **not** perform OCR.

The live model defaults to `gpt-4.1-mini`, a configurable initial candidate, not a verified optimum. No model training, retrieval/vector database, autonomous agent, or orchestration framework is needed. The model cannot call tools or approve an application. Schema compliance is checked again after the response, but it does not prove that the transcription is correct.

## Field rules

| Check | Rule and deliberate boundary |
| --- | --- |
| Brand, class/type, producer name/address, origin | Unicode NFC, case folding, collapsed whitespace, and equivalent apostrophes. No fuzzy matching, synonym expansion, abbreviation expansion, or inferred address equivalence. |
| ABV | Explicit printed percent; exact Decimal numeric comparison. `45` and `45.0` match. No percentage tolerance. Proof alone is not converted into a missing ABV; proof consistency is not independently certified. |
| Net contents | Unambiguous positive metric quantity in mL, cL, or L, converted with Decimal. `0.75 L` matches `750 mL`. This is volume equivalence, not a standards-of-fill or placement determination. Imperial quantities need review. |
| Government warning | Exact source text, case, and punctuation after whitespace-only normalization. Missing words, punctuation, or unreadable fragments trigger review. A body-case difference is a **conservative screening flag**, not a claim that every capitalization change is legally prohibited. |
| Warning heading | Case-sensitive `GOVERNMENT WARNING:` prefix plus independent visual boldness assessment. |
| Visual presentation | Model reports yes/no/uncertain for bold heading, non-bold body, separate continuous paragraph, and legibility. These are provisional visual findings, not calibrated measurements. |
| Printed size | Always red Review needed. No known scale or container measurements are supplied. |
| Missing/uncertain evidence | Never converted into a match. A populated value without a valid source-image index is treated as uncertain. |

Every result is a screening record, not approval/rejection. A clean sample still has a manual printed-size check. Grey **Not checked** is used for an unprovided optional ABV comparison or an unrequested domestic-origin comparison; it is not an exemption decision.

## Scope assumptions and exclusions

**Input.** Expected values are manually entered or supplied in a UTF-8 CSV; the prototype does not parse application-form PDFs. Producers and addresses use separate fields to make discrepancies explainable. Country of origin is required when `imported=true`. An expected ABV is mandatory for distilled spirits. Wine/beer may omit it, but the result then explicitly says the comparison was not performed.

**Product scope.** The warning screening is designed for beverage alcohol at or above 0.5% ABV. A supplied value below that threshold is flagged out of scope, not automatically passed. Beverage-category nuances, jurisdictional exceptions, appellation rules, class/type legality, font-character-density measurement, standards of fill, and claim substantiation are not implemented. Operator entry is not evidence that a field is legally required or exempt.

**Images.** One to three JPEG/PNG images, 5 MiB and 24 megapixels each. Front, back, and detail crops can be combined; source references identify which image supports each value. EXIF orientation is corrected and transparency flattened. Images larger than 3000 pixels on one edge are downscaled and the result discloses this. Glare, perspective, or blur may still prevent reliable extraction. A warning absent from the supplied images is not necessarily absent from the bottle.

**State.** No database, saved application history, background worker, accounts, or persistent job IDs. Batch state and the access code stay in the active browser tab. Download results before navigating away. Aborting a browser request cannot guarantee cancellation of an already-billed upstream model request.

**Batch.** Maximum 300 CSV rows; image filenames are mapped explicitly, not guessed by order. Two active verification requests in a browser; a server-wide per-process limit controls concurrency. Failures do not stop other rows. No automatic repeated provider calls: the reviewer chooses Retry unfinished.

## Five-second target and trade-offs

There is one network extraction request per application, and all comparisons run in ordinary Python. The browser timer includes request/response transport; server time separately identifies extraction time. The 12-second provider timeout is a failure bound, **not** a claim of meeting the five-second target. Sample-mode timing is explicitly excluded from AI performance conclusions.

Run `scripts/evaluate.py` against the live deployment, then inspect real images and false matches, not only successful response times. The script reports failed requests separately. A small synthetic test set cannot establish production accuracy, nor does the 300-item in-memory queue test establish peak-season service throughput. If performance is inadequate, compare another compatible vision model, adjust image crops/output size, or evaluate a sanctioned local OCR/vision alternative; do not hide missed targets.

## Network and provider dependencies

The browser contacts the app origin only; static assets are bundled rather than CDN-hosted. The backend requires outbound HTTPS to `api.openai.com` in live mode. This design does not bypass government firewall restrictions. An agency-hosted deployment would need an approved reachable endpoint or a separately implemented local provider adapter. The sample adapter is for testing only and is not such a replacement.

## Sources consulted

- TTB, [Health Warning Statement](https://www.ttb.gov/regulated-commodities/beverage-alcohol/distilled-spirits/ds-labeling-home/ds-health-warning), and [27 CFR Part 16](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-16): warning baseline and presentation constraints.
- OpenAI, [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Images and vision](https://developers.openai.com/api/docs/guides/images-vision), and [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini): extraction integration and limitations.
- FastAPI, [Request forms and files](https://fastapi.tiangolo.com/tutorial/request-forms-and-files/): multipart handling.
- Vite, [Getting started](https://vite.dev/guide/): development and build workflow.

These sources inform implementation, not a claim of regulatory certification or externally tested application performance.
