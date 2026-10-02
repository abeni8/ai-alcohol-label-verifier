"""Tests use generated pixel data; no OCR or external calls."""
import hashlib
import io

import pytest
from PIL import Image, PngImagePlugin

from app.errors import AppError
from app.images import prepare_image


def encoded(mode="RGB", size=(80, 60), format="PNG", **kwargs):
    image = Image.new(mode, size)
    out = io.BytesIO()
    image.save(out, format=format, **kwargs)
    return out.getvalue()


@pytest.mark.parametrize("name,mime,format", [
    ("a.png", "image/jpeg", "PNG"),
    ("a.jpg", "image/jpeg", "PNG"),
    ("a.png", "image/png", "JPEG"),
    ("a.jpeg", "image/png", "JPEG"),
])
def test_declared_format_must_match(name, mime, format):
    with pytest.raises(AppError) as exc:
        prepare_image(name, mime, encoded(format=format))
    assert exc.value.code == "image_type_mismatch"


def test_transparency_flattens_to_white():
    out = prepare_image("a.png", "image/png", encoded(mode="RGBA"))
    with Image.open(io.BytesIO(out.jpeg_bytes)) as result:
        assert result.mode == "RGB"
        assert result.getpixel((0, 0)) == (255, 255, 255)


def test_metadata_is_not_forwarded_and_hash_uses_original():
    info = PngImagePlugin.PngInfo()
    info.add_text("Private note", "not sent to the image service")
    raw = encoded(pnginfo=info)
    out = prepare_image("a.png", "image/png", raw)
    assert out.sha256 == hashlib.sha256(raw).hexdigest()
    assert b"not sent to" not in out.jpeg_bytes
    with Image.open(io.BytesIO(out.jpeg_bytes)) as result:
        assert not result.getexif()


def test_exif_rotation_applied_then_removed():
    exif = Image.Exif()
    exif[274] = 6  # 90 degrees clockwise.
    raw = encoded(size=(80, 60), format="JPEG", exif=exif)
    out = prepare_image("a.jpg", "image/jpeg", raw)
    assert (out.width, out.height) == (60, 80)
    with Image.open(io.BytesIO(out.jpeg_bytes)) as result:
        assert not result.getexif()


def test_large_image_downscales_and_reports_it():
    out = prepare_image("wide.png", "image/png", encoded(size=(3200, 200)))
    assert out.resized and out.width == 3000 and out.height < 200


def test_pixel_limit_is_checked_before_full_decode():
    with pytest.raises(AppError) as exc:
        prepare_image("large.png", "image/png", encoded(size=(6000, 4100)))
    assert exc.value.code == "image_dimensions"


def test_apng_rejected():
    out = io.BytesIO()
    Image.new("RGB", (40,40), "white").save(out, format="PNG", save_all=True,
        append_images=[Image.new("RGB", (40,40), "black")], duration=100, loop=0)
    with pytest.raises(AppError) as exc:
        prepare_image("animated.png", "image/png", out.getvalue())
    assert exc.value.code == "animated_image"


def test_truncated_image_rejected():
    raw = encoded()[:45]
    with pytest.raises(AppError) as exc:
        prepare_image("broken.png", "image/png", raw)
    assert exc.value.code == "unreadable_image"
