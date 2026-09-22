const $=id=>document.getElementById(id);
const pretty=value=>JSON.stringify(value,null,2);
const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const architectureArray=value=>Array.isArray(value)?value:String(value||'').split(',').map(tag=>tag.trim()).filter(Boolean);

let cores=[];
let currentCore=null;
let currentPlan=null;
let healthState=null;
let providerState=null;
let inputMode='text';
let dirty=false;

async function api(path,opts={}){
  const response=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  const body=await response.json().catch(()=>({detail:response.statusText}));
  if(!response.ok) throw new Error(body.detail||body.error||pretty(body));
  return body;
}

function shortId(value){
  const s=String(value||'');
  return s.length>16?s.slice(0,8)+'…'+s.slice(-5):s;
}

function formatNumber(value){
  const n=Number(value);
  if(!Number.isFinite(n)) return '—';
  if(Math.abs(n)>=1000) return n.toLocaleString();
  if(Math.abs(n)<0.001 && n!==0) return n.toExponential(2);
  return Number.isInteger(n)?String(n):n.toFixed(4).replace(/0+$/,'').replace(/\.$/,'');
}

function formatPercent(value){
  const n=Number(value);
  return Number.isFinite(n)?Math.round(n*100)+'%':'—';
}

function setDirty(value=true){
  dirty=value;
  $('saveState').textContent=value?'Unsaved configuration changes. Run will save them first.':'Configuration matches backend.';
}

async function boot(){
  await refreshAll();
}

async function refreshAll(){
  $('health').textContent='connecting…';
  $('health').className='pill neutral';
  try{
    const [health,workers]=await Promise.all([api('/api/health'),api('/api/workers')]);
    healthState=health;
    cores=workers;
    $('health').textContent='HIVE running · v'+health.version;
    $('health').className='pill ok';
    renderSystemTruth();
    renderCoreSelect();
    await Promise.all([loadProviderConfig(),loadConnectomes()]);
    await selectCore(true);
    loadProviders();
  }catch(error){
    $('health').textContent='HIVE unavailable';
    $('health').className='pill bad';
    $('systemTruthTitle').textContent='Cannot read the HIVE backend';
    $('systemTruthText').textContent=error.message;
    $('primaryStatus').textContent='OFFLINE';
    $('primaryStatus').className='truth-badge blocked';
  }
}

function renderSystemTruth(){
  const runtime=healthState?.neural_runtime||{};
  const ready=Boolean(runtime.primary_experiment_ready);
  const blockers=runtime.primary?.blockers||[];
  $('primaryStatus').textContent=ready?'PRIMARY READY':'PRIMARY BLOCKED';
  $('primaryStatus').className='truth-badge '+(ready?'ready':'blocked');
  if(ready){
    $('systemTruthTitle').textContent='Full Cook → full MaleCNS has executed successfully';
    $('systemTruthText').textContent='The target machine has valid execution receipts for the required full biological substrates. You can now run and compare experimental configurations.';
  }else{
    $('systemTruthTitle').textContent='The primary full-connectome experiment is not ready yet';
    $('systemTruthText').textContent=blockers.length?blockers.join(' · '):'HIVE has not yet produced the execution receipts required by the primary experiment.';
  }
}

function renderCoreSelect(){
  const previous=$('coreSelect').value;
  $('coreSelect').innerHTML=cores.map(core=>{
    const prefix=core.id==='primary-full'?'PRIMARY · ':'EXAMPLE CORE · ';
    return '<option value="'+escapeHtml(core.id)+'">'+escapeHtml(prefix+core.name)+' — '+escapeHtml(core.id)+'</option>';
  }).join('');
  if(previous && cores.some(c=>c.id===previous)) $('coreSelect').value=previous;
  else if(cores.some(c=>c.id==='primary-full')) $('coreSelect').value='primary-full';
}

async function selectCore(initial=false){
  const id=$('coreSelect').value;
  currentCore=cores.find(core=>core.id===id)||null;
  if(!currentCore) return;
  currentPlan=await api('/api/experiments/'+encodeURIComponent(id)+'/plan');
  syncControlsFromCore();
  renderPlan();
  await loadRunHistory();
  if(!initial) $('runSummary').innerHTML='<div class="empty-state">Run this Core to see its execution trace.</div>';
  $('executionTrace').innerHTML='';
  $('rawRun').textContent='No run yet.';
  setDirty(false);
}

function syncControlsFromCore(){
  $('coreName').textContent=currentCore.name;
  $('coreObjective').textContent=currentCore.experiment?.objective||currentCore.description||'No objective recorded.';
  $('architectureTags').value=architectureArray(currentCore.architecture).join(',');
  $('integrationCycles').value=currentCore.runtime?.integration_cycles||2;
  $('jevEnabled').checked=Boolean(currentCore.jev?.enabled);
  $('jevModel').value=currentCore.jev?.model||'jev-latest';
  $('jevFeedback').checked=Boolean(currentCore.jev?.feedback_to_brain);
  $('jevFeedbackTargets').value=(currentCore.jev?.feedback_targets||[]).join(',');
  $('llmEnabled').checked=Boolean(currentCore.llm?.enabled);
  $('llmProvider').value=currentCore.llm?.provider||'lmstudio';
  $('llmModel').value=currentCore.llm?.model||'';
  $('llmFeedback').checked=Boolean(currentCore.llm?.feedback_to_brain);
  $('llmFeedbackTargets').value=(currentCore.llm?.feedback_targets||[]).join(',');
  $('llmVerify').checked=Boolean(currentCore.llm?.verify_with_jev);
  $('recordingLevel').value=currentCore.outputs?.recording_level||'trace';
  $('persistState').checked=currentCore.runtime?.persist_brain_state!==false;
  $('experimentObjective').value=currentCore.experiment?.objective||'';
  $('taskPrompt').value=currentCore.experiment?.task_prompt||'';
  $('jevQuestions').value=pretty(currentCore.jev?.questions||{});
  $('coreJson').textContent=pretty(currentCore);
  $('hiveChain').value=currentCore.id;
  updateLayerExplanations();
}

function updateLayerExplanations(){
  const tags=$('architectureTags').value.split(',').map(value=>value.trim()).filter(Boolean);
  const jevTagged=tags.includes('jev');
  const llmTagged=tags.includes('llm');
  $('jevExplanation').textContent=$('jevEnabled').checked
    ?(jevTagged?'Enabled. Venice JEV is called exactly where the jev tag appears.':'Enabled in configuration, but no jev tag is present in this architecture.')
    :'Disabled as an ablation. Any jev tags are recorded as skipped and no JEV network call occurs.';
  const provider=$('llmProvider').value;
  $('llmExplanation').textContent=$('llmEnabled').checked
    ?(llmTagged?'Enabled. '+(provider==='venice'?'Venice':'LM Studio')+' is called exactly where the llm tag appears. It is an integrated HIVE component, but it is not part of the biological connectome.':'Enabled in configuration, but no llm tag is present in this architecture. The model is not part of the biological connectome.')
    :'Disabled as an ablation. Any llm tags are recorded as skipped and no language-model call occurs. The model is not part of the biological connectome.';
}

function localStagePlan(stage){
  const server=currentPlan?.stages?.find(item=>item.id===stage.id)||{};
  return {...server,enabled:stage.enabled,engine:stage.engine,input_from:stage.input_from||[],config:stage.config||{}};
}

function stageNode(stage){
  const plan=localStagePlan(stage);
  const role=plan.role||'experimental';
  const installed=plan.pack_id?plan.dataset_installed:true;
  const details=(plan.details||[]).join(' · ');
  return '<div class="pipeline-node '+role+(stage.enabled?'':' disabled')+'">'+
    '<div class="node-top"><div><div class="node-type">Neural substrate · '+escapeHtml(role)+'</div><strong>'+escapeHtml(plan.name||stage.id)+'</strong></div>'+
    '<label class="switch" title="Enable or disable this neural stage"><input type="checkbox" '+(stage.enabled?'checked':'')+' onchange="setStageEnabled(\''+escapeHtml(stage.id)+'\',this.checked)"><span></span></label></div>'+
    '<div class="node-engine">'+escapeHtml(plan.engine_label||stage.engine)+'</div>'+
    '<div class="node-detail">'+(plan.pack_id?(installed?'Dataset installed':'DATASET NOT INSTALLED'):'No external dataset')+(details?' · '+escapeHtml(details):'')+'</div>'+
  '</div>';
}

function bridgeNode(source,target){
  const bridge=(currentCore.bridges||[]).find(b=>b.source===source && b.target===target);
  if(!bridge) return '<div class="pipeline-arrow">→</div>';
  const label=currentPlan?.bridges?.find(b=>b.id===bridge.id)?.label||bridge.engine;
  return '<div class="bridge-editor"><strong>'+escapeHtml(source)+' → '+escapeHtml(target)+'</strong>'+
    '<div class="meta">'+escapeHtml(label)+'</div>'+
    '<select onchange="setBridgeEngine(\''+escapeHtml(bridge.id)+'\',this.value)">'+
      '<option value="state_projection_v1" '+(bridge.engine==='state_projection_v1'?'selected':'')+'>Neural state projection</option>'+
      '<option value="hash_projection_v1" '+(bridge.engine==='hash_projection_v1'?'selected':'')+'>Hash projection control</option>'+
      '<option value="identity_payload_v1" '+(bridge.engine==='identity_payload_v1'?'selected':'')+'>Payload handoff</option>'+
    '</select></div>';
}

function externalNode(kind,enabled,label,details){
  return '<div class="pipeline-arrow">→</div><div class="pipeline-node external'+(enabled?'':' disabled')+'">'+
    '<div class="node-type">'+escapeHtml(kind)+'</div><strong>'+escapeHtml(label)+'</strong>'+
    '<div class="node-engine">'+escapeHtml(details)+'</div>'+
    '<div class="node-detail">'+(enabled?'ENABLED':'DISABLED')+'</div></div>';
}

function renderPlan(){
  if(!currentCore||!currentPlan) return;
  $('coreName').textContent=currentCore.name;
  $('coreObjective').textContent=currentCore.experiment?.objective||currentPlan.objective||'No objective recorded.';

  const stages=currentCore.brain_chain||[];
  const stageById=Object.fromEntries(stages.map(stage=>[stage.id,stage]));
  const bridges=currentCore.bridges||[];
  const bridgeById=Object.fromEntries(bridges.map(bridge=>[bridge.id,bridge]));
  const tags=$('architectureTags').value.split(',').map(value=>value.trim()).filter(Boolean);

  let html='<div class="pipeline-node"><div class="node-type">Start</div><strong>Input</strong><div class="node-engine">Your text or JSON payload</div><div class="node-detail">The tagged architecture starts here.</div></div>';
  for(const tag of tags){
    html+='<div class="pipeline-arrow">→</div>';
    if(stageById[tag]){
      html+=stageNode(stageById[tag]);
      continue;
    }
    if(bridgeById[tag]){
      const bridge=bridgeById[tag];
      const label=currentPlan?.bridges?.find(item=>item.id===bridge.id)?.label||bridge.engine;
      html+='<div class="pipeline-node bridge"><div class="node-type">Bridge</div><strong>'+escapeHtml(tag)+'</strong><div class="node-engine">'+escapeHtml(bridge.source+' → '+bridge.target)+'</div><div class="node-detail">'+escapeHtml(label)+'</div></div>';
      continue;
    }
    if(tag==='readout'){
      html+='<div class="pipeline-node"><div class="node-type">State adapter</div><strong>Whole-state readout</strong><div class="node-engine">Context derived from the complete executed neural state</div><div class="node-detail">Required before JEV/LLM after neural or bridge changes.</div></div>';
      continue;
    }
    if(tag==='jev'){
      html+='<div class="pipeline-node external'+($('jevEnabled').checked?'':' disabled')+'"><div class="node-type">Decision layer</div><strong>JEV</strong><div class="node-engine">Venice · '+escapeHtml($('jevModel').value||'jev-latest')+'</div><div class="node-detail">'+($('jevEnabled').checked?'CALL':'ABLATION SKIP')+'</div></div>';
      continue;
    }
    if(tag==='llm'){
      html+='<div class="pipeline-node external'+($('llmEnabled').checked?'':' disabled')+'"><div class="node-type">Reasoning layer</div><strong>LLM</strong><div class="node-engine">'+escapeHtml(($('llmProvider').value||'—')+' · '+($('llmModel').value||'model not selected'))+'</div><div class="node-detail">'+($('llmEnabled').checked?'CALL':'ABLATION SKIP')+'</div></div>';
      continue;
    }
    if(tag==='jev_verify'){
      const verifyEnabled=$('jevEnabled').checked&&$('llmEnabled').checked&&$('llmVerify').checked;
      html+='<div class="pipeline-node external'+(verifyEnabled?'':' disabled')+'"><div class="node-type">Verification</div><strong>JEV verify</strong><div class="node-engine">Venice Decisions verification</div><div class="node-detail">'+(verifyEnabled?'CALL':'SKIP')+' · verifies the latest LLM output; a prior regular JEV decision is optional.</div></div>';
      continue;
    }
    if(tag==='feedback'){
      const sources=[];
      if($('jevFeedback').checked) sources.push('JEV');
      if($('llmFeedback').checked) sources.push('LLM');
      html+='<div class="pipeline-node'+(sources.length?'':' disabled')+'"><div class="node-type">Recurrent adapter</div><strong>Feedback</strong><div class="node-engine">Independent bounded modulation from '+escapeHtml(sources.join(' + ')||'no enabled source')+'</div><div class="node-detail">Each source uses its own target set. Affects later neural tags in this cycle or the next integration cycle.</div></div>';
      continue;
    }
    html+='<div class="pipeline-node disabled"><div class="node-type">Unknown tag</div><strong>'+escapeHtml(tag)+'</strong><div class="node-engine">Will be rejected by backend validation</div></div>';
  }
  html+='<div class="pipeline-arrow">→</div><div class="pipeline-node"><div class="node-type">End</div><strong>Recorded result</strong><div class="node-engine">'+escapeHtml($('recordingLevel').value)+' recording</div><div class="node-detail">Exact component order and provider receipts are persisted.</div></div>';
  $('pipelineBuilder').innerHTML=html;

  const warnings=dirty?[]:[...(currentPlan.warnings||[])];
  const known=new Set([...Object.keys(stageById),...Object.keys(bridgeById),'readout','jev','llm','jev_verify','feedback']);
  const unknown=tags.filter(tag=>!known.has(tag));
  if(unknown.length) warnings.push('Unknown architecture tags: '+unknown.join(', '));
  for(const stage of stages){
    const p=localStagePlan(stage);
    if(stage.enabled && tags.includes(stage.id) && p.pack_id && !p.dataset_installed) warnings.push((p.name||stage.id)+' is tagged and enabled but its dataset is not installed.');
    if(stage.enabled && !tags.includes(stage.id)) warnings.push((p.name||stage.id)+' is enabled but omitted from the architecture tags.');
  }
  if($('jevEnabled').checked && tags.includes('jev') && !currentPlan.jev?.configured) warnings.push('JEV is tagged and enabled but Venice credentials are not configured.');
  if($('jevEnabled').checked && $('llmEnabled').checked && $('llmVerify').checked && tags.includes('jev_verify') && !currentPlan.jev?.configured) warnings.push('JEV verification is tagged and enabled but Venice credentials are not configured.');
  if($('llmEnabled').checked && tags.includes('llm') && !$('llmModel').value.trim() && !providerState?.default_llm_model) warnings.push('LLM is tagged and enabled but no model is selected.');
  $('planWarnings').innerHTML=warnings.length
    ?[...new Set(warnings)].map(w=>'<div class="warning">'+escapeHtml(w)+'</div>').join('')
    :'<div class="ok-note">Tagged architecture resolves without obvious configuration blockers.</div>';

  $('coreJson').textContent=pretty(currentCore);
}

function setStageEnabled(id,enabled){
  const stage=currentCore?.brain_chain?.find(item=>item.id===id);
  if(!stage) return;
  stage.enabled=enabled;
  setDirty();
  renderPlan();
}

function setBridgeEngine(id,engine){
  const bridge=currentCore?.bridges?.find(item=>item.id===id);
  if(!bridge) return;
  bridge.engine=engine;
  setDirty();
  renderPlan();
}

function updateCoreControls(){
  if(!currentCore) return;
  currentCore.architecture=$('architectureTags').value.split(',').map(value=>value.trim()).filter(Boolean);
  currentCore.runtime.integration_cycles=Math.max(1,Math.min(8,Number($('integrationCycles').value)||1));
  currentCore.jev.enabled=$('jevEnabled').checked;
  currentCore.jev.model=$('jevModel').value.trim()||'jev-latest';
  currentCore.jev.feedback_to_brain=$('jevFeedback').checked;
  currentCore.jev.feedback_targets=$('jevFeedbackTargets').value.split(',').map(value=>value.trim()).filter(Boolean);
  currentCore.llm.enabled=$('llmEnabled').checked;
  currentCore.llm.provider=$('llmProvider').value;
  currentCore.llm.model=$('llmModel').value.trim()||null;
  currentCore.llm.feedback_to_brain=$('llmFeedback').checked;
  currentCore.llm.feedback_targets=$('llmFeedbackTargets').value.split(',').map(value=>value.trim()).filter(Boolean);
  currentCore.llm.verify_with_jev=$('llmVerify').checked;
  currentCore.outputs.recording_level=$('recordingLevel').value;
  currentCore.runtime.persist_brain_state=$('persistState').checked;
  updateLayerExplanations();
  setDirty();
  renderPlan();
}

function syncAdvancedControls(){
  currentCore.experiment.objective=$('experimentObjective').value.trim();
  currentCore.experiment.task_prompt=$('taskPrompt').value;
  try{
    currentCore.jev.questions=JSON.parse($('jevQuestions').value||'{}');
  }catch(error){
    throw new Error('JEV questions JSON is invalid: '+error.message);
  }
}

async function saveCore(options={}){
  if(!currentCore) return;
  syncAdvancedControls();
  updateCoreControls();
  const saved=await api('/api/workers/'+encodeURIComponent(currentCore.id),{method:'PUT',body:JSON.stringify(currentCore)});
  currentCore=saved;
  const index=cores.findIndex(core=>core.id===saved.id);
  if(index>=0) cores[index]=saved;
  currentPlan=await api('/api/experiments/'+encodeURIComponent(saved.id)+'/plan');
  syncControlsFromCore();
  renderPlan();
  setDirty(false);
  if(!options.quiet) $('saveState').textContent='Saved to HIVE backend.';
}

function setInputMode(mode){
  inputMode=mode;
  $('textModeBtn').classList.toggle('active',mode==='text');
  $('jsonModeBtn').classList.toggle('active',mode==='json');
  $('runInput').placeholder=mode==='json'
    ?'Paste a JSON object or array…'
    :'Type or paste the input you want this experiment to process…';
}

function inputPayload(){
  const raw=$('runInput').value.trim();
  if(!raw) throw new Error('Enter an input before running the experiment.');
  if(inputMode==='json'){
    try{return JSON.parse(raw)}catch(error){throw new Error('Input JSON is invalid: '+error.message)}
  }
  return {text:raw};
}

async function runCore(){
  $('runButton').disabled=true;
  $('runStatus').textContent='Saving configuration…';
  try{
    const payload=inputPayload();
    await saveCore({quiet:true});
    if($('resetBeforeRun').checked){
      $('runStatus').textContent='Resetting neural state…';
      await api('/api/pipeline/reset?worker_id='+encodeURIComponent(currentCore.id),{method:'POST'});
    }
    $('runStatus').textContent='Executing '+currentCore.name+'…';
    const result=await api('/api/pipeline/run',{
      method:'POST',
      body:JSON.stringify({
        worker_id:currentCore.id,
        jev_enabled:currentCore.jev.enabled,
        llm_enabled:currentCore.llm.enabled,
        mode:'auto',
        event:{source_id:'gui',kind:'experiment_input',payload}
      })
    });
    renderRun(result,payload);
    $('rawRun').textContent=pretty(result);
    $('runStatus').textContent='Run complete · '+shortId(result.run_id);
    await Promise.all([loadRunHistory(),refreshHealthOnly()]);
  }catch(error){
    $('runStatus').textContent='Run failed';
    $('runSummary').innerHTML='<div class="warning"><b>Run failed:</b> '+escapeHtml(error.message)+'</div>';
    $('executionTrace').innerHTML='';
  }finally{
    $('runButton').disabled=false;
  }
}

async function refreshHealthOnly(){
  try{
    healthState=await api('/api/health');
    renderSystemTruth();
    currentPlan=await api('/api/experiments/'+encodeURIComponent(currentCore.id)+'/plan');
    renderPlan();
  }catch(_){}
}

function metricItems(metrics){
  const order=['nodes','edges','synaptic_contacts','input_nodes','spikes','active_fraction','energy','novelty','max_abs','mean'];
  const labels={
    nodes:'Neurons / nodes',edges:'Connections',synaptic_contacts:'Synaptic contacts',input_nodes:'Stimulated inputs',
    spikes:'Spikes',active_fraction:'Active fraction',energy:'State energy',novelty:'State change',max_abs:'Max activity',mean:'Mean activity'
  };
  return order.filter(key=>metrics?.[key]!==undefined).map(key=>{
    const value=key==='active_fraction'?formatPercent(metrics[key]):formatNumber(metrics[key]);
    return '<div class="metric"><span>'+escapeHtml(labels[key]||key)+'</span><strong>'+escapeHtml(value)+'</strong></div>';
  }).join('');
}

function decisionValue(answer){
  if(!answer||typeof answer!=='object') return String(answer??'—');
  if(answer.choice!==undefined) return String(answer.choice);
  if(answer.score!==undefined) return formatNumber(answer.score);
  if(answer.noul!==undefined) return formatPercent(answer.noul);
  return 'structured result';
}

function decisionsHtml(bundle){
  const answers=bundle?.answers||{};
  const entries=Object.entries(answers);
  if(!entries.length) return '<div class="meta">No structured decisions returned.</div>';
  return '<div class="decision-grid">'+entries.map(([key,value])=>
    '<div class="decision"><span>'+escapeHtml(key.replaceAll('_',' '))+'</span><strong>'+escapeHtml(decisionValue(value))+'</strong></div>'
  ).join('')+'</div>';
}

function traceRow(index,title,badge,body,klass=''){
  return '<div class="trace-row"><div class="trace-index">'+index+'</div><div class="trace-card '+klass+'">'+
    '<div class="trace-title"><strong>'+escapeHtml(title)+'</strong><span class="trace-badge">'+escapeHtml(badge)+'</span></div>'+body+'</div></div>';
}

function renderRun(result,payload){
  const ex=result.execution||{};
  const role=ex.study_role||'experimental';
  const trace=ex.integration?.trace||[];
  const calledComponents=trace.flatMap(cycle=>cycle.components||[]).filter(item=>item.called).length;
  $('runSummary').innerHTML='<div class="run-overview"><div><h3>'+escapeHtml(currentCore.name)+'</h3>'+
    '<div class="meta">Architecture: '+escapeHtml(architectureArray(ex.architecture||currentCore.architecture).join(' → '))+' · cycles '+escapeHtml(ex.integration?.cycles||1)+' · '+escapeHtml(calledComponents)+' executed component call(s).</div></div>'+
    '<div><div class="trace-badge">'+escapeHtml(role.replaceAll('_',' '))+'</div><div class="run-id">'+escapeHtml(result.run_id)+'</div></div></div>';

  let rows=[];
  let index=1;
  const payloadText=typeof payload==='string'?payload:pretty(payload);
  rows.push(traceRow(index++,'Input','entered HIVE','<div class="output-text">'+escapeHtml(payloadText)+'</div>'));

  for(const cycle of trace){
    rows.push(traceRow(index++,'Integration cycle '+cycle.cycle,'cycle','<div class="meta">'+escapeHtml((cycle.architecture||[]).join(' → '))+'</div>'));
    for(const component of cycle.components||[]){
      const called=Boolean(component.called);
      const typeLabel={
        neural_stage:'neural stage',
        bridge:'bridge',
        neural_readout:'state readout',
        jev:'JEV call',
        llm:'LLM call',
        jev_verification:'JEV verification',
        feedback:'feedback'
      }[component.type]||component.type||'component';
      const stagePlan=component.type==='neural_stage'
        ?currentPlan?.stages?.find(item=>item.id===component.tag)
        :null;
      let title=stagePlan?.name||component.tag||component.type||'component';
      const badge=called?typeLabel+' · executed':typeLabel+' · skipped';
      let body='<div class="meta">Tag: '+escapeHtml(component.tag||'—')+' · Type: '+escapeHtml(component.type||'unknown')+'</div>';

      if(!called){
        body+='<div class="meta">Reason: '+escapeHtml(component.reason||'disabled')+'</div>';
        rows.push(traceRow(index++,title,badge,body,''));
        continue;
      }

      if(component.type==='neural_stage'){
        body='<div class="meta">'+escapeHtml(component.engine||'neural engine')+' · step '+escapeHtml(component.step??'—')+'</div>'+
          '<div class="metrics-grid">'+metricItems(component.metrics||{})+'</div>'+
          (component.state_hash?'<div class="meta">State hash: <span class="run-id">'+escapeHtml(shortId(component.state_hash))+'</span></div>':'');
      }else if(component.type==='bridge'){
        body='<div class="meta">'+escapeHtml(component.source+' → '+component.target)+' · '+escapeHtml(component.engine||'bridge')+'</div>'+
          '<div class="metrics-grid"><div class="metric"><span>Stimulus channels</span><strong>'+escapeHtml(formatNumber(component.stimulus_count||0))+'</strong></div><div class="metric"><span>Source step</span><strong>'+escapeHtml(formatNumber(component.source_step||0))+'</strong></div></div>';
      }else if(component.type==='neural_readout'){
        const hashes=Object.entries(component.state_hashes||{}).map(([stage,hash])=>stage+': '+shortId(hash)).join(' · ');
        body='<div class="meta">Whole-state representation built for: '+escapeHtml((component.stages||[]).join(', ')||'no neural stage yet')+'. This is a deterministic engineering readout used to expose neural state to other Core components.</div>'+
          (hashes?'<div class="meta">'+escapeHtml(hashes)+'</div>':'');
      }else if(component.type==='jev'){
        body='<div class="meta">Real Venice Decisions call · model '+escapeHtml(component.model||'—')+' · receipt '+escapeHtml(shortId(component.call_id))+'. JEV outputs are typed inference judgments, not labels discovered by the connectome itself.</div>';
      }else if(component.type==='llm'){
        body='<div class="meta">Real '+escapeHtml(component.provider||'LLM')+' call · model '+escapeHtml(component.model||'—')+' · receipt '+escapeHtml(shortId(component.call_id))+' · feedback '+escapeHtml(formatNumber(component.neural_feedback))+'</div>';
      }else if(component.type==='jev_verification'){
        body='<div class="meta">Real Venice verification call · model '+escapeHtml(component.model||'—')+' · receipt '+escapeHtml(shortId(component.call_id))+'</div>';
      }else if(component.type==='feedback'){
        const sources=Object.entries(component.sources||{}).map(([name,spec])=>name+'='+formatNumber(spec.value)+'→'+((spec.targets||[]).join(',')||'all')).join(' · ');
        const targets=Object.entries(component.target_modulations||{}).map(([name,value])=>name+'='+formatNumber(value)).join(' · ');
        body='<div class="meta">Aggregate modulation '+escapeHtml(formatNumber(component.modulation))+' · sources '+escapeHtml(sources||'none')+'</div>'+
          '<div class="meta">'+(component.applied?'Applied per neural target: '+escapeHtml(targets||'none'):'Not applied because no later same-input neural execution remained')+'</div>';
      }
      rows.push(traceRow(index++,title,badge,body,called?'success':''));
    }
  }

  if(ex.jev?.called){
    rows.push(traceRow(index++,'Final JEV decision','result',decisionsHtml(result.decisions),'external'));
  }
  if(ex.llm?.called && result.llm){
    rows.push(traceRow(index++,'Final LLM output','result','<div class="output-text">'+escapeHtml(result.llm.text||'(empty response)')+'</div>','external'));
  }

  const finalBody='<div class="meta">Run persisted with '+escapeHtml(currentCore.outputs.recording_level)+' recording. Final modulation: '+escapeHtml(formatNumber(result.modulation))+'.</div>'+
    '<div class="meta">Labels: '+escapeHtml((result.labels||[]).join(' · ')||'none')+'</div>'+
    ((result.unresolved||[]).length?'<div class="warning">'+escapeHtml(result.unresolved.join(' · '))+'</div>':'');
  rows.push(traceRow(index++,'Recorded result','saved',finalBody,'success'));
  $('executionTrace').innerHTML=rows.join('');
}

async function runMatrix(){
  try{
    const payload=inputPayload();
    await saveCore({quiet:true});
    $('matrixHuman').innerHTML='<div class="meta">Running four matched configurations…</div>';
    const result=await api('/api/evals/run',{method:'POST',body:JSON.stringify({
      worker_id:currentCore.id,
      cases:[{id:'gui-ablation',event:{source_id:'gui:ablation',kind:'experiment_input',payload}}]
    })});
    const order=['jev_off_llm_off','jev_on_llm_off','jev_off_llm_on','jev_on_llm_on'];
    $('matrixHuman').innerHTML=order.map(key=>{
      const row=result.summary?.[key]||{};
      const label=key.replaceAll('_',' ').replace('jev','JEV').replace('llm','LLM');
      return '<div class="matrix-row"><strong>'+escapeHtml(label)+'</strong><span>'+escapeHtml(formatNumber(row.mean_latency_ms))+' ms</span><span>JEV '+escapeHtml(row.jev_calls??0)+'</span><span>LLM '+escapeHtml(row.llm_calls??0)+'</span><span>fail '+escapeHtml(row.failures??0)+'</span></div>';
    }).join('');
    await loadRunHistory();
  }catch(error){
    $('matrixHuman').innerHTML='<div class="warning">'+escapeHtml(error.message)+'</div>';
  }
}

async function loadRunHistory(){
  if(!currentCore) return;
  try{
    const runs=await api('/api/runs?limit=8&worker_id='+encodeURIComponent(currentCore.id));
    $('runHistory').innerHTML=runs.length?runs.map(run=>{
      const route=run.decisions?.answers?.route?.choice||'—';
      const time=run.event?.timestamp?new Date(run.event.timestamp).toLocaleString():'unknown time';
      return '<div class="history-row"><strong>'+escapeHtml(time)+' · '+escapeHtml(route)+'</strong><div class="meta">'+Object.keys(run.stages||{}).length+' neural stage(s) · JEV '+(run.execution?.jev?.called?'called':'not called')+' · LLM '+(run.execution?.llm?.called?'called':'not called')+' · '+escapeHtml(shortId(run.run_id))+'</div></div>';
    }).join(''):'<div class="meta">No saved runs for this Core yet.</div>';
  }catch(error){
    $('runHistory').innerHTML='<div class="warning">'+escapeHtml(error.message)+'</div>';
  }
}

function downloadExperiment(all=false){
  const query=all?'':'?worker_id='+encodeURIComponent(currentCore?.id||'');
  window.location.assign('/api/exports/experiment'+query);
}

async function loadProviderConfig(){
  try{
    providerState=await api('/api/providers/config');
    $('veniceBaseUrl').value=providerState.venice_base_url||'';
    $('veniceDefaultJevModel').value=providerState.venice_decision_model||'jev-latest';
    $('lmstudioBaseUrl').value=providerState.lmstudio_base_url||'';
    $('defaultLlmModel').value=providerState.default_llm_model||'';
    $('providerConfigState').textContent='Venice key: '+(providerState.venice_api_key_configured?'configured':'missing')+' · LM Studio token: '+(providerState.lmstudio_api_token_configured?'configured':'not set');
  }catch(error){
    $('providerConfigState').textContent='Could not load provider configuration: '+error.message;
  }
}

async function saveProviderConfig(){
  try{
    const payload={
      venice_base_url:$('veniceBaseUrl').value.trim(),
      venice_decision_model:$('veniceDefaultJevModel').value.trim()||'jev-latest',
      lmstudio_base_url:$('lmstudioBaseUrl').value.trim(),
      default_llm_model:$('defaultLlmModel').value.trim()||null,
      clear_default_llm_model:!$('defaultLlmModel').value.trim()
    };
    if($('veniceApiKey').value) payload.venice_api_key=$('veniceApiKey').value;
    if($('lmstudioApiToken').value) payload.lmstudio_api_token=$('lmstudioApiToken').value;
    providerState=await api('/api/providers/config',{method:'PUT',body:JSON.stringify(payload)});
    $('veniceApiKey').value='';
    $('lmstudioApiToken').value='';
    $('providerConfigState').textContent='Saved. Venice key: '+(providerState.venice_api_key_configured?'configured':'missing')+' · LM Studio token: '+(providerState.lmstudio_api_token_configured?'configured':'not set');
    await Promise.all([loadProviders(),refreshHealthOnly()]);
  }catch(error){
    $('providerConfigState').textContent='Save failed: '+error.message;
  }
}

async function loadProviders(){
  try{
    const status=await api('/api/providers/status');
    const venice=status.venice||{};
    const lm=status.lmstudio||{};
    $('providers').innerHTML=
      '<div class="provider-card"><strong>Venice</strong><div class="meta">'+(venice.configured?(venice.ok?'Reachable for model discovery':'Configured but model discovery failed'):'No API key configured')+' · '+escapeHtml(venice.base_url||'')+'</div></div>'+
      '<div class="provider-card"><strong>LM Studio</strong><div class="meta">'+(lm.ok?'Reachable from HIVE container':'Not reachable from HIVE container')+' · '+escapeHtml(lm.base_url||'')+'</div></div>';
  }catch(error){
    $('providers').innerHTML='<div class="warning">'+escapeHtml(error.message)+'</div>';
  }
}

async function testProvider(capability){
  try{
    let model=null;
    if(capability==='venice_jev') model=$('jevModel').value.trim()||$('veniceDefaultJevModel').value.trim();
    if(capability==='venice_chat') model=$('llmProvider').value==='venice'?$('llmModel').value.trim():'';
    if(capability==='lmstudio_chat') model=$('llmProvider').value==='lmstudio'?$('llmModel').value.trim():$('defaultLlmModel').value.trim();
    const result=await api('/api/providers/test',{method:'POST',body:JSON.stringify({capability,model:model||null})});
    const t=result.transport||{};
    $('providers').innerHTML='<div class="provider-card"><strong>Real inference call succeeded</strong><div class="meta">Capability: '+escapeHtml(capability)+' · model '+escapeHtml(result.model||'—')+' · HTTP '+escapeHtml(t.http_status??'—')+' · '+escapeHtml(formatNumber(t.latency_ms))+' ms</div><div class="meta">Receipt '+escapeHtml(shortId(t.call_id))+' · request '+escapeHtml(shortId(t.request_hash))+' · response '+escapeHtml(shortId(t.response_hash))+'</div></div>';
  }catch(error){
    $('providers').innerHTML='<div class="warning"><b>Real inference call failed:</b> '+escapeHtml(error.message)+'</div>';
  }
}

async function loadConnectomes(){
  try{
    const packs=await api('/api/connectomes');
    $('connectomes').innerHTML=packs.map(pack=>{
      const state=pack.installed?'INSTALLED + VERIFIED':(pack.installable?'NOT INSTALLED':'REFERENCE ONLY');
      const tags=[pack.primary_required?'PRIMARY REQUIRED':'',pack.control_only?'CONTROL ONLY':''].filter(Boolean).join(' · ');
      const button=pack.installable&&!pack.installed?'<button class="secondary small" onclick="installPack(\''+escapeHtml(pack.id)+'\','+(Boolean(pack.warning))+')">Install</button>':'';
      return '<div class="pack-row"><div><div class="pack-title">'+escapeHtml(pack.name)+'</div><div class="pack-state">'+escapeHtml(state+(tags?' · '+tags:''))+'</div><div class="meta">'+escapeHtml(pack.role||'')+'</div></div>'+button+'</div>';
    }).join('');
  }catch(error){
    $('connectomes').innerHTML='<div class="warning">'+escapeHtml(error.message)+'</div>';
  }
}

async function installPack(id,large){
  if(!confirm('Download and verify '+id+'?'+(large?' This is a large required dataset.':''))) return;
  try{
    await api('/api/connectomes/'+encodeURIComponent(id)+'/install?confirm='+(large?'true':'false'),{method:'POST'});
    const started=Date.now();
    while(Date.now()-started<7200000){
      await new Promise(resolve=>setTimeout(resolve,1200));
      const job=await api('/api/connectomes/'+encodeURIComponent(id)+'/job');
      if(job.status==='complete') break;
      if(job.status==='error') throw new Error(job.error||'connectome install failed');
    }
    await Promise.all([loadConnectomes(),refreshHealthOnly()]);
  }catch(error){
    alert(error.message);
  }
}

async function runHiveChain(){
  try{
    const ids=$('hiveChain').value.split(',').map(value=>value.trim()).filter(Boolean);
    if(!ids.length) throw new Error('Enter at least one Core ID.');
    const payload=inputPayload();
    await saveCore({quiet:true});
    $('hiveResult').innerHTML='<div class="meta">Running '+ids.length+' Core(s)…</div>';
    const result=await api('/api/hive/run',{method:'POST',body:JSON.stringify({
      core_ids:ids,mode:'auto',event:{source_id:'gui:hive',kind:'experiment_input',payload}
    })});
    $('hiveResult').innerHTML=result.results.map((run,index)=>{
      return '<div class="history-row"><strong>'+(index+1)+'. '+escapeHtml(ids[index])+'</strong><div class="meta">run '+escapeHtml(shortId(run.run_id))+' · stages '+Object.keys(run.stages||{}).length+' · JEV '+(run.execution?.jev?.called?'called':'not called')+' · LLM '+(run.execution?.llm?.called?'called':'not called')+'</div></div>';
    }).join('');
    await loadRunHistory();
  }catch(error){
    $('hiveResult').innerHTML='<div class="warning">'+escapeHtml(error.message)+'</div>';
  }
}

boot().catch(error=>{
  console.error(error);
  $('health').textContent='startup error';
  $('health').className='pill bad';
});
