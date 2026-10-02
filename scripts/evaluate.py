"""Evaluate controlled label scenarios through an HTTP deployment.

Uses real AI when PROVIDER=openai on the server. Sample mode is refused unless
--allow-demo is supplied, and is never presented as an AI accuracy/latency result.
These synthetic smoke checks are NOT a representative real-world accuracy study.
"""
import argparse
import json
import math
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "old-tom": {"brand_name": "match", "abv": "match", "net_contents": "match", "warning_text": "match", "physical_type_size": "review"},
    "wrong-abv": {"abv": "review", "warning_text": "match"},
    "warning-typo": {"warning_text": "review", "abv": "match"},
    "title-case": {"warning_caps": "review", "heading_bold": "review"},
    "front-only": {"warning_text": "review"},
    "unreadable": {"warning_text": "review"},
    "import": {"country_of_origin": "match", "abv": "match", "net_contents": "match"},
}


def percentile95(values):
    return sorted(values)[max(0, math.ceil(len(values) * .95) - 1)] if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=1, help="Repeats per scenario; live requests may incur API fees")
    parser.add_argument("--allow-demo", action="store_true")
    parser.add_argument("--output", default="reports/evaluation.json")
    args = parser.parse_args()
    if args.runs < 1 or args.runs > 20:
        parser.error("Choose 1 to 20 repeats per scenario.")
    token = os.getenv("REVIEW_ACCESS_TOKEN", "")
    headers = {"X-Review-Token": token} if token else {}
    results = []
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=70, headers=headers, follow_redirects=False) as client:
        config_response = client.get("/api/config")
        config_response.raise_for_status()
        config = config_response.json()
        mode = config["mode"]
        if mode == "demo" and not args.allow_demo:
            parser.error("The server is in sample mode. Enable live AI or explicitly pass --allow-demo for a non-AI smoke test.")
        if not config["ready"]:
            parser.error("Live mode has no configured server API key.")
        if config["requires_access_code"] and not token:
            parser.error("Set REVIEW_ACCESS_TOKEN in your shell for this access-controlled deployment.")
        catalog = json.loads((ROOT / "samples/catalog.json").read_text())
        for repeat in range(args.runs):
            for scenario in catalog:
                files = [("images", (name, (ROOT / "samples" / name).read_bytes(), "image/png")) for name in scenario["filenames"]]
                started = time.perf_counter()
                try:
                    response = client.post("/api/verify", data={"application": json.dumps(scenario["application"])}, files=files)
                    elapsed = round((time.perf_counter()-started)*1000, 1)
                    body = response.json()
                    if response.status_code != 200:
                        results.append({"scenario": scenario["id"], "repeat":repeat+1, "ok":False, "mode":mode, "elapsed_ms":elapsed, "error":body.get("error",{}).get("code",f"http_{response.status_code}")})
                        continue
                    if body.get("mode") != mode:
                        raise ValueError("Provider mode changed during evaluation; discard mixed-mode results.")
                    status = {check["key"]:check["status"] for check in body["checks"]}
                    expectations = EXPECTED[scenario["id"]]
                    discrepancies = {key:{"expected":expected,"actual":status.get(key)} for key,expected in expectations.items() if status.get(key) != expected}
                    false_matches = sum(v["expected"] == "review" and v["actual"] == "match" for v in discrepancies.values())
                    results.append({"scenario":scenario["id"], "repeat":repeat+1, "ok":not discrepancies, "mode":mode, "model":body["model"], "elapsed_ms":elapsed, "extraction_ms":body["extraction_ms"], "false_matches":false_matches, "discrepancies":discrepancies})
                except (httpx.HTTPError, ValueError) as exc:
                    results.append({"scenario":scenario["id"], "repeat":repeat+1, "ok":False, "mode":mode, "elapsed_ms":round((time.perf_counter()-started)*1000,1), "error":type(exc).__name__})
    timings = [r["elapsed_ms"] for r in results if "error" not in r]
    report = {
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "mode":mode,
        "interpretation":"Controlled synthetic sample evaluation, not representative production accuracy." if mode == "openai" else "Fixture smoke test. NOT an AI accuracy or AI latency benchmark.",
        "requests":len(results), "passed_scenario_checks":sum(r["ok"] for r in results),
        "errors":sum("error" in r for r in results),
        "false_matches_on_explicit_test_cases":sum(r.get("false_matches",0) for r in results),
        "successful_request_median_ms":statistics.median(timings) if timings else None,
        "successful_request_p95_ms":percentile95(timings),
        "live_five_second_target_met":all(r["ok"] and r["elapsed_ms"] <= 5000 for r in results) if mode == "openai" else None,
        "results":results,
    }
    output = Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(f'{sum(r["ok"] for r in results)}/{len(results)} controlled scenario checks passed; mode={mode}. Report: {output}')
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
