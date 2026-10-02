# Security and data handling

This is a small public-demo design, not a production federal authorization package.

## Implemented controls

- The AI key is a server environment secret, never a React variable or browser credential. `.env` is excluded from Git and Docker build context. Public config exposes mode/readiness, not keys.
- An optional shared `REVIEW_ACCESS_TOKEN` protects both verification and CSV validation. Render configuration generates one by default. The frontend holds it only in memory, not local storage. This is a demo access gate, not identity management.
- POST request bodies are bounded at 16 MiB before multipart parsing, including requests without Content-Length. Each image is separately limited to 5 MiB/24 megapixels; file extension, MIME type, and decoded format must agree. Paths and animations are rejected. Server concurrency is bounded.
- Uploaded images are decoded, orientation-corrected, flattened, and re-encoded without source metadata. User-controlled URLs are never fetched. The upstream endpoint is fixed in code and not a user input.
- Extraction prompts treat label text as untrusted data. Expected application values are withheld from the model. There are no model tools/actions. Schema and source indices are checked, and uncertainty is not a pass. Prompt injection and hallucination remain risks; a system prompt is not a formal security boundary.
- React renders user/model text as text, not injected HTML. CSV fields are quoted and formula-like prefixes escaped. Content Security Policy, frame protection, no-sniff, and API no-store headers are applied to ordinary application responses. The same-origin POST check provides defense in depth; the shared code is the access control.
- A per-process rolling limit bounds verification starts, and a semaphore bounds active extraction. There is no silent retry loop or sample fallback after a live failure. Errors avoid echoing keys and uploaded documents.

## Retention boundaries

The app has no persistent upload/result database and does not deliberately log request bodies or full extractions. Multipart parsing may spool uploads to temporary files; upload handles are closed at the end of requests. This is **not** a guarantee of forensic secure erasure. Hosting access logs and backups have their own policies. Browser results last until the tab is cleared; exports are deliberately saved by the reviewer.

Live images are sent to the configured AI provider. The request uses `store: false`, but this does **not** by itself establish zero data retention: provider abuse-monitoring and account controls are separate. See OpenAI's [data controls documentation](https://developers.openai.com/api/docs/guides/your-data). Use synthetic/public samples until the intended data use and retention are approved.

## Remaining production work

A production deployment would need agency-approved identity/access management, authorization boundaries, threat review, model/vendor approval, encryption and retention policies, approved audit records, dependency scanning/locking, distributed rate limiting, edge body/connection limits, load testing, monitoring, incident response, and an authorization process. No FedRAMP/ATO, legal-compliance, or adversarial-robustness claim is made.

In-memory limits apply to **one server process**. Do not add multiple workers or replicas and assume those limits remain global. Client disconnects can leave already-issued provider work running until its timeout; usage may still be charged. A process restart loses queues and counters. The public access code should be enabled, changed after the review period, and shared outside the repository.

Before public deployment, run current dependency audits in a connected environment, verify HTTPS, set a provider usage budget, and restrict access to the evaluation audience. No vulnerability scan or third-party penetration test was performed in this build environment.
