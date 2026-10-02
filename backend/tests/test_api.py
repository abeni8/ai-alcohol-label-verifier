import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import MAX_BODY_BYTES, ROOT, Settings
from app.main import create_app
from conftest import upload_files


def test_health_config(client):
    assert client.get("/api/health").json() == {"status":"ok"}
    config = client.get("/api/config").json()
    assert config["mode"] == "demo"
    assert "openai_api_key" not in config
    assert client.get("/api/ready").status_code == 200


def test_sample_verification(client, application):
    response = client.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["mode"] == "demo" and data["target_met"] is None
    assert data["reviews"] == 1
    assert data["matches"] == 12
    assert data["not_checked"] == 1
    assert data["filenames"] == ["old-tom-front.png", "old-tom-back.png"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"

@pytest.mark.parametrize("names,key", [(("wrong-abv-front.png", "old-tom-back.png"), "abv"), (("old-tom-front.png", "warning-typo-back.png"), "warning_text"), (("old-tom-front.png", "title-case-back.png"), "warning_caps"), (("old-tom-front.png",), "warning_text"), (("old-tom-front.png", "unreadable-back.png"), "warning_text")])
def test_scenarios(client, application, names, key):
    response = client.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files(names))
    assert response.status_code == 200, response.text
    assert {r['key']:r for r in response.json()['checks']}[key]['status'] == 'review'


def test_unknown_image_not_simulated(client, application):
    out = io.BytesIO()
    Image.new("RGB", (300, 300), "white").save(out, format="PNG")
    response = client.post("/api/verify", data={"application":application.model_dump_json()}, files=[("images", ("old-tom-front.png", out.getvalue(), "image/png"))])
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'demo_unknown_image'

@pytest.mark.parametrize("name,raw,mime,status", [("bad.pdf", b'%PDF', 'application/pdf',415), ("fake.png", b'notimage', 'image/png',422), ("empty.png", b'', 'image/png',422), ("../file.png", b'abc', 'image/png',422), ("x.png", b'x'*(5*1024*1024+1), 'image/png',413)])
def test_upload_errors(client, application, name, raw, mime, status):
    response = client.post("/api/verify", data={"application":application.model_dump_json()}, files=[("images",(name,raw,mime))])
    assert response.status_code == status, response.text
    assert "checks" not in response.json()


def test_duplicate_files(client, application):
    response = client.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files(("old-tom-front.png", "old-tom-front.png")))
    assert response.status_code == 422


def test_too_many_files(client, application):
    response = client.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files(("old-tom-front.png", "old-tom-back.png", "wrong-abv-front.png", "warning-typo-back.png")))
    assert response.status_code == 422


def test_bad_application(client):
    response = client.post("/api/verify", data={"application":"{no}"}, files=upload_files())
    assert response.status_code == 422


def test_no_files(client, application):
    response = client.post("/api/verify", data={"application":application.model_dump_json()})
    assert response.status_code == 422


def test_auth_no_key_leak(application):
    settings = Settings(provider="demo", review_access_token="review-secret", openai_api_key="private-ai-secret", _env_file=None)
    with TestClient(create_app(settings)) as c:
        assert c.get("/api/config").json()["requires_access_code"]
        assert "secret" not in c.get("/api/config").text
        assert c.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files()).status_code == 401
        assert c.post("/api/verify", headers={"X-Review-Token":"review-secret"}, data={"application":application.model_dump_json()}, files=upload_files()).status_code == 200


def test_external_origin_rejected(client, application):
    response = client.post("/api/verify", headers={"Origin":"https://malicious.invalid"}, data={"application":application.model_dump_json()}, files=upload_files())
    assert response.status_code == 403


def test_body_limit(client):
    response = client.post("/api/verify", content=b"", headers={"Content-Length":str(MAX_BODY_BYTES+1)})
    assert response.status_code == 413


def test_chunked_body_limit(client):
    response = client.post("/api/verify", content=(b'x'*1024*1024 for _ in range(17)))
    assert response.status_code == 413


def test_hidden_fixture_file(client):
    assert client.get("/api/sample-files/fixtures.json").status_code == 404
    assert client.get("/api/sample-files/old-tom-front.png").status_code == 200


def test_live_missing_key_does_not_fallback(application):
    with TestClient(create_app(Settings(provider="openai", openai_api_key="", _env_file=None))) as c:
        assert c.get("/api/ready").status_code == 503
        r = c.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files())
        assert r.status_code == 503
        assert r.json()['error']['code'] == 'provider_unconfigured'


def test_rate_limit(application):
    with TestClient(create_app(Settings(provider="demo", requests_per_minute=1, _env_file=None))) as c:
        assert c.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files()).status_code == 200
        r = c.post("/api/verify", data={"application":application.model_dump_json()}, files=upload_files())
        assert r.status_code == 429
        assert r.headers['retry-after'] == '60'
