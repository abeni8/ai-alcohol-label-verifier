"""Browser acceptance tests against a running FastAPI server.

Default: standard HTTP navigation. --bridge: in-memory browser rendering and an
explicit local HTTP bridge for environments that disable browser URL navigation.
The bridge executes the same source and real local API, not hardcoded responses.
Optional injected failures/delays are identified as simulated resilience checks.
"""
import argparse
import base64
import json
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--bridge', action='store_true')
parser.add_argument('--browser', default=None)
parser.add_argument('--url', default='http://127.0.0.1:8000')
args = parser.parse_args()
checks, browser_errors = [], []

BRIDGE = r"""
window.__nativeFetch = window.fetch.bind(window);
const toBase64 = bytes => {let text=''; for(let i=0;i<bytes.length;i+=8192)text+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(text);};
window.fetch = async (input, options={}) => {
  if(String(input).startsWith('blob:'))return window.__nativeFetch(input,options);
  const request = new Request(new URL(input,'http://review.local').href,options);
  const bytes = new Uint8Array(await request.arrayBuffer());
  const go = async () => {
    if(window.__delayVerify && new URL(request.url).pathname==='/api/verify')await new Promise(r=>setTimeout(r,window.__delayVerify));
    if(options.signal?.aborted)throw new DOMException('Aborted','AbortError');
    if(window.__failNextVerify && new URL(request.url).pathname==='/api/verify'){
      window.__failNextVerify=false;
      return new Response(JSON.stringify({error:{code:'provider_timeout',message:'Simulated provider timeout. Retry or review manually.'}}),{status:504,headers:{'Content-Type':'application/json'}});
    }
    const result = await window.__http({path:new URL(request.url).pathname,method:request.method,headers:Object.fromEntries(request.headers),body:toBase64(bytes)});
    return new Response(Uint8Array.from(atob(result.body),c=>c.charCodeAt(0)),{status:result.status,headers:result.headers});
  };
  if(!options.signal)return go();
  if(options.signal.aborted)throw new DOMException('Aborted','AbortError');
  return await Promise.race([go(),new Promise((_,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true}))]);
};
"""
EXPORT_CAPTURE = r"""
window.__downloads=[];
HTMLAnchorElement.prototype.click=function(){if(this.download){window.__downloads.push({url:this.href,name:this.download});}else{this.dispatchEvent(new MouseEvent('click',{bubbles:true}));}};
"""

def record(name):
    checks.append(name)
    print('PASS', name)

with httpx.Client(base_url=args.url, timeout=25) as http, sync_playwright() as p:
    launch = {'headless':True}
    if args.browser:
        launch.update(executable_path=args.browser, args=['--no-sandbox'])
    browser = p.chromium.launch(**launch)
    page = browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
    page.on('pageerror', lambda e:browser_errors.append(str(e)))
    def load_page():
        if args.bridge:
            def bridge(data):
                response = http.request(data['method'], data['path'], headers=data['headers'], content=base64.b64decode(data['body']))
                return {'status':response.status_code,'headers':dict(response.headers),'body':base64.b64encode(response.content).decode()}
            page.expose_function('__http',bridge)
            page.set_content('<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Label Review · Alcohol label verification</title></head><body><div id="root"></div></body></html>')
            page.add_style_tag(content=(ROOT/'frontend/offline-vendor/bootstrap.min.css').read_text())
            page.add_style_tag(content=(ROOT/'frontend/src/styles.css').read_text())
            page.add_script_tag(content=BRIDGE)
            page.add_script_tag(content=(ROOT/'evidence/browser-harness.js').read_text())
        else:
            page.goto(args.url,wait_until='networkidle')
        page.get_by_role('button',name='Load sample',exact=True).wait_for()
        # Favicon artwork is decorative; use data to avoid network in bridge screenshots.
        page.evaluate("data=>{const im=document.querySelector('.brand img');if(im)im.src=data;}", 'data:image/svg+xml;base64,' + base64.b64encode((ROOT/'frontend/public/favicon.svg').read_bytes()).decode())
        page.evaluate(EXPORT_CAPTURE)
    load_page()
    expect(page.get_by_text('SAMPLE MODE',exact=True)).to_be_visible()
    assert not browser_errors, browser_errors
    record('Individual form renders with explicit sample-mode disclosure')
    page.screenshot(path=str(ROOT/'evidence/01-individual-form.png'),full_page=True)

    page.get_by_role('button',name='Load sample',exact=True).click()
    expect(page.locator('#brand_name')).to_have_value('Old Tom Distillery')
    expect(page.locator('.preview-card')).to_have_count(2)
    record('Sample populates editable expected values and two image previews')
    page.get_by_role('button',name='Verify label',exact=False).click()
    expect(page.get_by_test_id('results')).to_be_visible(timeout=20000)
    expect(page.get_by_test_id('check-brand_name').locator('.result-badge')).to_have_text('✓Match')
    expect(page.get_by_test_id('check-physical_type_size').locator('.result-badge')).to_have_text('!Review needed')
    expect(page.locator('[data-testid^="check-"]')).to_have_count(14)
    record('Actual API results show green normalized matches and red physical-size review')
    page.screenshot(path=str(ROOT/'evidence/02-individual-results.png'),full_page=True)

    page.get_by_label('Only review needed').check()
    expect(page.locator('[data-testid^="check-"]')).to_have_count(1)
    record('Review-only filter shows the right checks')
    page.get_by_role('button',name='Export results',exact=True).click()
    csv = page.evaluate("async()=>await (await fetch(window.__downloads.at(-1).url)).text()")
    assert 'application_id' in csv and 'Printed size' in csv and 'demo' in csv
    record('Individual CSV export contains full results and mode provenance')

    page.locator('#brand_name').fill('Different Brand')
    expect(page.get_by_test_id('results')).to_have_count(0)
    page.get_by_role('button',name='Verify label',exact=False).click()
    expect(page.get_by_test_id('check-brand_name').locator('.result-badge')).to_have_text('!Review needed')
    record('Editing input invalidates stale results; changed brand is flagged')

    page.locator('#sample-choice').select_option('warning-typo')
    page.get_by_role('button',name='Load sample',exact=True).click()
    expect(page.locator('#brand_name')).to_have_value('Old Tom Distillery')
    page.get_by_role('button',name='Verify label',exact=False).click()
    expect(page.get_by_test_id('check-warning_text').locator('.result-badge')).to_have_text('!Review needed')
    page.get_by_text('Inspect government warning differences',exact=True).click()
    expect(page.locator('.diff-mark').first).to_contain_text('machinery,')
    record('Warning punctuation discrepancy and expected/observed diff are visible')

    page.get_by_test_id('single-files').set_input_files({'name':'bad.pdf','mimeType':'application/pdf','buffer':b'%PDF fake'})
    expect(page.get_by_role('alert')).to_contain_text('JPEG')
    expect(page.get_by_test_id('results')).to_have_count(0)
    expect(page.locator('.preview-card')).to_have_count(0)
    record('Unsupported uploads clear stale evidence and block submission')
    page.get_by_role('button',name='Load sample',exact=True).click()
    expect(page.locator('.preview-card')).to_have_count(2)

    if args.bridge:
        page.evaluate('window.__failNextVerify=true')
        page.get_by_role('button',name='Verify label',exact=False).click()
        expect(page.get_by_role('alert')).to_contain_text('Simulated provider timeout')
        expect(page.get_by_test_id('results')).to_have_count(0)
        record('Simulated provider timeout surfaces an error, not successful results')

    page.get_by_role('button',name='Batch review').click()
    page.get_by_role('button',name='Load sample batch').click()
    expect(page.get_by_text('✓ 6 images selected')).to_be_visible()
    page.get_by_role('button',name='Validate CSV & image mapping').click()
    expect(page.get_by_test_id('batch-row')).to_have_count(4)
    record('Sample CSV validates four applications with explicit image mapping')
    page.get_by_role('button',name='Start batch',exact=True).click()
    expect(page.get_by_text('4 / 4 finished')).to_be_visible(timeout=20000)
    expect(page.get_by_role('button',name='Review findings')).to_have_count(4)
    expect(page.get_by_text('4 completed · 0 failed · 0 stopped')).to_be_visible()
    record('Batch completes four real local API requests and exposes individual findings')
    page.wait_for_timeout(700)  # Finish Bootstrap's progress-width animation.
    page.screenshot(path=str(ROOT/'evidence/03-batch-results.png'),full_page=True)
    page.get_by_role('button',name='Review findings for WRONG-ABV',exact=True).click()
    expect(page.get_by_test_id('check-abv').locator('.result-badge')).to_have_text('!Review needed')
    record('Batch detail preserves the correct application-to-result association')
    page.get_by_role('button',name='Export batch CSV').click()
    csv = page.evaluate("async()=>await (await fetch(window.__downloads.at(-1).url)).text()")
    assert 'WRONG-ABV' in csv and 'IMPORT-001' in csv and 'warning' in csv.lower()
    record('Batch export includes every application and every check')

    # Validate a deliberately broken manifest; no AI request should be queued.
    page.locator('#batch-csv').set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':b'wrong,columns\nx,y\n'})
    page.get_by_role('button',name='Validate CSV & image mapping').click()
    expect(page.get_by_role('alert')).to_contain_text('template')
    expect(page.get_by_test_id('batch-row')).to_have_count(0)
    record('Malformed CSV is blocked without a partially accepted queue')

    if args.bridge:
        page.get_by_role('button',name='Load sample batch').click()
        expect(page.get_by_text('✓ 6 images selected')).to_be_visible()
        page.get_by_role('button',name='Validate CSV & image mapping').click()
        expect(page.get_by_test_id('batch-row')).to_have_count(4)
        page.evaluate('window.__delayVerify=700')
        page.get_by_role('button',name='Start batch',exact=True).click()
        page.get_by_role('button',name='Stop queue').click()
        expect(page.get_by_role('button',name='Retry unfinished')).to_be_visible(timeout=10000)
        expect(page.get_by_text('4 / 4 finished')).to_be_visible()
        record('Queue stop preserves outcomes and offers retry without new scheduling')
        page.evaluate('window.__delayVerify=0;window.__failNextVerify=true')
        page.get_by_role('button',name='Retry unfinished').click()
        expect(page.get_by_text('3 completed · 1 failed · 0 stopped')).to_be_visible(timeout=20000)
        record('A simulated one-row timeout does not stop other batch applications')
        page.get_by_role('button',name='Retry unfinished').click()
        expect(page.get_by_text('4 completed · 0 failed · 0 stopped')).to_be_visible(timeout=20000)
        record('Retry targets only unfinished rows and completes the queue')

    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name='Individual application').click()
    expect(page.get_by_role('button',name='Load sample',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
    page.screenshot(path=str(ROOT/'evidence/04-mobile-form.png'),full_page=True)
    record('390-pixel mobile layout fits viewport; wide results tables scroll locally')
    assert not browser_errors, browser_errors
    record('No uncaught browser JavaScript exceptions')
    browser.close()

report={'status':'passed','checks':len(checks),'check_names':checks,'browser_errors':browser_errors,'mode':'in-memory React source + real localhost API bridge' if args.bridge else 'standard HTTP browser','live_ai_tested':False,'public_deployment_tested':False}
(ROOT/'evidence/browser-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
