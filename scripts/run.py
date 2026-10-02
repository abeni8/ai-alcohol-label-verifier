"""Run the API and the included React build with one command, from any directory."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="Development only")
    args = parser.parse_args()
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        parser.error("The frontend build is missing. Run npm install && npm run build in frontend/.")
    import uvicorn
    uvicorn.run("app.main:app", host=args.host, port=args.port, workers=1,
                reload=args.reload, reload_dirs=[str(ROOT / "backend")] if args.reload else None,
                timeout_keep_alive=5, limit_concurrency=16)


if __name__ == "__main__":
    main()
