import csv
import io
import json

import pytest

from app.batch import HEADERS, parse_manifest
from app.config import ROOT
from app.errors import AppError


def manifest(application, changes=None, count=1):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=HEADERS)
    writer.writeheader()
    for i in range(count):
        row = application.model_dump() | {'application_id':str(i), 'imported':'false', 'image_files':'old-tom-front.png|old-tom-back.png'}
        writer.writerow(row | (changes or {}))
    return out.getvalue().encode()

NAMES = ['old-tom-front.png','old-tom-back.png']


def test_csv_valid(application):
    result = parse_manifest(manifest(application), NAMES)
    assert result['valid'] and len(result['rows']) == 1
    assert result['rows'][0]['application']['producer_address'] == application.producer_address
    assert result['rows'][0]['application']['imported'] is False


def test_bom_csv(application):
    assert parse_manifest(b'\xef\xbb\xbf'+manifest(application), NAMES)['valid']

@pytest.mark.parametrize('changes', [{'abv':'not-a-number'}, {'brand_name':''}, {'imported':'yes'}, {'image_files':'absent.png'}, {'image_files':'../old-tom-front.png'}, {'image_files':'old-tom-front.png|old-tom-front.png'}, {'image_files':''}, {'imported':'true','country_of_origin':''}])
def test_row_errors(application, changes):
    result = parse_manifest(manifest(application, changes), NAMES)
    assert not result['valid']
    assert result['rows'] == [] and result['errors']


def test_duplicate_application_ids(application):
    result = parse_manifest(manifest(application, {'application_id':'duplicate'}, 2), NAMES)
    assert not result['valid']


def test_duplicate_upload_names(application):
    with pytest.raises(AppError) as e:
        parse_manifest(manifest(application), NAMES + NAMES)
    assert e.value.code == 'duplicate_filenames'


def test_300_rows(application):
    assert len(parse_manifest(manifest(application, count=300), NAMES)['rows']) == 300


def test_301_rows(application):
    with pytest.raises(AppError) as e:
        parse_manifest(manifest(application, count=301), NAMES)
    assert e.value.code == 'csv_row_limit'


def test_unused_names(application):
    assert parse_manifest(manifest(application), NAMES+['unused.png'])['unused_files'] == ['unused.png']

@pytest.mark.parametrize('raw,code', [(b'','csv_headers'),(b'wrong\nvalues\n','csv_headers'),(b'\xff','csv_encoding'),(b'x'*1000001,'csv_too_large'),(b'\x00','csv_invalid'), ((','.join(HEADERS)+'\n').encode(),'csv_empty')])
def test_invalid_files(raw, code):
    with pytest.raises(AppError) as e:
        parse_manifest(raw, NAMES)
    assert e.value.code == code


def test_bad_column_count(application):
    raw = manifest(application).replace(b'0,distilled_spirits', b'0,extra,distilled_spirits')
    assert not parse_manifest(raw, NAMES)['valid']


def test_batch_endpoint(client):
    r = client.post('/api/batch/validate', data={'filenames':json.dumps([p.name for p in (ROOT/'samples').glob('*.png')])}, files={'manifest':('sample.csv',(ROOT/'samples/batch-sample.csv').read_bytes(),'text/csv')})
    assert r.status_code == 200 and r.json()['valid']
    assert len(r.json()['rows']) == 4


def test_batch_invalid_name_types(client):
    r = client.post('/api/batch/validate', data={'filenames':'[123]'}, files={'manifest':('sample.csv',(ROOT/'samples/batch-sample.csv').read_bytes(),'text/csv')})
    assert r.status_code == 422
