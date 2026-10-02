import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.images import prepare_image
from app.main import create_app
from app.models import Application
from app.providers import DemoExtractor

@pytest.fixture
def catalog():
    return json.loads((ROOT / "samples/catalog.json").read_text())

@pytest.fixture
def application(catalog):
    return Application(**catalog[0]["application"])

@pytest.fixture
def extraction():
    images = [prepare_image(name, "image/png", (ROOT / "samples" / name).read_bytes()) for name in ("old-tom-front.png", "old-tom-back.png")]
    return asyncio.run(DemoExtractor().extract(images))

@pytest.fixture
def client():
    with TestClient(create_app(Settings(provider="demo", _env_file=None))) as c:
        yield c


def upload_files(names=("old-tom-front.png", "old-tom-back.png")):
    return [("images", (name, (ROOT / "samples" / name).read_bytes(), "image/png")) for name in names]
