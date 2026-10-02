"""Validate a CSV manifest without sending images to the model or storing a job.

The browser runs bounded individual requests after every manifest row has passed
validation. This keeps errors isolated and avoids a long HTTP request for a batch.
"""
import csv
import io
import json
from pathlib import PurePath
from typing import Annotated

from fastapi import File, Form, UploadFile
from pydantic import ValidationError

from .config import MAX_BATCH_ROWS, MAX_CSV_BYTES, MAX_IMAGES
from .errors import AppError
from .models import Application

HEADERS = ["application_id", "beverage_type", "imported", "brand_name", "class_type", "abv", "net_contents", "producer_name", "producer_address", "country_of_origin", "image_files"]


def safe_name(name: str) -> bool:
    return bool(name) and len(name) <= 200 and '/' not in name and '\\' not in name and not name.startswith('.') and PurePath(name).suffix.lower() in {'.jpg', '.jpeg', '.png'}


def parse_manifest(raw: bytes, available_names: list[str]) -> dict:
    if len(raw) > MAX_CSV_BYTES:
        raise AppError(413, "csv_too_large", "CSV files must be 1 MB or smaller.")
    if len(available_names) > MAX_BATCH_ROWS * MAX_IMAGES:
        raise AppError(422, "too_many_batch_images", "Select no more than 900 images for a batch.")
    if any(not isinstance(n, str) or not safe_name(n) for n in available_names):
        raise AppError(422, "invalid_filename", "Batch image names must be JPEG/PNG filenames without directory paths.")
    if len(available_names) != len(set(available_names)):
        raise AppError(422, "duplicate_filenames", "Selected images have duplicate filenames. Rename them before validating the CSV.")
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise AppError(422, "csv_encoding", "Save the CSV as UTF-8 and try again.") from exc
    if '\x00' in text:
        raise AppError(422, "csv_invalid", "The CSV contains invalid binary data.")
    reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
    try:
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or set(headers) != set(HEADERS):
            raise AppError(422, "csv_headers", "Use the provided CSV template without changing, omitting or duplicating its column names.")
        rows, errors, seen_ids, used = [], [], set(), set()
        available = set(available_names)
        for index, row in enumerate(reader, 1):
            line = reader.line_num
            if index > MAX_BATCH_ROWS:
                raise AppError(422, "csv_row_limit", "A batch can contain no more than 300 applications.")
            if None in row or any(v is None for v in row.values()):
                errors.append({"line": line, "message": "Wrong number of CSV columns. Quote values that contain commas."})
                continue
            row = {k: v.strip() for k,v in row.items()}
            identifier = row['application_id']
            if identifier in seen_ids:
                errors.append({"line": line, "message": "Application IDs must be unique."})
            seen_ids.add(identifier)
            flag = row['imported'].lower()
            if flag not in {'true','false'}:
                errors.append({"line": line, "message": "The imported column must be true or false."})
                continue
            names = [n.strip() for n in row.pop('image_files').split('|')]
            if not 1 <= len(names) <= MAX_IMAGES or len(names) != len(set(names)) or any(not safe_name(n) for n in names):
                errors.append({"line": line, "message": "Use one to three unique JPEG/PNG image filenames, separated by |."})
                continue
            missing = [name for name in names if name not in available]
            if missing:
                errors.append({"line": line, "message": "Missing selected image(s): " + ', '.join(missing)})
            row['imported'] = flag == 'true'
            try:
                application = Application.model_validate(row)
                rows.append({"application": application.model_dump(), "filenames": names, "line": line})
                used.update(names)
            except ValidationError as exc:
                for e in exc.errors(include_input=False, include_context=False):
                    errors.append({"line": line, "message": f"{'.'.join(map(str, e['loc'])) or 'Application'}: {e['msg']}"})
        if not rows and not errors:
            raise AppError(422, "csv_empty", "The CSV must contain at least one application.")
        if errors:
            return {"valid": False, "rows": [], "errors": errors, "unused_files": []}
        return {"valid": True, "rows": rows, "errors": [], "unused_files": sorted(available - used)}
    except csv.Error as exc:
        raise AppError(422, "csv_invalid", "The CSV could not be parsed. Check quote characters and delimiters.") from exc


def register_batch_routes(app):
    @app.post('/api/batch/validate')
    async def validate_batch(manifest: Annotated[UploadFile, File()], filenames: Annotated[str, Form()]):
        try:
            if not (manifest.filename or '').lower().endswith('.csv'):
                raise AppError(415, "csv_type", "Upload a .csv manifest.")
            if len(filenames) > 200000:
                raise AppError(422, "invalid_filenames", "Too many or overly long filenames.")
            try:
                names = json.loads(filenames)
                if not isinstance(names, list):
                    raise ValueError()
            except (ValueError, TypeError) as exc:
                raise AppError(422, "invalid_filenames", "Provide a list of the selected image filenames.") from exc
            return parse_manifest(await manifest.read(MAX_CSV_BYTES + 1), names)
        finally:
            await manifest.close()
