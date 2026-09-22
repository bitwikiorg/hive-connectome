from __future__ import annotations

import re
from pathlib import Path

ROOT=Path(__file__).parents[1]
HTML=(ROOT/"src/hive_connectome/static/index.html").read_text(encoding="utf-8")
JS=(ROOT/"src/hive_connectome/static/app.js").read_text(encoding="utf-8")


def test_every_js_id_reference_exists_in_html():
    html_ids=set(re.findall(r'id="([A-Za-z0-9_-]+)"',HTML))
    js_ids=set(re.findall(r"\$\('([A-Za-z0-9_-]+)'\)",JS))
    assert not sorted(js_ids-html_ids)


def test_inline_handlers_have_javascript_functions():
    handlers=set(re.findall(r'on(?:click|change)="([A-Za-z0-9_]+)\(',HTML))
    functions=set(re.findall(r'(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(',JS))
    assert handlers<=functions


def test_gui_is_backend_driven_experiment_builder():
    for control in [
        "coreSelect","pipelineBuilder","planWarnings","architectureTags","integrationCycles",
        "jevEnabled","jevModel","jevFeedback","llmEnabled","llmProvider","llmModel","recordingLevel","persistState",
        "runInput","resetBeforeRun","runButton","runSummary","executionTrace","rawRun",
        "matrixHuman","runHistory","providers","connectomes","hiveChain","hiveResult",
        "veniceBaseUrl","veniceDefaultJevModel","veniceApiKey","lmstudioBaseUrl",
        "lmstudioApiToken","defaultLlmModel","providerConfigState","experimentObjective",
        "taskPrompt","jevQuestions","coreJson",
    ]:
        assert f'id="{control}"' in HTML
    for route in [
        "/api/health","/api/workers","/api/experiments/","/api/pipeline/run","/api/pipeline/reset",
        "/api/hive/run","/api/evals/run","/api/providers/status","/api/providers/config",
        "/api/providers/test","/api/connectomes","/api/runs","/api/exports/experiment",
    ]:
        assert route in JS
    assert "RESOLVED EXECUTION PATH" in HTML
    assert "Whole-state projection" in JS
    assert "Run this Core" in HTML


def test_gui_exposes_real_provider_proof_calls_and_lossless_export():
    for phrase in ["Real JEV test","Real Venice LLM test","Real LM Studio test","Download all experiments"]:
        assert phrase in HTML
    assert "Real inference call succeeded" in JS
    assert "request " in JS and "response " in JS
    assert "Debugging: raw run JSON" in HTML
