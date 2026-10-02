"""Deterministic comparisons: conservative, transparent, and independent of AI."""
import difflib
import re
import unicodedata
from decimal import Decimal

from .models import Application, Check, Extraction, Observation
from .policy import WARNING


def whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFC", value).translate(str.maketrans({"’": "'", "‘": "'"}))
    return whitespace(value).casefold()


def parse_abv(value: str) -> Decimal | None:
    # Do not infer ABV from proof alone; multiple distinct percentages are ambiguous.
    values = re.findall(r"(?<![-\d.,])([0-9]+(?:\.[0-9]+)?)\s*%", value)
    distinct = {Decimal(v) for v in values}
    if len(distinct) != 1:
        return None
    number = next(iter(distinct))
    return number if 0 <= number <= 100 else None


def parse_volume(value: str) -> Decimal | None:
    # Unit equivalence is not a ruling on permitted label formats or standards of fill.
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(ml|cl|l|liter|liters|litre|litres)\s*", value, flags=re.I)
    if not match:
        return None
    number = Decimal(match[1]) * {"ml": 1, "cl": 10, "l": 1000, "liter": 1000, "liters": 1000, "litre": 1000, "litres": 1000}[match[2].lower()]
    return number if number > 0 else None


def compare_field(key: str, label: str, expected: str, obs: Observation, kind: str = "text", optional: bool = False) -> Check:
    row = Check(key=key, label=label, expected=expected or "Not supplied", observed=obs.value or "Not found in supplied images", status="review", reason="", image_indices=obs.image_indices)
    if not expected and optional:
        row.status = "not_checked"
        row.reason = "No expected value supplied. Applicability is not determined by this comparison."
    elif not obs.value:
        row.reason = "Not found in the supplied images; add a readable front/back image. This does not prove absence from the container."
    elif obs.uncertain or not obs.image_indices:
        row.reason = "The extraction is uncertain or has no image evidence. Compare with the artwork manually."
    elif kind == "abv":
        number = parse_abv(obs.value)
        if number is None:
            row.reason = "An unambiguous percentage could not be read; proof alone is not sufficient."
        elif number == Decimal(expected):
            row.status, row.reason = "match", "Exact numeric ABV match; no tolerance applied."
        else:
            row.reason = "The alcohol percentage differs from the application."
    elif kind == "volume":
        a, b = parse_volume(expected), parse_volume(obs.value)
        if a is None or b is None:
            row.reason = "The volume could not be parsed as one metric quantity. Check the units and label format."
        elif a == b:
            row.status, row.reason = "match", "Same metric volume after unit normalization; permitted labeling format is not certified."
        else:
            row.reason = "The net volume differs from the application."
    elif normalize(expected) == normalize(obs.value):
        row.status = "match"
        row.reason = "Exact text match." if expected == obs.value else "Match after capitalization, whitespace and apostrophe normalization only."
    else:
        row.reason = "Text differs from the application. No fuzzy matching or synonym substitution was applied."
    return row


def warning_diff(observed: str) -> list[dict[str, str]]:
    expected_words, actual_words = WARNING.split(), observed.split()
    result = []
    for tag, a, b, c, d in difflib.SequenceMatcher(a=expected_words, b=actual_words, autojunk=False).get_opcodes():
        result.append({"kind": tag, "expected": " ".join(expected_words[a:b]), "observed": " ".join(actual_words[c:d])})
    return result


def validate(application: Application, extraction: Extraction) -> list[Check]:
    rows = [
        compare_field("brand_name", "Brand name", application.brand_name, extraction.brand_name),
        compare_field("class_type", "Class / type", application.class_type, extraction.class_type),
        compare_field("abv", "Alcohol content", application.abv, extraction.alcohol_content, "abv", optional=application.beverage_type != "distilled_spirits"),
        compare_field("net_contents", "Net contents", application.net_contents, extraction.net_contents, "volume"),
        compare_field("producer_name", "Bottler / producer name", application.producer_name, extraction.producer_name),
        compare_field("producer_address", "Bottler / producer address", application.producer_address, extraction.producer_address),
    ]
    if application.imported or application.country_of_origin:
        rows.append(compare_field("country_of_origin", "Country of origin", application.country_of_origin, extraction.country_of_origin))
    else:
        rows.append(Check(key="country_of_origin", label="Country of origin", expected="Domestic product", observed=extraction.country_of_origin.value or "—", status="not_checked", reason="Import-origin check not applied because the application identifies a domestic product."))
    obs = extraction.warning
    raw = whitespace(obs.value or "")
    reliable = bool(obs.value) and not obs.uncertain and bool(obs.image_indices)
    matches = reliable and raw == WARNING
    rows.append(Check(key="warning_text", label="Government warning text", expected=WARNING, observed=obs.value or "Not found in supplied images", status="match" if matches else "review", reason="Exact wording and punctuation match; layout-only whitespace ignored." if matches else "Read against the official wording. Missing text, uncertainty, case changes or punctuation differences require review.", image_indices=obs.image_indices))
    capitals = reliable and raw.startswith("GOVERNMENT WARNING:")
    rows.append(Check(key="warning_caps", label="Warning heading capitals", expected="GOVERNMENT WARNING:", observed=raw.split(":", 1)[0] + ":" if ":" in raw else raw[:40] or "Not found", status="match" if capitals else "review", reason="Heading is uppercase with a colon." if capitals else "The heading must read GOVERNMENT WARNING: in capitals.", image_indices=obs.image_indices))
    for key, label, expected in [("heading_bold", "Warning heading bold", "Bold"), ("body_not_bold", "Warning body weight", "Not bold"), ("warning_separate", "Warning separation", "Separate, continuous paragraph"), ("warning_legible", "Warning legibility", "Readable on contrasting background")]:
        value = getattr(extraction, key)
        ok = reliable and value == "yes"
        rows.append(Check(key=key, label=label, expected=expected, observed={"yes": "Appears correct", "no": "Appears incorrect", "uncertain": "Uncertain"}[value], status="match" if ok else "review", reason="Visual screening observation; confirm against the image." if ok else "Visual evidence is missing, uncertain or appears incorrect. Human review is needed.", image_indices=obs.image_indices))
    rows.append(Check(key="physical_type_size", label="Printed size / character density", expected="Measured printed dimensions", observed="Not measurable from unscaled artwork", status="review", reason="Physical type size and characters per inch cannot be verified from pixels alone. This check always requires a reviewer."))
    if application.abv and Decimal(application.abv) < Decimal("0.5"):
        rows.append(Check(key="scope", label="Product scope", expected="At least 0.5% ABV", observed=application.abv + "%", status="review", reason="Products below 0.5% ABV are outside this prototype's rules. Do not use its warning findings as an applicability determination."))
    return rows
