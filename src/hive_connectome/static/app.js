const j=x=>JSON.stringify(x,null,2);
let workers=[], templates=[];

async function api(path,opts={}){
  const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  const body=await r.json().catch(()=>({error:r.statusText}));
  if(!r.ok) throw new Error(body.detail||body.error||j(body));
  return body;
}
const $=id=>document.getElementById(id);
const csv=x=>x.split(',').map(s=>s.trim()).filter(Boolean);
const bool=id=>$(id).checked;
const num=id=>Number($(id).value||0);

function selectedWorker(){
  return workers.find(w=>w.id===$('workerSelect').value);
}

async function boot(){
  await loadHealth();
  const t=await api('/api/experiment-templates');templates=t.templates||[];
  $('templateSelect').innerHTML=templates.map(x=>`<option value="${x.id}">${x.name}</option>`).join('');
  await refreshWorkers();
  await loadConnectomes();
}

async function loadHealth(){
  try{
    await api('/api/health');
    $('health').textContent='healthy';$('health').className='pill ok';
  }catch(e){
    $('health').textContent='offline';$('health').className='pill bad';
  }
}

async function refreshWorkers(selectId=null){
  const old=selectId||$('workerSelect').value;
  workers=await api('/api/workers');
  $('workerSelect').innerHTML=workers.map(w=>`<option value="${w.id}">${w.name} · ${w.id}</option>`).join('');
  if(old && workers.some(w=>w.id===old)) {
    $('workerSelect').value=old;
  } else if(workers.length) {
    $('workerSelect').value=workers[0].id;
  }
  loadWorkerForm();
}

function renderDataEnvironment(){
  const mode=$('dataMode').value;
  for(const id of ['envSources','envBrowser','envFiles','envWorkers']) $(id).style.display='none';
  if(mode==='source_ids') $('envSources').style.display='block';
  if(mode==='browser_dom'||mode==='browser_visual') $('envBrowser').style.display='block';
  if(mode==='file_drop') $('envFiles').style.display='block';
  if(mode==='worker_output') $('envWorkers').style.display='block';

  const labels={
    manual:'Experiment input (JSON)',
    source_ids:'Optional eval/sample input (JSON); environment run uses configured sources',
    browser_dom:'Optional eval/sample DOM evidence (JSON); environment run awaits browser adapter',
    browser_visual:'Optional eval/sample OCR/visual evidence (JSON); environment run awaits browser adapter',
    file_drop:'Optional eval/sample file evidence (JSON); environment run reads inbox',
    simulation:'Simulation event (JSON)',
    worker_output:'Optional eval/sample upstream worker output (JSON)'
  };
  $('inputLabel').childNodes[0].nodeValue=(labels[mode]||'Experiment input (JSON)')+' ';
}

function loadWorkerForm(){
  const w=selectedWorker();if(!w)return;
  $('workerIdLabel').textContent=`worker id: ${w.id}`;
  $('workerName').value=w.name;
  $('workerRole').value=w.role;
  $('workerDescription').value=w.description||'';

  $('jevEnabled').checked=w.jev.enabled;
  $('llmEnabled').checked=w.llm.enabled;
  $('runJev').checked=w.jev.enabled;
  $('runLlm').checked=w.llm.enabled;

  $('experimentKind').value=w.experiment.kind;
  $('experimentObjective').value=w.experiment.objective;
  $('taskPrompt').value=w.experiment.task_prompt;
  $('expectedOutput').value=w.experiment.expected_output;
  $('evalMetric').value=w.experiment.eval_metric;
  $('experimentNotes').value=w.experiment.notes||'';

  $('dataMode').value=w.data_environment.mode;
  $('sourceIds').value=(w.data_environment.source_ids||[]).join(', ');
  $('browserUrl').value=w.data_environment.url||'';
  $('filePath').value=w.data_environment.file_path||'';
  $('pollInterval').value=w.data_environment.poll_interval_seconds;
  $('alwaysOn').checked=w.data_environment.always_on;
  $('browserExtract').value=w.data_environment.browser_extract;
  $('ocrEnabled').checked=w.data_environment.ocr_enabled;
  $('upstreamWorkers').value=(w.data_environment.upstream_workers||[]).join(', ');
  renderDataEnvironment();

  $('larvaEngine').value=w.larva.engine;
  $('larvaSubstrate').value=w.larva.substrate;
  $('larvaSize').value=w.larva.state_size;
  $('larvaConfig').value=j(w.larva.config||{});
  $('beeEngine').value=w.bee.engine;
  $('beeSubstrate').value=w.bee.substrate;
  $('beeSize').value=w.bee.state_size;
  $('beeConfig').value=j(w.bee.config||{});

  $('jevModel').value=w.jev.model;
  $('jevThreshold').value=w.jev.llm_gate_threshold;
  $('jevFeedback').checked=w.jev.feedback_to_brain;
  $('jevQuestions').value=j(w.jev.questions||{});

  $('llmProvider').value=w.llm.provider;
  $('llmModel').value=w.llm.model||'';
  $('llmActivation').value=w.llm.activation;
  $('llmTemperature').value=w.llm.temperature;
  $('verifyWithJev').checked=w.llm.verify_with_jev;
  $('llmPrompt').value=w.llm.prompt||'';

  $('runtimeEnabled').checked=Boolean(w.runtime.enabled);
  $('runtimeMode').value=w.runtime.mode;
  $('runtimeInterval').value=w.runtime.interval_seconds;
  $('runtimeCron').value=w.runtime.cron||'';
  $('persistBrain').checked=w.runtime.persist_brain_state;
  $('maxEvents').value=w.runtime.max_events_per_tick;

  $('saveEvent').checked=w.outputs.save_event;
  $('saveRun').checked=w.outputs.save_run;
  $('writeLabels').checked=w.outputs.write_labels;
  $('emitHivemind').checked=w.outputs.emit_to_hivemind;
  $('nextWorkers').value=(w.outputs.next_workers||[]).join(', ');
}

function formToWorker(){
  const old=selectedWorker();
  return {
    id:old.id,
    name:$('workerName').value,
    description:$('workerDescription').value,
    role:$('workerRole').value,
    experiment:{
      kind:$('experimentKind').value,
      objective:$('experimentObjective').value,
      task_prompt:$('taskPrompt').value,
      expected_output:$('expectedOutput').value,
      eval_metric:$('evalMetric').value,
      notes:$('experimentNotes').value
    },
    data_environment:{
      mode:$('dataMode').value,
      source_ids:csv($('sourceIds').value),
      url:$('browserUrl').value||null,
      file_path:$('filePath').value||null,
      poll_interval_seconds:num('pollInterval')||60,
      always_on:bool('alwaysOn'),
      browser_extract:$('browserExtract').value,
      ocr_enabled:bool('ocrEnabled'),
      upstream_workers:csv($('upstreamWorkers').value)
    },
    larva:{
      engine:$('larvaEngine').value,
      substrate:$('larvaSubstrate').value,
      state_size:num('larvaSize'),
      config:JSON.parse($('larvaConfig').value||'{}')
    },
    bee:{
      engine:$('beeEngine').value,
      substrate:$('beeSubstrate').value,
      state_size:num('beeSize'),
      config:JSON.parse($('beeConfig').value||'{}')
    },
    jev:{
      enabled:bool('jevEnabled'),
      provider:'venice',
      model:$('jevModel').value,
      questions:JSON.parse($('jevQuestions').value||'{}'),
      llm_gate_threshold:Number($('jevThreshold').value),
      feedback_to_brain:bool('jevFeedback')
    },
    llm:{
      enabled:bool('llmEnabled'),
      provider:$('llmProvider').value,
      model:$('llmModel').value||null,
      activation:$('llmActivation').value,
      prompt:$('llmPrompt').value,
      temperature:Number($('llmTemperature').value),
      verify_with_jev:bool('verifyWithJev')
    },
    runtime:{
      enabled:bool('runtimeEnabled'),
      mode:$('runtimeMode').value,
      interval_seconds:num('runtimeInterval')||60,
      cron:$('runtimeCron').value||null,
      persist_brain_state:bool('persistBrain'),
      max_events_per_tick:num('maxEvents')||25
    },
    outputs:{
      save_event:bool('saveEvent'),
      save_run:bool('saveRun'),
      write_labels:bool('writeLabels'),
      emit_to_hivemind:bool('emitHivemind'),
      next_workers:csv($('nextWorkers').value)
    }
  };
}

async function saveWorker(){
  try{
    const w=formToWorker();
    await api('/api/workers/'+encodeURIComponent(w.id),{method:'PUT',body:JSON.stringify(w)});
    await refreshWorkers(w.id);
    alert('worker saved');
  }catch(e){alert(e.message)}
}

async function createWorker(){
  const id=$('newWorkerId').value.trim();
  if(!id)return alert('enter worker id');
  const q=new URLSearchParams({worker_id:id});
  if($('newWorkerName').value.trim())q.set('name',$('newWorkerName').value.trim());
  try{
    const w=await api('/api/workers/from-template/'+encodeURIComponent($('templateSelect').value)+'?'+q.toString(),{method:'POST'});
    await refreshWorkers(w.id);
  }catch(e){alert(e.message)}
}

async function cloneWorker(){
  const old=selectedWorker();const id=$('cloneWorkerId').value.trim();
  if(!old||!id)return alert('select a worker and enter new id');
  try{
    const w=await api(`/api/workers/${encodeURIComponent(old.id)}/clone?new_id=${encodeURIComponent(id)}`,{method:'POST'});
    await refreshWorkers(w.id);
  }catch(e){alert(e.message)}
}

async function deleteWorker(){
  const w=selectedWorker();if(!w)return;
  if(!confirm(`Delete ${w.id}?`))return;
  try{await api('/api/workers/'+encodeURIComponent(w.id),{method:'DELETE'});await refreshWorkers()}
  catch(e){alert(e.message)}
}

async function runWorker(){
  const w=selectedWorker();if(!w)return;
  $('runResult').textContent='running...';
  try{
    const payload=JSON.parse($('runPayload').value);
    const x=await api('/api/pipeline/run',{method:'POST',body:JSON.stringify({
      worker_id:w.id,
      jev_enabled:bool('runJev'),
      llm_enabled:bool('runLlm'),
      mode:'auto',
      event:{source_id:'gui',kind:'experiment',payload}
    })});
    $('runResult').textContent=j(x);
  }catch(e){$('runResult').textContent=e.message}
}

async function resetWorker(){
  const w=selectedWorker();if(!w)return;
  try{await api('/api/pipeline/reset?worker_id='+encodeURIComponent(w.id),{method:'POST'});$('runResult').textContent='paired neural state reset'}
  catch(e){$('runResult').textContent=e.message}
}

async function runEnvironment(){
  const w=selectedWorker();if(!w)return;
  $('environmentResult').textContent='running environment...';
  try{
    $('environmentResult').textContent=j(await api(`/api/workers/${encodeURIComponent(w.id)}/run-environment`,{method:'POST'}));
  }catch(e){$('environmentResult').textContent=e.message}
}

async function runEval(){
  const w=selectedWorker();if(!w)return;
  $('evalResult').textContent='running same worker across four toggle states...';
  try{
    const payload=JSON.parse($('runPayload').value);
    const expected=$('expectedRoute').value||null;
    const x=await api('/api/evals/run',{method:'POST',body:JSON.stringify({
      worker_id:w.id,
      cases:[{id:'gui-eval',event:{source_id:'eval',kind:'eval',payload},expected_route:expected}]
    })});
    $('evalResult').textContent=j(x);
  }catch(e){$('evalResult').textContent=e.message}
}

async function loadProviders(){
  $('providers').textContent='testing...';
  try{$('providers').textContent=j(await api('/api/providers/status'))}
  catch(e){$('providers').textContent=e.message}
}

async function loadConnectomes(){
  try{
    const packs=await api('/api/connectomes');
    $('connectomes').innerHTML=packs.map(p=>`<div class="pack">
      <b>${p.name}</b>
      <div class="meta">${p.installed?'installed + verified':(p.installable?'available':'research reference')}</div>
      ${p.warning?`<div class="warn">${p.warning}</div>`:''}
      ${p.installable&&!p.installed?`<button class="secondary" onclick="installConnectome('${p.id}', ${JSON.stringify(Boolean(p.warning))})">Install</button>`:''}
    </div>`).join('');
  }catch(e){$('connectomes').textContent=e.message}
}

async function installConnectome(id,isLarge){
  if(!confirm(`Install ${id}?${isLarge?' This pack is large and can exceed 1 GB.':''}`))return;
  try{
    const result=await api(`/api/connectomes/${encodeURIComponent(id)}/install?confirm=${isLarge?'true':'false'}`,{method:'POST'});
    $('connectomes').insertAdjacentHTML('afterbegin',`<div class="meta">${j(result)}</div>`);
    setTimeout(loadConnectomes,1200);
  }catch(e){alert(e.message)}
}

boot().catch(e=>{
  $('health').textContent='startup error';$('health').className='pill bad';
  console.error(e);
});
