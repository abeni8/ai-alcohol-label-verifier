import asyncio
import json

import httpx
import pytest

from app.config import ROOT, Settings
from app.errors import AppError
from app.images import prepare_image
from app.providers import OpenAIExtractor


def run_provider(handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAIExtractor(Settings(provider='openai', openai_api_key='test-only-secret', _env_file=None), client)
            image = prepare_image('old-tom-front.png', 'image/png', (ROOT / 'samples/old-tom-front.png').read_bytes())
            return await provider.extract([image])
    return asyncio.run(run())


def success_body(extraction):
    data = extraction.model_copy(deep=True)
    for name in ('brand_name','class_type','alcohol_content','net_contents','producer_name','producer_address','country_of_origin','warning'):
        getattr(data, name).image_indices = [1] if getattr(data, name).value else []
    return {'status':'completed', 'output':[{'type':'message', 'content':[{'type':'output_text','text':data.model_dump_json()}]}]}


def test_provider_contract(extraction):
    def handler(request):
        assert request.url == 'https://api.openai.com/v1/responses'
        assert request.headers['authorization'] == 'Bearer test-only-secret'
        data = json.loads(request.content)
        assert data['store'] is False
        assert data['text']['format']['strict'] is True
        assert data['text']['format']['schema']['additionalProperties'] is False
        assert 'application_id' not in request.content.decode()
        assert 'tools' not in data
        assert data['input'][0]['content'][2]['type'] == 'input_image'
        return httpx.Response(200, json=success_body(extraction))
    assert run_provider(handler).brand_name.value == 'OLD TOM DISTILLERY'

@pytest.mark.parametrize('status,code', [(401,'provider_credentials'),(403,'provider_credentials'),(429,'provider_busy'),(500,'provider_error'),(400,'provider_error')])
def test_provider_http_errors(status, code):
    with pytest.raises(AppError) as error:
        run_provider(lambda req: httpx.Response(status, json={'error':'private provider details'}))
    assert error.value.code == code
    assert 'private provider' not in error.value.message

@pytest.mark.parametrize('exception,code', [(httpx.ReadTimeout,'provider_timeout'),(httpx.ConnectError,'provider_unreachable')])
def test_network_errors(exception, code):
    def handler(req):
        raise exception('internal secret', request=req)
    with pytest.raises(AppError) as error:
        run_provider(handler)
    assert error.value.code == code

@pytest.mark.parametrize('body', [None, {}, {'status':'incomplete'}, {'status':'completed','output':[]}, {'status':'completed','output':[{'content':[{'type':'output_text','text':'not-json'}]}]}])
def test_invalid_output_fails_closed(body):
    with pytest.raises(AppError) as error:
        run_provider(lambda req: httpx.Response(200, json=body))
    assert error.value.code == 'invalid_extraction'


def test_refusal():
    with pytest.raises(AppError) as error:
        run_provider(lambda req: httpx.Response(200, json={'status':'completed','output':[{'content':[{'type':'refusal','refusal':'No'}]}]}))
    assert error.value.code == 'provider_refusal'


def test_invalid_image_reference(extraction):
    body = success_body(extraction)
    data = json.loads(body['output'][0]['content'][0]['text'])
    data['brand_name']['image_indices'] = [2]
    body['output'][0]['content'][0]['text'] = json.dumps(data)
    with pytest.raises(AppError) as error:
        run_provider(lambda req:httpx.Response(200, json=body))
    assert error.value.code == 'invalid_extraction'
