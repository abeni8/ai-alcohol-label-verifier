"""Versioned screening rules, NOT a complete determination of TTB compliance.

Source: 27 CFR 16.21–16.22; TTB distilled spirits health-warning guidance.
See docs/SOURCES.md. The comma after 'machinery' is intentional and mandatory.
"""

POLICY_VERSION = "ttb-screening-v1"
WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)
LIMITATIONS = [
    "A match is a comparison with extracted text, not TTB approval or a guarantee of accurate transcription.",
    "Printed type size and character density require physical measurements; photographs alone do not establish compliance.",
    "Visual boldness, separation and legibility are screening observations and require human confirmation.",
    "This prototype is for products at or above 0.5% ABV. Category-specific exceptions and full regulatory approval are outside scope.",
]
