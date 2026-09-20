from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
HTML = (ROOT / "src/hive_connectome/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/hive_connectome/static/app.js").read_text(encoding="utf-8")


def test_every_js_id_reference_exists_in_html():
    html_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', HTML))
    js_ids = set(re.findall(r"\$\('([A-Za-z0-9_-]+)'\)", JS))
    missing = sorted(js_ids - html_ids)
    assert not missing, f"JS references missing DOM ids: {missing}"


def test_inline_handlers_have_javascript_functions():
    handlers = set(re.findall(r'on(?:click|change)="([A-Za-z0-9_]+)\(', HTML))
    functions = set(re.findall(r'(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(', JS))
    assert handlers <= functions


def test_gui_core_controls_and_api_targets_present():
    for control in [
        "workerSelect", "jevEnabled", "llmEnabled", "dataMode", "larvaEngine",
        "beeEngine", "jevModel", "llmProvider", "runtimeEnabled", "runJev",
        "runLlm", "runPayload", "evalResult", "connectomes",
    ]:
        assert f'id="{control}"' in HTML
    for route in [
        "/api/health", "/api/experiment-templates", "/api/workers",
        "/api/pipeline/run", "/api/evals/run", "/api/providers/status",
        "/api/connectomes",
    ]:
        assert route in JS
    assert "installConnectome" in JS
