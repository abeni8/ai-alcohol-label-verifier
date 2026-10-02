"""Check that the included static build has no broken local module/asset references."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend/dist"
missing = []
checked = 0
for source in sorted(DIST.rglob("*")):
    if source.suffix not in {".html", ".js", ".mjs"}:
        continue
    text = source.read_text()
    patterns = [r'(?:src|href)="([^"]+)"'] if source.suffix == ".html" else [r'''^\s*import\s+(?:[^;\n]*?\s+from\s+)?["']([^"']+)["']''']
    for pattern in patterns:
        for reference in re.findall(pattern, text, re.MULTILINE):
            if reference.startswith(("data:","https:","http:","#")):
                continue
            checked += 1
            target = DIST / reference.lstrip("/") if reference.startswith("/") else source.parent / reference
            if not target.is_file():
                missing.append(f"{source.relative_to(DIST)} -> {reference}")
if missing:
    raise SystemExit("Missing static assets:\n" + "\n".join(missing))
print(f"PASS: {checked} static imports/asset references resolve.")
