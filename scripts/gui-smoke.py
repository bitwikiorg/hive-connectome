#!/usr/bin/env python3
from __future__ import annotations
import argparse, asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]

async def run(executable: str|None, screenshot: Path|None):
    html=(ROOT/'src/hive_connectome/static/index.html').read_text()
    css=(ROOT/'src/hive_connectome/static/style.css').read_text()
    js=(ROOT/'src/hive_connectome/static/app.js').read_text()
    workers=json.loads((ROOT/'config/workers.default.json').read_text())['workers']
    packs=json.loads((ROOT/'config/connectomes.json').read_text())['packs']
    for p in packs: p['installed']=False; p['file_status']=[]
    html=re.sub(r'<link rel="stylesheet" href="/static/style.css">',f'<style>{css}</style>',html)
    html=html.replace('<script src="/static/app.js"></script>','')
    async with async_playwright() as pw:
        kw={'headless':True,'args':['--no-sandbox']}
        if executable: kw['executable_path']=executable
        browser=await pw.chromium.launch(**kw)
        page=await browser.new_page(viewport={'width':1440,'height':1050})
        console_errors=[]; page_errors=[]
        page.on('console',lambda m: console_errors.append(m.text) if m.type=='error' else None)
        page.on('pageerror',lambda e: page_errors.append(str(e)))
        await page.set_content(html,wait_until='domcontentloaded')
        fixtures={'workers':workers,'packs':packs}
        await page.evaluate("""fx=>{window.__fx=fx;window.fetch=async(url,opts={})=>{const u=new URL(url,'http://hive.local');const p=u.pathname;let body,status=200;
          if(p==='/api/health')body={ok:true,version:'0.5.0',venice_configured:true,lmstudio_model:'tiny',neural_runtime:{backend:'cook2019_connectome -> malecns_locomotor',real_connectome_runtime_ready:true,larva:{installed:true},bee:{installed:true}}};
          else if(p==='/api/workers'&&(!opts.method||opts.method==='GET'))body=fx.workers;
          else if(p==='/api/connectomes')body=fx.packs;
          else if(p==='/api/sources')body=[{id:'local-inbox',name:'Local inbox',kind:'file_drop',enabled:true,interval_seconds:10}];
          else if(p==='/api/events')body=[];
          else if(p==='/api/providers/status')body={venice:{configured:true,ok:true},lmstudio:{ok:true,models:[{id:'tiny'}]}};
          else if(p==='/api/pipeline/run')body={worm:{engine:'cook2019-corrected-connectome-graded-v1'},fly:{engine:'malecns-v1-locomotor-lif-v1'},decisions:{provider:'venice',model:'jev-latest',answers:{route:{choice:'store'},meaningful_signal:{noul:.82},novelty:{score:1.2},llm_needed:{noul:.3}}},llm:null,labels:['worker:scout'],unresolved:[],execution:{larva:{engine:'cook2019-corrected-connectome-graded-v1',real_connectome_topology:true},bee:{engine:'malecns-v1-locomotor-lif-v1',real_connectome_topology:true},jev:{requested:true,called:true,provider:'venice',model:'jev-latest'},llm:{requested:true,called:false,provider:null,model:null}}};
          else if(p==='/api/evals/run')body={summary:{jev_off_llm_off:{mean_latency_ms:1,jev_calls:0,llm_calls:0,failures:0},jev_on_llm_off:{mean_latency_ms:2,jev_calls:1,llm_calls:0,failures:0},jev_off_llm_on:{mean_latency_ms:3,jev_calls:0,llm_calls:1,failures:0},jev_on_llm_on:{mean_latency_ms:4,jev_calls:1,llm_calls:1,failures:0}}};
          else if(p.startsWith('/api/workers/')&&opts.method==='PUT')body=JSON.parse(opts.body);
          else if(p.includes('/install'))body={status:'queued'};
          else if(p.includes('/job'))body={status:'complete'};
          else{status=404;body={detail:'mock missing '+p}};
          return{ok:status<400,status,json:async()=>body,statusText:status===404?'Not Found':'OK'};};}""",fixtures)
        await page.add_script_tag(content=js)
        await page.wait_for_function("document.getElementById('taskSelect').options.length > 3 && document.getElementById('workerSelect').options.length > 0")
        assert await page.locator('#realBrainStatus').text_content()=='READY — real topology'
        await page.click('button:has-text("Load example")')
        assert len(await page.locator('#runInput').input_value())>10
        await page.click('button:has-text("Run HIVE")')
        await page.wait_for_function("document.getElementById('humanResult').textContent.includes('What HIVE actually did')")
        text=await page.locator('#humanResult').text_content(); assert 'Real connectome topology executed: YES' in text; assert 'Jev LIVE call succeeded' in text
        await page.locator('details.advanced').evaluate('(el)=>el.open=true')
        await page.click('button:has-text("Run comparison")')
        await page.wait_for_function("document.getElementById('matrixHuman').textContent.includes('jev on llm on')")
        assert await page.locator('#connectomes').locator('button:has-text("Install verified pack")').count() >= 1
        assert not console_errors, console_errors
        assert not page_errors, page_errors
        if screenshot:
            screenshot.parent.mkdir(parents=True,exist_ok=True)
            await page.screenshot(path=str(screenshot),full_page=True)
        print('GUI smoke: PASS')
        await browser.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--executable');ap.add_argument('--screenshot',type=Path);a=ap.parse_args();asyncio.run(run(a.executable,a.screenshot))
if __name__=='__main__':main()
