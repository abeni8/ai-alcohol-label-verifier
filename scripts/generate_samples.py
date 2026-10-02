"""Render controlled synthetic test labels. No AI art, real brands, or font files included."""
import copy
import hashlib
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.policy import WARNING

OUT = ROOT / "samples"
OUT.mkdir(exist_ok=True)

def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default(size=size)


def base(title):
    im = Image.new("RGB", (1400, 1050), "#fcf6e8")
    d = ImageDraw.Draw(im)
    d.rectangle((28, 28, 1372, 1022), outline="#223d3b", width=4)
    d.text((80, 78), title, fill="#223d3b", font=font(22, True))
    d.text((80, 975), "SYNTHETIC TEST LABEL / NOT FOR SALE", fill="#665e50", font=font(20))
    return im, d


def save_front(name, brand="OLD TOM DISTILLERY", class_type="Kentucky Straight Bourbon Whiskey", alcohol="45% Alc./Vol. (90 Proof)", volume="750 mL"):
    im, d = base("DISTILLERY COLLECTION · TEST ARTWORK")
    d.line((80, 185, 1320, 185), fill="#ad813f", width=3)
    d.text((80, 270), brand, fill="#223d3b", font=font(65, True))
    d.text((82, 392), class_type, fill="#223d3b", font=font(36))
    d.text((82, 595), alcohol, fill="#223d3b", font=font(44, True))
    d.text((82, 690), volume, fill="#223d3b", font=font(40))
    im.save(OUT / name)
    return {"brand_name": {"value": brand}, "class_type": {"value": class_type}, "alcohol_content": {"value": alcohol}, "net_contents": {"value": volume}}


def save_back(name, warning=WARNING, heading_bold=True, producer="Old Tom Distillery", address="123 Example Lane, Louisville, KY 40202", origin=""):
    im, d = base("PRODUCER INFORMATION")
    d.text((80, 150), "Bottled by " + producer, fill="#223d3b", font=font(34))
    d.text((80, 218), address, fill="#223d3b", font=font(30))
    if origin:
        d.text((80, 278), "Product of " + origin, fill="#223d3b", font=font(30))
    # Keep the heading and body in one continuous paragraph, with the heading alone bold.
    x, y = 80, 388
    heading, body = warning.split(":", 1)
    heading += ":"
    d.text((x, y), heading, fill="#172522", font=font(31, heading_bold))
    x += int(d.textlength(heading + " ", font=font(31, heading_bold)))
    for word in body.strip().split():
        width = d.textlength(word + " ", font=font(31))
        if x + width > 1310:
            x, y = 80, y + 49
        d.text((x, y), word, fill="#172522", font=font(31))
        x += width
    im.save(OUT / name)
    return {"producer_name": {"value": producer}, "producer_address": {"value": address}, "country_of_origin": {"value": origin or None}, "warning": {"value": warning}, "heading_bold": "yes" if heading_bold else "no", "body_not_bold": "yes", "warning_separate": "yes", "warning_legible": "yes"}

fixtures = {}
def register(filename, part):
    fixtures[hashlib.sha256((OUT / filename).read_bytes()).hexdigest()] = part

register("old-tom-front.png", save_front("old-tom-front.png"))
register("old-tom-back.png", save_back("old-tom-back.png"))
register("wrong-abv-front.png", save_front("wrong-abv-front.png", alcohol="40% Alc./Vol. (80 Proof)"))
register("warning-typo-back.png", save_back("warning-typo-back.png", warning=WARNING.replace("machinery,", "machinery")))
register("title-case-back.png", save_back("title-case-back.png", warning=WARNING.replace("GOVERNMENT WARNING:", "Government Warning:"), heading_bold=False))
register("import-front.png", save_front("import-front.png", brand="DOMAINE SAMPLE", class_type="Red Wine", alcohol="12.5% Alc./Vol.", volume="0.75 L"))
register("import-back.png", save_back("import-back.png", producer="Domaine Sample", address="10 Example Road, Bordeaux, France", origin="France"))
im = Image.open(OUT / "old-tom-back.png").filter(ImageFilter.GaussianBlur(18))
im.save(OUT / "unreadable-back.png")
register("unreadable-back.png", {"issues": ["Back label is deliberately blurred; warning and producer information are not readable."]})
application = {"application_id": "OLD-TOM-001", "beverage_type": "distilled_spirits", "imported": False, "brand_name": "Old Tom Distillery", "class_type": "Kentucky Straight Bourbon Whiskey", "abv": "45", "net_contents": "750 mL", "producer_name": "Old Tom Distillery", "producer_address": "123 Example Lane, Louisville, KY 40202", "country_of_origin": ""}
cases = [
    ("old-tom", "Old Tom · matching fields", ["old-tom-front.png", "old-tom-back.png"], "Field values match; printed size still requires a human."),
    ("wrong-abv", "Alcohol percentage mismatch", ["wrong-abv-front.png", "old-tom-back.png"], "Application says 45%; artwork says 40%."),
    ("warning-typo", "Warning punctuation error", ["old-tom-front.png", "warning-typo-back.png"], "The comma after 'machinery' is missing."),
    ("title-case", "Warning heading formatting", ["old-tom-front.png", "title-case-back.png"], "The heading is title case and not bold."),
    ("front-only", "Missing back-label evidence", ["old-tom-front.png"], "The warning is not present in the supplied image set."),
    ("unreadable", "Unreadable back label", ["old-tom-front.png", "unreadable-back.png"], "Uncertainty must not turn into a match."),
]
catalog = []
for identifier, title, filenames, note in cases:
    app = copy.deepcopy(application)
    app['application_id'] = identifier.upper()
    catalog.append({"id": identifier, "title": title, "description": note, "application": app, "filenames": filenames})
app = dict(application, application_id="IMPORT-001", beverage_type="wine", imported=True, brand_name="Domaine Sample", class_type="Red Wine", abv="12.5", producer_name="Domaine Sample", producer_address="10 Example Road, Bordeaux, France", country_of_origin="France")
catalog.append({"id": "import", "title": "Imported wine · matching fields", "description": "Includes origin; 0.75 L and 750 mL compare as equal quantities.", "application": app, "filenames": ["import-front.png", "import-back.png"]})
(OUT / "fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
(OUT / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
print(f"Created {len(fixtures)} images and {len(catalog)} sample scenarios")
import csv
from app.batch import HEADERS
with (OUT / 'batch-template.csv').open('w', newline='') as f:
    csv.writer(f).writerow(HEADERS)
with (OUT / 'batch-sample.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    for item in [catalog[0], catalog[1], catalog[2], catalog[-1]]:
        row = dict(item['application'])
        row['imported'] = str(row['imported']).lower()
        row['image_files'] = '|'.join(item['filenames'])
        writer.writerow(row)
