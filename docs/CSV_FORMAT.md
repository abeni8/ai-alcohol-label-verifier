# CSV format and batch operation

Use `samples/batch-template.csv`, or begin with the working `samples/batch-sample.csv`. Encoding must be UTF-8; a UTF-8 byte-order mark is accepted. Limit: 1 MB, 300 applications. The delimiter is a comma.

All **column headers** below are mandatory, with no extras or duplicates. Their order can vary. Values noted as optional may be blank, but the column must still exist.

| Column | Expected value |
| --- | --- |
| `application_id` | Nonempty unique identifier, up to 100 characters |
| `beverage_type` | `distilled_spirits`, `wine`, or `malt_beverage` |
| `imported` | `true` or `false` (case-insensitive) |
| `brand_name` | Expected brand |
| `class_type` | Expected class/type designation |
| `abv` | Numeric percent, e.g. `45`, not `45%`; required for spirits, optional comparison for wine/beer |
| `net_contents` | Metric quantity, e.g. `750 mL` or `0.75 L` |
| `producer_name` | Expected bottler/producer name, without a role prefix |
| `producer_address` | Expected address, quoted when it contains a comma |
| `country_of_origin` | Required for imports; otherwise optional |
| `image_files` | One to three exact filenames, joined with a pipe character (`&#124;`) |

```csv
application_id,beverage_type,imported,brand_name,class_type,abv,net_contents,producer_name,producer_address,country_of_origin,image_files
OLD-TOM-001,distilled_spirits,false,Old Tom Distillery,Kentucky Straight Bourbon Whiskey,45,750 mL,Old Tom Distillery,"123 Example Lane, Louisville, KY 40202",,old-tom-front.png|old-tom-back.png
```

Filenames are case-sensitive, must end in .jpg/.jpeg/.png, and cannot include directories. Each selected file must have a unique filename. A row cannot reference the same image twice. The same selected file can deliberately be referenced by different applications, as the controlled sample does for a shared back label.

## Workflow

1. Select the CSV and all referenced images. Selecting hundreds of files retains browser File references; it does not upload the whole batch at once.
2. Validate CSV and image mapping. The server checks every row, duplicate IDs, types, missing files, and the image-count limit. A row error blocks the entire queue; no partial batch is silently accepted. Unreferenced selected images are reported and are not sent for verification.
3. Start the queue. Two applications are submitted at a time, each with its own expected values and mapped images. File contents are validated by the individual verification endpoint before inference.
4. Inspect individual findings or export the batch. The CSV export includes application IDs, check values, status, reasons, provider mode, timings, and failures/cancellations. Potential spreadsheet-formula prefixes are neutralized.

Stop queue halts new scheduling and aborts browser requests. Completed results stay available; upstream requests already sent may continue. Retry unfinished targets failed/cancelled rows without resubmitting completed ones. There is no background persistence, automatic exponential retry, or recovery after a tab refresh.

A malformed image can pass filename mapping and still fail the later image-decoding check. That failure is shown on its application rather than represented as a label match or a regulatory rejection.
