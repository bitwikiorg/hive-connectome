from __future__ import annotations
import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import BackgroundTasks,FastAPI,HTTPException,Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from hive_connectome.connectomes.installer import ConnectomeInstaller
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.providers.venice import VeniceJev
from hive_connectome.scheduler import HeartbeatDaemon
from hive_connectome.schemas import CronTaskSpec,DataSourceSpec,PipelineRequest,SimulationSpec
from hive_connectome.settings import Settings
from hive_connectome.sources import poll_source

settings=Settings.from_env();settings.data_dir.mkdir(parents=True,exist_ok=True);(settings.data_dir/"inbox").mkdir(parents=True,exist_ok=True)
db=HiveDB(settings.data_dir/"hive.sqlite3")
venice=VeniceJev(settings.venice_base_url,settings.venice_api_key,settings.venice_decision_model) if settings.venice_api_key else None
lmstudio=LMStudio(settings.lmstudio_base_url,settings.lmstudio_api_token)
pipeline=HivePipeline(db,venice=venice,lmstudio=lmstudio,llm_model=settings.llm_model)
installer=ConnectomeInstaller(settings.config_dir/"connectomes.json",settings.data_dir);heartbeat=HeartbeatDaemon(db,pipeline,settings.data_dir/"inbox");install_jobs={}

def seed_sources():
    example=settings.config_dir/"sources.example.json"
    if not db.list_sources() and example.exists():
        for item in json.loads(example.read_text(encoding="utf-8"))["sources"]:db.upsert_source(DataSourceSpec.model_validate(item).model_dump())

@asynccontextmanager
async def lifespan(app:FastAPI):
    seed_sources();heartbeat.start();yield;await heartbeat.stop()

app=FastAPI(title="HIVE Connectome",version="0.1.0",lifespan=lifespan);static_dir=Path(__file__).parent/"static";app.mount("/static",StaticFiles(directory=static_dir),name="static")
@app.get("/")
async def root():return FileResponse(static_dir/"index.html")
@app.get("/api/health")
async def health():return {"ok":True,"version":"0.1.0","venice_configured":venice is not None,"lmstudio_model":settings.llm_model}
@app.get("/api/providers/status")
async def provider_status():
    result={"venice":{"configured":venice is not None,"ok":False,"model":settings.venice_decision_model},"lmstudio":{"configured":True,"ok":False,"base_url":settings.lmstudio_base_url,"models":[]}}
    if venice:
        try:result["venice"]["models"]=await venice.list_models();result["venice"]["ok"]=True
        except Exception as e:result["venice"]["error"]=str(e)
    try:
        models=await lmstudio.list_models();result["lmstudio"]["ok"]=True;result["lmstudio"]["models"]=models.get("data",models)
    except Exception as e:result["lmstudio"]["error"]=str(e)
    return result
@app.get("/api/connectomes")
async def connectomes():return installer.list_status()
async def _install(pack_id):
    install_jobs[pack_id]={"status":"running"}
    try:install_jobs[pack_id]={"status":"complete","receipt":await installer.install(pack_id)}
    except Exception as e:install_jobs[pack_id]={"status":"error","error":str(e)}
@app.post("/api/connectomes/{pack_id}/install")
async def install_connectome(pack_id:str,background_tasks:BackgroundTasks,confirm:bool=Query(False)):
    try:pack=installer.get_pack(pack_id)
    except KeyError:raise HTTPException(404,"unknown connectome pack")
    if not pack.get("installable"):raise HTTPException(400,pack.get("reason","not installable"))
    total=sum(int(f.get("bytes") or 0) for f in pack.get("files",[]))
    if total>100*1024*1024 and not confirm:raise HTTPException(409,f"large download ({total} bytes); resend with confirm=true")
    if install_jobs.get(pack_id,{}).get("status")=="running":return install_jobs[pack_id]
    background_tasks.add_task(_install,pack_id);return {"status":"queued","pack_id":pack_id}
@app.get("/api/connectomes/{pack_id}/job")
async def connectome_job(pack_id:str):return install_jobs.get(pack_id,{"status":"idle"})
@app.post("/api/pipeline/run")
async def run_pipeline(req:PipelineRequest):
    try:return await pipeline.run(req)
    except Exception as e:raise HTTPException(502,str(e))
@app.post("/api/pipeline/reset")
async def reset_pipeline():pipeline.reset();return {"ok":True}
@app.get("/api/events")
async def events(limit:int=Query(50,ge=1,le=500)):return db.list_events(limit)
@app.get("/api/sources")
async def list_sources():return db.list_sources()
@app.post("/api/sources")
async def add_source(spec:DataSourceSpec):db.upsert_source(spec.model_dump());return {"ok":True,"source":spec}
@app.post("/api/sources/{source_id}/poll")
async def poll_one(source_id:str):
    raw=next((x for x in db.list_sources() if x["id"]==source_id),None)
    if not raw:raise HTTPException(404,"source not found")
    spec=DataSourceSpec.model_validate({k:v for k,v in raw.items() if not k.startswith("_")})
    try:return await poll_source(spec,settings.data_dir/"inbox")
    except Exception as e:raise HTTPException(400,str(e))
@app.get("/api/tasks")
async def list_tasks():return db.list_tasks()
@app.post("/api/tasks")
async def add_task(spec:CronTaskSpec):
    from croniter import croniter
    if not croniter.is_valid(spec.cron):raise HTTPException(400,"invalid cron expression")
    db.upsert_task(spec.model_dump());return {"ok":True,"task":spec}
@app.post("/api/simulate")
async def simulate(spec:SimulationSpec):
    if spec.reset_brains:pipeline.reset()
    results=[]
    for event in spec.events:results.append(await pipeline.run(PipelineRequest(event=event,mode=spec.mode)))
    return {"name":spec.name,"count":len(results),"results":results}
