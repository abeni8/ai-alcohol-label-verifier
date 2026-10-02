import hashlib
import io
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .config import MAX_IMAGE_BYTES, MAX_PIXELS
from .errors import AppError


@dataclass(frozen=True)
class PreparedImage:
    filename: str
    sha256: str
    jpeg_bytes: bytes
    width: int
    height: int
    resized: bool


def prepare_image(filename: str, content_type: str, raw: bytes) -> PreparedImage:
    if not raw:
        raise AppError(422, "empty_image", "An uploaded image is empty.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise AppError(413, "image_too_large", "Each image must be 5 MB or smaller.")
    if not filename or '/' in filename or '\\' in filename or len(filename) > 200:
        raise AppError(422, "invalid_filename", "Use a filename without folders, no longer than 200 characters.")
    suffix = Path(filename).suffix.lower()
    allowed = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}
    if suffix not in allowed or content_type not in ("image/jpeg", "image/png"):
        raise AppError(415, "unsupported_image", "Upload JPEG or PNG images only.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format != allowed[suffix] or content_type != ("image/jpeg" if image.format == "JPEG" else "image/png"):
                    raise AppError(415, "image_type_mismatch", "The file extension, content type and actual image format must agree.")
                if getattr(image, "n_frames", 1) != 1:
                    raise AppError(415, "animated_image", "Upload a single-frame JPEG or PNG, not an animation.")
                if image.width * image.height > MAX_PIXELS:
                    raise AppError(413, "image_dimensions", "Each image must be 24 megapixels or smaller.")
                image.load()
                fixed = ImageOps.exif_transpose(image).convert("RGBA")
                canvas = Image.new("RGB", fixed.size, "white")
                canvas.paste(fixed, mask=fixed.getchannel("A"))
                resized = max(canvas.size) > 3000
                canvas.thumbnail((3000, 3000), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                canvas.save(output, format="JPEG", quality=95)  # No source metadata is carried over.
                return PreparedImage(filename, hashlib.sha256(raw).hexdigest(), output.getvalue(), canvas.width, canvas.height, resized)
    except AppError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise AppError(422, "unreadable_image", "This file is not a readable image. Export a new JPEG or PNG.") from exc
