"""Wait for a local service before running acceptance tests."""
import time
import urllib.error
import urllib.request

for attempt in range(60):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/ready", timeout=2) as response:
            if response.status == 200:
                print("Server ready")
                break
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(1)
else:
    raise SystemExit("The local service did not become ready within 60 attempts.")
