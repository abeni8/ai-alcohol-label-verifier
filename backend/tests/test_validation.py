import pytest
from pydantic import ValidationError

from app.models import Application, Observation
from app.policy import WARNING
from app.validation import compare_field, normalize, parse_abv, parse_volume, validate, warning_diff


def observation(value, uncertain=False, indices=None):
    return Observation(value=value, uncertain=uncertain, image_indices=[1] if indices is None else indices)

@pytest.mark.parametrize("a,b", [("STONE’S THROW", "Stone's Throw"), (" Brand  Name ", "brand name"), ("café", "cafe\u0301"), ("A\nB", "a b")])
def test_normalization(a, b):
    assert normalize(a) == normalize(b)

@pytest.mark.parametrize("a,b", [("Stone", "Stones"), ("A-B", "A B"), ("Kentucky Straight Bourbon Whiskey", "Bourbon"), ("123 Main St.", "123 Main Street")])
def test_no_fuzzy_matching(a, b):
    assert compare_field("brand", "Brand", a, observation(b)).status == "review"

@pytest.mark.parametrize("text, expected", [("45% Alc./Vol. (90 Proof)", "45"), ("45.0% ABV", "45.0"), ("0.5%", "0.5"), ("100%", "100"), ("90 proof", None), ("45% / 40%", None), ("-45%", None), ("12,5%", None), ("101%", None), ("45% and 45.0%", "45")])
def test_abv_parser(text, expected):
    result = parse_abv(text)
    assert (str(result) if result is not None else None) == expected

@pytest.mark.parametrize("text, expected", [("750 mL", 750), ("0.75 L", 750), ("75 cl", 750), ("1 litre", 1000), ("0 mL", None), ("25.4 fl oz", None), ("750 mL / 1 L", None), ("-750 mL", None)])
def test_volume_parser(text, expected):
    assert parse_volume(text) == expected

@pytest.mark.parametrize("actual,status", [("45%", "match"), ("45.0%", "match"), ("44.99%", "review"), ("90 proof", "review")])
def test_abv_comparison(actual, status):
    assert compare_field("abv", "ABV", "45", observation(actual), "abv").status == status

@pytest.mark.parametrize("actual,status", [("0.75 L", "match"), ("750mL", "match"), ("700 mL", "review"), ("750 mL extra", "review")])
def test_volume_comparison(actual, status):
    assert compare_field("volume", "Volume", "750 mL", observation(actual), "volume").status == status

@pytest.mark.parametrize("value,uncertain,indices", [(None, True, []), ("Brand", True, [1]), ("Brand", False, [])])
def test_uncertainty_never_passes(value, uncertain, indices):
    assert compare_field("brand", "Brand", "Brand", observation(value, uncertain, indices)).status == "review"

@pytest.mark.parametrize("edit", [lambda x:x.replace("machinery,", "machinery"), lambda x:x.replace("not drink", "drink"), lambda x:x.replace("GOVERNMENT", "Government"), lambda x:x.replace("(1)", "1."), lambda x:x.replace("health problems.", "health issues.")])
def test_warning_must_match(application, extraction, edit):
    extraction.warning.value = edit(WARNING)
    checks = {r.key:r for r in validate(application, extraction)}
    assert checks["warning_text"].status == "review"


def test_warning_layout_whitespace(application, extraction):
    extraction.warning.value = WARNING.replace(" ", "\n  ")
    checks = {r.key:r for r in validate(application, extraction)}
    assert checks["warning_text"].status == "match"


def test_physical_size_always_manual(application, extraction):
    checks = {r.key:r for r in validate(application, extraction)}
    assert checks["physical_type_size"].status == "review"
    assert checks["warning_text"].status == "match"
    assert checks["country_of_origin"].status == "not_checked"

@pytest.mark.parametrize("field", ["heading_bold", "body_not_bold", "warning_separate", "warning_legible"])
@pytest.mark.parametrize("value", ["no", "uncertain"])
def test_visual_flags(application, extraction, field, value):
    setattr(extraction, field, value)
    checks = {r.key:r for r in validate(application, extraction)}
    assert checks[field].status == "review"


def test_no_warning_means_no_visual_pass(application, extraction):
    extraction.warning = observation(None, True, [])
    checks = {r.key:r for r in validate(application, extraction)}
    assert all(checks[k].status == "review" for k in ("warning_text", "warning_caps", "heading_bold", "body_not_bold"))

@pytest.mark.parametrize("change", [{"brand_name":" "}, {"abv":"NaN"}, {"abv":"101"}, {"abv":"-1"}, {"abv":"45%"}, {"abv":""}, {"imported":True, "country_of_origin":""}, {"imported":"false"}, {"beverage_type":"other"}, {"producer_name":""}, {"unknown":"field"}])
def test_input_rejection(application, change):
    with pytest.raises(ValidationError):
        Application(**(application.model_dump() | change))


def test_optional_wine_abv(application, extraction):
    wine = Application(**(application.model_dump() | {"beverage_type":"wine", "abv":""}))
    rows = {r.key:r for r in validate(wine, extraction)}
    assert rows["abv"].status == "not_checked"


def test_import_country_checked(application, extraction):
    imported = Application(**(application.model_dump() | {"imported":True, "country_of_origin":"France"}))
    assert {r.key:r for r in validate(imported, extraction)}["country_of_origin"].status == "review"


def test_below_threshold_outside_scope(application, extraction):
    app = Application(**(application.model_dump() | {"abv":"0.3"}))
    assert any(r.key == "scope" and r.status == "review" for r in validate(app, extraction))


def test_warning_diff_preserves_error():
    result = warning_diff(WARNING.replace("machinery,", "machinery"))
    changed = [r for r in result if r["kind"] != "equal"]
    assert changed == [{"kind":"replace", "expected":"machinery,", "observed":"machinery"}]
