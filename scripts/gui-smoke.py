#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


def normalize_worker(raw: dict) -> dict:
    worker = json.loads(json.dumps(raw))
    if not worker.get("brain_chain"):
        chain = []
        if worker.get("larva"):
            chain.append({
                "id": "worm",
                "kind": "worm_link",
                "engine": worker["larva"]["engine"],
                "enabled": worker["larva"].get("enabled", True),
                "state_size": worker["larva"].get("state_size"),
                "connectome_pack": worker["larva"].get("config", {}).get("pack_id"),
                "input_from": [],
                "output_name": None,
                "config": worker["larva"].get("config", {}),
            })
        if worker.get("bee"):
            chain.append({
                "id": "fly",
                "kind": "fly_core",
                "engine": worker["bee"]["engine"],
                "enabled": worker["bee"].get("enabled", True),
                "state_size": worker["bee"].get("state_size"),
                "connectome_pack": worker["bee"].get("config", {}).get("pack_id"),
                "input_from": ["worm"] if worker.get("larva", {}).get("enabled", True) else [],
                "output_name": None,
                "config": worker["bee"].get("config", {}),
            })
        worker["brain_chain"] = chain
    if not worker.get("bridges") and len(worker["brain_chain"]) >= 2:
        worker["bridges"] = [{
            "id": "worm-to-fly",
            "source": "worm",
            "target": "fly",
            "engine": "state_projection_v1",
            "enabled": True,
            "config": {"source_excerpt": 32, "target_count": 24, "gain": 1.0},
        }]
    worker.setdefault("outputs", {}).setdefault("recording_level", "trace")
    worker.setdefault("runtime", {}).setdefault("persist_brain_state", True)
    return worker


async def run(executable: str | None, screenshot: Path | None):
    html = (ROOT / "src/hive_connectome/static/index.html").read_text()
    css = (ROOT / "src/hive_connectome/static/style.css").read_text()
    js = (ROOT / "src/hive_connectome/static/app.js").read_text()
    workers = [normalize_worker(w) for w in json.loads((ROOT / "config/workers.default.json").read_text())["workers"]]
    packs = json.loads((ROOT / "config/connectomes.json").read_text())["packs"]
    for pack in packs:
        pack["installed"] = pack["id"] in {"worm-cook-2020", "fly-malecns-locomotor"}
        pack["file_status"] = []

    html = re.sub(r'<link rel="stylesheet" href="/static/style.css">', f"<style>{css}</style>", html)
    html = html.replace('<script src="/static/app.js"></script>', "")

    async with async_playwright() as pw:
        kwargs = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            kwargs["executable_path"] = executable
        browser = await pw.chromium.launch(**kwargs)
        page = await browser.new_page(viewport={"width": 1440, "height": 1200})
        console_errors = []
        page_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        await page.set_content(html, wait_until="domcontentloaded")
        fixtures = {"workers": workers, "packs": packs}
        await page.evaluate(
            """fx=>{
              window.__fx=fx;
              const planFor=id=>{
                const w=fx.workers.find(x=>x.id===id);
                const packById=Object.fromEntries(fx.packs.map(p=>[p.id,p]));
                const names={worm_link:'C. elegans',fly_core:'MaleCNS',synthetic:'Synthetic neural stage'};
                const engines={cook2019_connectome:'Cook full C. elegans',malecns_full_v1:'Full MaleCNS v1.0',malecns_locomotor:'MaleCNS locomotor control',synthetic:'Synthetic recurrent network'};
                return {
                  core_id:w.id,name:w.name,description:w.description,objective:w.experiment.objective,
                  stages:w.brain_chain.map(s=>({
                    id:s.id,name:names[s.kind]||s.id,kind:s.kind,engine:s.engine,engine_label:engines[s.engine]||s.engine,
                    enabled:s.enabled,input_from:s.input_from||[],pack_id:s.config?.pack_id||s.connectome_pack,
                    dataset_installed:Boolean(packById[s.config?.pack_id||s.connectome_pack]?.installed),
                    role:s.engine==='malecns_locomotor'?'control':(s.engine==='cook2019_connectome'||s.engine==='malecns_full_v1'?'primary':'experimental'),
                    details:s.state_size?[s.state_size+' neurons/state units']:[],config:s.config||{}
                  })),
                  bridges:(w.bridges||[]).map(b=>({...b,label:b.engine==='state_projection_v1'?'Neural state projection':b.engine})),
                  jev:{enabled:w.jev.enabled,provider:w.jev.provider,model:w.jev.model,configured:true,feedback_to_brain:w.jev.feedback_to_brain},
                  llm:{enabled:w.llm.enabled,provider:w.llm.provider,model:w.llm.model,activation:w.llm.activation,configured:true},
                  recording:w.outputs.recording_level||'trace',persist_state:w.runtime.persist_brain_state!==false,
                  warnings:[],is_primary_topology:w.id==='primary-full',primary_experiment_ready:false,
                  primary_blockers:['full MaleCNS dataset is not installed']
                };
              };
              window.fetch=async(url,opts={})=>{
                const u=new URL(url,'http://hive.local');
                const p=u.pathname;
                let body,status=200;
                if(p==='/api/health') body={ok:true,version:'0.7.0',venice_configured:true,lmstudio_model:'tiny',workers:fx.workers.map(w=>w.id),neural_runtime:{primary_experiment_ready:false,study_mode:'CONTROL_ONLY',primary:{blockers:['full MaleCNS dataset is not installed']},control_runtime:{ready:true,backend:'cook2019_connectome → malecns_locomotor'}}};
                else if(p==='/api/workers'&&(!opts.method||opts.method==='GET')) body=fx.workers;
                else if(p.startsWith('/api/experiments/')&&p.endsWith('/plan')) body=planFor(decodeURIComponent(p.split('/')[3]));
                else if(p==='/api/providers/config') body={venice_base_url:'https://api.venice.ai/api/v1',venice_decision_model:'jev-latest',venice_api_key_configured:true,lmstudio_base_url:'http://host.docker.internal:1234/v1',lmstudio_api_token_configured:false,default_llm_model:'tiny'};
                else if(p==='/api/providers/status') body={venice:{configured:true,ok:true,base_url:'https://api.venice.ai/api/v1',model:'jev-latest'},lmstudio:{ok:true,base_url:'http://host.docker.internal:1234/v1',models:[{id:'tiny'}]}};
                else if(p==='/api/connectomes') body=fx.packs;
                else if(p==='/api/runs') body=[];
                else if(p==='/api/pipeline/reset') body={ok:true};
                else if(p==='/api/pipeline/run') body={
                  run_id:'run-smoke-1',
                  event:{timestamp:new Date().toISOString(),payload:{text:'test signal'}},
                  stages:{
                    worm:{brain_kind:'worm_link',engine:'cook2019-corrected-connectome-graded-v1',step:1,state_vector:[.1,.2],metrics:{nodes:300,edges:2200,input_nodes:18,energy:.12,novelty:.02},metadata:{real_connectome_topology:true,node_count:300,edge_count:2200}},
                    fly:{brain_kind:'fly_core',engine:'malecns-v1-locomotor-lif-v1',step:1,state_vector:[0,.1],metrics:{nodes:1045,edges:17224,input_nodes:24,spikes:9,energy:.08,novelty:.01},metadata:{real_connectome_topology:true,node_count:1045,edge_count:17224,input_encoding:'explicit bridge stimulus'}}
                  },
                  worm:{engine:'cook2019-corrected-connectome-graded-v1'},
                  fly:{engine:'malecns-v1-locomotor-lif-v1'},
                  decisions:{provider:'venice',model:'jev-latest',answers:{route:{choice:'store'},meaningful_signal:{noul:.82},novelty:{score:1.2},llm_needed:{noul:.3}},transport:{call_id:'jev-smoke',http_status:200,latency_ms:42}},
                  llm:null,labels:['core:scout','jev:on','llm:on'],unresolved:[],modulation:.15,
                  execution:{study_role:'control_only',primary_experiment:false,core_id:'scout',bridges:[{id:'worm-to-fly',source:'worm',target:'fly',engine:'state_projection_v1',stimulus_count:24,source_step:1}],jev:{requested:true,called:true,provider:'venice',model:'jev-latest',call_id:'jev-smoke'},llm:{requested:true,called:false,provider:null,model:null}}
                };
                else if(p==='/api/evals/run') body={summary:{jev_off_llm_off:{mean_latency_ms:1,jev_calls:0,llm_calls:0,failures:0},jev_on_llm_off:{mean_latency_ms:2,jev_calls:1,llm_calls:0,failures:0},jev_off_llm_on:{mean_latency_ms:3,jev_calls:0,llm_calls:1,failures:0},jev_on_llm_on:{mean_latency_ms:4,jev_calls:1,llm_calls:1,failures:0}}};
                else if(p.startsWith('/api/workers/')&&opts.method==='PUT'){
                  body=JSON.parse(opts.body);
                  const idx=fx.workers.findIndex(w=>w.id===body.id);
                  if(idx>=0)fx.workers[idx]=body;
                }
                else if(p.includes('/install')) body={status:'queued'};
                else if(p.includes('/job')) body={status:'complete'};
                else {status=404;body={detail:'mock missing '+p};}
                return {ok:status<400,status,json:async()=>body,statusText:status===404?'Not Found':'OK'};
              };
            }""",
            fixtures,
        )

        await page.add_script_tag(content=js)
        await page.wait_for_function("document.getElementById('coreSelect').options.length > 0 && document.getElementById('pipelineBuilder').children.length > 0")
        assert "primary experiment is not ready" in (await page.locator("#systemTruthTitle").text_content()).lower()

        await page.select_option("#coreSelect", "scout")
        await page.dispatch_event("#coreSelect", "change")
        await page.wait_for_function("document.getElementById('coreName').textContent.includes('Scout')")
        assert "C. elegans" in await page.locator("#pipelineBuilder").text_content()
        assert "MaleCNS" in await page.locator("#pipelineBuilder").text_content()

        await page.fill("#runInput", "A repeated signal changed sharply.")
        await page.click('button:has-text("Run this Core")')
        await page.wait_for_function("document.getElementById('executionTrace').textContent.includes('JEV decision')")
        trace = await page.locator("#executionTrace").text_content()
        assert "C. elegans" in trace
        assert "MaleCNS" in trace
        assert "bridge" in trace.lower()
        assert "Recorded result" in trace

        await page.click('button:has-text("Run JEV/LLM 2 × 2")')
        await page.wait_for_function("document.getElementById('matrixHuman').textContent.includes('JEV on LLM on')")

        assert await page.locator("#connectomes").locator('button:has-text("Install")').count() >= 1
        assert not console_errors, console_errors
        assert not page_errors, page_errors
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot), full_page=True)
        print("GUI smoke: PASS")
        await browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable")
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    asyncio.run(run(args.executable, args.screenshot))


if __name__ == "__main__":
    main()
