const $=id=>document.getElementById(id);
const j=x=>JSON.stringify(x,null,2);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let workers=[], inputMode='text', lastResult=null;

const TASKS={
 understand:{title:'Understand new information',worker:'scout',jev:true,llm:true,help:'Development/control preset while the full MaleCNS primary engine is still being integrated. Jev makes bounded judgments; the configured LLM may add prose reasoning.',example:'Pool TVL fell 18% in the last hour while volume doubled. Price is mostly unchanged.'},
 sort:{title:'Sort / route an event',worker:'scout',jev:true,llm:false,help:'Fast keep / inspect / escalate / ignore classification. No prose model.',example:'A scheduled API poll returned the same value as the previous six polls.'},
 explain:{title:'Explain something with the configured LLM',worker:'scout',jev:false,llm:true,help:'Run the configured LLM without Jev so its contribution can be compared independently.',example:'Liquidity moved from pool A into pool B after a fee change. Explain what changed and what I should investigate.'},
 remember:{title:'Decide what is worth remembering',worker:'keeper',jev:true,llm:true,help:'Use the Keeper Core to test durable-state decisions.',example:'The project permanently changed its default API endpoint from provider A to provider B.'},
 audit:{title:'Check a claim against evidence',worker:'auditor',jev:true,llm:true,help:'Separate supported claims, contradictions, and missing evidence.',example:'Claim: the deployment is healthy. Evidence: the API health check passed, but the database migration check was never run.'},
 browser:{title:'Interpret browser evidence',worker:'browser',jev:true,llm:true,help:'Use supplied DOM/accessibility/OCR evidence. HIVE does not browse by itself yet.',example:'Page title: Releases. Visible text: v2.4.1 Latest, published today; v2.4.0 published last week.'},
 brain:{title:'Test the connectome neural layer',worker:'scout',jev:false,llm:false,help:'Run only the configured neural stages and explicit bridges. The default reduced MaleCNS stage remains CONTROL ONLY.',example:'Repeated signal A: 1, 1, 1, 1; then signal A changes to 5.'}
};

async function api(path,opts={}){
 const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
 const b=await r.json().catch(()=>({error:r.statusText}));
 if(!r.ok)throw new Error(b.detail||b.error||j(b));
 return b;
}
function task(){return TASKS[$('taskSelect').value]||TASKS.understand}
function selectedWorker(){return workers.find(w=>w.id===$('workerSelect').value)}

async function boot(){
 $('taskSelect').innerHTML=Object.entries(TASKS).map(([k,v])=>`<option value="${k}">${v.title}</option>`).join('');
 selectTask();
 await loadHealth();
 workers=await api('/api/workers');
 $('workerSelect').innerHTML=workers.map(w=>`<option value="${w.id}">${w.name} — ${esc(w.description||w.role)}</option>`).join('');
 loadWorkerForm();
 await Promise.all([loadConnectomes(),loadSources(),loadEventsHuman(),loadProviderConfig(),loadProviders()]);
}

function selectTask(){
 const t=task();
 $('taskHelp').innerHTML=`<b>${esc(t.title)}</b><br>${esc(t.help)}<br><span class="meta">Uses Core: ${esc(t.worker)} · Jev ${t.jev?'on':'off'} · LLM ${t.llm?'on':'off'}</span>`;
}
function loadExample(){$('runInput').value=task().example}
function setInputMode(mode){
 inputMode=mode;
 $('textModeBtn').classList.toggle('active',mode==='text');
 $('jsonModeBtn').classList.toggle('active',mode==='json');
 $('runInput').placeholder=mode==='text'?'Paste a note, event, claim, API result, or observation here…':'Paste a JSON object or array here…';
}
async function loadHealth(){
 try{
  const h=await api('/api/health'), n=h.neural_runtime||{};
  $('health').textContent='running'; $('health').className='pill ok';
  $('brainRuntime').textContent=(n.control_runtime&&n.control_runtime.backend)||n.backend||'unknown';
  $('realBrainStatus').textContent=n.primary_experiment_ready?'READY — full Cook → full MaleCNS':'BLOCKED — full MaleCNS engine missing';
  $('realBrainStatus').className=n.primary_experiment_ready?'good':'warn-text';
  $('jevStatus').textContent=h.venice_configured?'configured — test calls available':'not configured';
  $('llmStatus').textContent=h.lmstudio_model||'Core-specific provider/model';
 }catch(e){$('health').textContent='offline';$('health').className='pill bad'}
}
function makePayload(){
 const raw=$('runInput').value.trim();
 if(!raw)throw new Error('Enter something for HIVE to work on.');
 if(inputMode==='json')return JSON.parse(raw);
 return {text:raw,job:task().title};
}
function pct(v){const n=Number(v);return Number.isFinite(n)?`${Math.round(n*100)}%`:'—'}

function humanResult(r,t){
 const a=r.decisions?.answers||{}, ex=r.execution||{};
 const route=a.route?.choice||'—', meaningful=a.meaningful_signal?.noul, novelty=a.novelty?.score, need=a.llm_needed?.noul;
 const jev=ex.jev||{}, llm=ex.llm||{}, stages=ex.stages||{}, bridges=ex.bridges||[];
 const stageRows=Object.entries(stages).map(([id,s])=>`<li><b>${esc(id)}</b> — ${esc(s.engine||s.requested_engine)} · ${esc(s.kind||'brain')} · topology ${s.real_connectome_topology?'measured':'synthetic/other'} · inputs ${esc((s.input_from||[]).join(', ')||'event')}</li>`).join('');
 const bridgeRows=bridges.map(b=>`<li><b>${esc(b.source)} → ${esc(b.target)}</b> — ${esc(b.engine)} · ${esc(b.stimulus_count??0)} explicit stimulus channels</li>`).join('');
 const providerRows=[
  jev.requested?(jev.called?`Jev LIVE: ${jev.provider} / ${jev.model} · call ${jev.call_id||'receipt missing'}`:'Jev requested but no live call completed'):'Jev disabled',
  llm.requested?(llm.called?`LLM LIVE: ${llm.provider} / ${llm.model||'model'} · call ${llm.call_id||'receipt missing'}`:'LLM requested but no model call completed'):'LLM disabled'
 ];
 const unresolved=(r.unresolved||[]).map(x=>`<li>${esc(x)}</li>`).join('');
 return `<div class="eyebrow">RESULT</div><h2>${esc(t.title)}</h2>
 <div class="result-grid"><div class="metric"><span>Route</span><strong>${esc(route)}</strong></div><div class="metric"><span>Meaningful</span><strong>${pct(meaningful)}</strong></div><div class="metric"><span>LLM needed</span><strong>${pct(need)}</strong></div></div>
 <div class="truth-row truth-bad"><b>${ex.study_role==='control_only'?'CONTROL RESULT — NOT PRIMARY EXPERIMENT':'EXPERIMENT RESULT'}</b> · Core ${esc(ex.core_id||'unknown')} · run ${esc(r.run_id||'—')}</div>
 <p><b>Novelty score:</b> ${esc(novelty??'—')} · <b>Modulation:</b> ${esc(r.modulation??'—')}</p>
 ${r.llm?.text?`<h3>Interpretation</h3><div class="interpretation">${esc(r.llm.text)}</div>`:'<p class="meta">No prose LLM output was produced.</p>'}
 <h3>Neural stages actually executed</h3><ol class="trace">${stageRows||'<li>No neural stage was active.</li>'}</ol>
 <h3>Bridges actually executed</h3><ol class="trace">${bridgeRows||'<li>No inter-stage bridge was needed.</li>'}</ol>
 <h3>External calls</h3><ol class="trace">${providerRows.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>
 ${unresolved?`<h3>Unresolved</h3><ul>${unresolved}</ul>`:''}`;
}

async function runTask(){
 const t=task(); $('runStatus').textContent='running…';
 try{
  const payload=makePayload();
  const r=await api('/api/pipeline/run',{method:'POST',body:JSON.stringify({worker_id:t.worker,jev_enabled:t.jev,llm_enabled:t.llm,mode:'auto',event:{source_id:'gui',kind:'human_job',payload}})});
  lastResult=r; $('humanResult').className='result-shell'; $('humanResult').innerHTML=humanResult(r,t); $('rawRun').textContent=j(r); $('runStatus').textContent='complete';
  await loadEventsHuman();
 }catch(e){$('humanResult').className='result-shell';$('humanResult').innerHTML=`<div class="bad"><b>Run failed:</b> ${esc(e.message)}</div>`;$('runStatus').textContent='failed'}
}

async function loadConnectomes(){
 try{
  const packs=await api('/api/connectomes');
  $('connectomes').innerHTML=packs.map(p=>`<div class="pack"><div class="pack-row"><div><b>${esc(p.name)}</b><div class="meta">${p.installed?'INSTALLED + VERIFIED':(p.installable?'NOT INSTALLED':'reference only')} ${p.primary_required?'· PRIMARY REQUIRED':''} ${p.control_only?'· CONTROL ONLY':''}</div>${p.warning?`<div class="warn-text meta">${esc(p.warning)}</div>`:''}</div>${p.installable&&!p.installed?`<button class="secondary" onclick="installPack('${p.id}',${Boolean(p.warning)})">Install verified pack</button>`:''}</div></div>`).join('');
 }catch(e){$('connectomes').innerHTML=`<div class="bad">${esc(e.message)}</div>`}
}
async function installPack(id,large){
 if(!confirm(`Download and verify ${id}?${large?' This is a large dataset.':''}`))return;
 try{
  await api(`/api/connectomes/${encodeURIComponent(id)}/install?confirm=${large?'true':'false'}`,{method:'POST'});
  const start=Date.now();
  while(Date.now()-start<900000){
   const x=await api(`/api/connectomes/${encodeURIComponent(id)}/job`);
   if(x.status==='complete'||x.status==='error'){alert(x.status==='complete'?'Pack installed and verified. Installation alone does not prove execution.':`Install failed: ${x.error}`);break}
   await new Promise(r=>setTimeout(r,1200));
  }
  await loadConnectomes(); await loadHealth();
 }catch(e){alert(e.message)}
}
async function loadSources(){
 try{const s=await api('/api/sources');$('sources').innerHTML=s.length?s.map(x=>`<div class="event"><b>${esc(x.name||x.id)}</b><div class="meta">${esc(x.kind)} · ${x.enabled?'enabled':'disabled'} · every ${x.interval_seconds}s</div></div>`).join(''):'<div class="meta">No sources configured.</div>'}catch(e){$('sources').textContent=e.message}
}
async function loadEventsHuman(){
 try{const e=await api('/api/events?limit=8');$('eventsHuman').innerHTML=e.length?e.map(x=>`<div class="event"><b>${esc(x.kind)}</b> <span class="meta">${esc(x.source_id)} · ${esc(x.timestamp)}</span><div>${esc(typeof x.payload==='string'?x.payload:JSON.stringify(x.payload)).slice(0,220)}</div></div>`).join(''):'<div class="meta">No events yet.</div>'}catch(e){$('eventsHuman').textContent=e.message}
}

function toggleBrainStage(index,enabled){const w=selectedWorker();if(w?.brain_chain?.[index])w.brain_chain[index].enabled=enabled}
function setBridgeEngine(index,value){const w=selectedWorker();if(w?.bridges?.[index])w.bridges[index].engine=value}

function loadWorkerForm(){
 const w=selectedWorker(); if(!w)return;
 $('workerRole').value=w.role; $('workerDescription').textContent=w.description||'';
 $('runJev').checked=w.jev.enabled; $('runLlm').checked=w.llm.enabled;
 $('jevModel').value=w.jev.model||'jev-latest'; $('llmProvider').value=w.llm.provider||'lmstudio'; $('llmModel').value=w.llm.model||''; $('llmActivation').value=w.llm.activation||'jev_gate';
 $('recordingLevel').value=w.outputs?.recording_level||'trace';
 $('taskPrompt').value=w.experiment.task_prompt; $('jevQuestions').value=j(w.jev.questions||{});
 $('hiveChain').value=w.id;
 $('brainStages').innerHTML=(w.brain_chain||[]).map((s,i)=>`<div class="event"><label><input type="checkbox" ${s.enabled?'checked':''} onchange="toggleBrainStage(${i},this.checked)"> <b>${esc(s.id)}</b></label><div class="meta">${esc(s.kind)} · engine ${esc(s.engine)} · input from ${esc((s.input_from||[]).join(', ')||'event')} · pack ${esc(s.connectome_pack||s.config?.pack_id||'none')}</div></div>`).join('')||'<div class="meta">No neural stages configured. This Core can still use Jev/LLM.</div>';
 $('bridges').innerHTML=(w.bridges||[]).map((b,i)=>`<div class="event"><b>${esc(b.source)} → ${esc(b.target)}</b><div class="formgrid"><label>Bridge engine<select onchange="setBridgeEngine(${i},this.value)"><option value="state_projection_v1" ${b.engine==='state_projection_v1'?'selected':''}>state projection</option><option value="hash_projection_v1" ${b.engine==='hash_projection_v1'?'selected':''}>hash projection control</option><option value="identity_payload_v1" ${b.engine==='identity_payload_v1'?'selected':''}>identity payload</option></select></label><label>Config<input value="${esc(JSON.stringify(b.config||{}))}" readonly></label></div></div>`).join('')||'<div class="meta">No inter-stage bridges.</div>';
}

async function saveAdvancedWorker(){
 const w=selectedWorker(); if(!w)return;
 try{
  w.experiment.task_prompt=$('taskPrompt').value;
  w.jev.questions=JSON.parse($('jevQuestions').value||'{}');
  w.jev.enabled=$('runJev').checked; w.jev.model=$('jevModel').value.trim()||'jev-latest';
  w.llm.enabled=$('runLlm').checked; w.llm.provider=$('llmProvider').value; w.llm.model=$('llmModel').value.trim()||null; w.llm.activation=$('llmActivation').value;
  w.outputs.recording_level=$('recordingLevel').value;
  const saved=await api(`/api/workers/${encodeURIComponent(w.id)}`,{method:'PUT',body:JSON.stringify(w)});
  const i=workers.findIndex(x=>x.id===w.id); workers[i]=saved; loadWorkerForm(); alert('Core saved.');
 }catch(e){alert(e.message)}
}

async function runHiveChain(){
 try{
  const coreIds=$('hiveChain').value.split(',').map(x=>x.trim()).filter(Boolean);
  if(!coreIds.length)throw new Error('Enter at least one Core ID.');
  const payload=makePayload();
  const x=await api('/api/hive/run',{method:'POST',body:JSON.stringify({core_ids:coreIds,mode:'auto',event:{source_id:'gui:hive',kind:'human_job',payload}})});
  $('hiveResult').innerHTML=x.results.map((r,i)=>`<div class="subcard"><div class="eyebrow">CORE ${i+1}: ${esc(coreIds[i])}</div>${humanResult(r,{title:coreIds[i]})}</div>`).join('');
  if(x.results.length){lastResult=x.results[x.results.length-1];$('rawRun').textContent=j(x)}
 }catch(e){$('hiveResult').innerHTML=`<div class="bad">${esc(e.message)}</div>`}
}

function downloadExperiment(all=false){
 const w=selectedWorker();
 const query=all?'':`?worker_id=${encodeURIComponent(w?.id||'')}`;
 window.location.assign('/api/exports/experiment'+query);
}

async function runMatrix(){
 const w=selectedWorker();if(!w)return;
 try{
  const payload=makePayload();
  const x=await api('/api/evals/run',{method:'POST',body:JSON.stringify({worker_id:w.id,cases:[{id:'gui',event:{source_id:'eval',kind:'eval',payload}}]})});
  $('matrixHuman').innerHTML=Object.entries(x.summary||{}).map(([k,v])=>`<div class="event"><b>${esc(k.replaceAll('_',' '))}</b><div class="meta">latency ${Math.round(v.mean_latency_ms||0)} ms · Jev calls ${v.jev_calls} · LLM calls ${v.llm_calls} · failures ${v.failures}</div></div>`).join('');
 }catch(e){$('matrixHuman').innerHTML=`<div class="bad">${esc(e.message)}</div>`}
}
async function loadProviderConfig(){
 try{
  const x=await api('/api/providers/config');
  $('veniceBaseUrl').value=x.venice_base_url||'';
  $('veniceDefaultJevModel').value=x.venice_decision_model||'jev-latest';
  $('lmstudioBaseUrl').value=x.lmstudio_base_url||'';
  $('defaultLlmModel').value=x.default_llm_model||'';
  $('providerConfigState').textContent=`Venice key: ${x.venice_api_key_configured?'configured':'missing'} · LM Studio token: ${x.lmstudio_api_token_configured?'configured':'not set'}`;
 }catch(e){$('providerConfigState').textContent=e.message}
}

async function saveProviderConfig(){
 try{
  const payload={
   venice_base_url:$('veniceBaseUrl').value.trim(),
   venice_decision_model:$('veniceDefaultJevModel').value.trim()||'jev-latest',
   lmstudio_base_url:$('lmstudioBaseUrl').value.trim(),
   default_llm_model:$('defaultLlmModel').value.trim()||null,
   clear_default_llm_model:!$('defaultLlmModel').value.trim(),
  };
  if($('veniceApiKey').value)payload.venice_api_key=$('veniceApiKey').value;
  if($('lmstudioApiToken').value)payload.lmstudio_api_token=$('lmstudioApiToken').value;
  const x=await api('/api/providers/config',{method:'PUT',body:JSON.stringify(payload)});
  $('veniceApiKey').value=''; $('lmstudioApiToken').value='';
  $('providerConfigState').textContent=`Saved · Venice key: ${x.venice_api_key_configured?'configured':'missing'} · LM Studio token: ${x.lmstudio_api_token_configured?'configured':'not set'}`;
  await loadHealth(); await loadProviders();
 }catch(e){$('providerConfigState').textContent=`Save failed: ${e.message}`}
}

async function testProvider(capability){
 try{
  let model=null;
  if(capability==='venice_jev')model=$('jevModel').value.trim()||$('veniceDefaultJevModel').value.trim();
  if(capability==='venice_chat')model=$('llmProvider').value==='venice'?$('llmModel').value.trim():$('llmModel').value.trim();
  if(capability==='lmstudio_chat')model=$('llmProvider').value==='lmstudio'?$('llmModel').value.trim():$('defaultLlmModel').value.trim();
  const x=await api('/api/providers/test',{method:'POST',body:JSON.stringify({capability,model:model||null})});
  $('providers').textContent=`REAL CALL SUCCEEDED
capability: ${capability}
model: ${x.model||'—'}
call id: ${x.transport?.call_id||'—'}
HTTP: ${x.transport?.http_status||'—'}
latency: ${Math.round(x.transport?.latency_ms||0)} ms
request hash: ${x.transport?.request_hash||'—'}
response hash: ${x.transport?.response_hash||'—'}

${j(x)}`;
 }catch(e){$('providers').textContent=`REAL CALL FAILED
${e.message}`}
}

async function loadProviders(){
 try{
  const x=await api('/api/providers/status');
  const lines=[
   `Venice: ${x.venice?.configured?(x.venice.ok?'reachable':'configured but failing'):'not configured'} · decision model ${x.venice?.model||'—'}`,
   `LM Studio: ${x.lmstudio?.ok?'reachable':'unreachable'} · ${x.lmstudio?.base_url||'—'}`,
   '',
   'Connection/status check only. Use a real-call button above to prove inference.',
   '',
   'Raw diagnostics:',
   j(x)
  ];
  $('providers').textContent=lines.join('\\n');
 }catch(e){$('providers').textContent=e.message}
}
boot().catch(e=>{console.error(e);$('health').textContent='startup error';$('health').className='pill bad'});
