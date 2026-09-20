#!/usr/bin/env python3
"""Offline GUI render/interaction smoke test.

This test uses the real HTML/CSS/JS and a deterministic in-page mock of the API.
The Python test suite separately exercises the real FastAPI routes. Keeping the
browser transport mocked makes this check reproducible and prevents provider or
network availability from affecting rendering tests.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


async def run(executable: str | None, screenshot: Path | None) -> None:
    html = (ROOT / "src/hive_connectome/static/index.html").read_text(encoding="utf-8")
    css = (ROOT / "src/hive_connectome/static/style.css").read_text(encoding="utf-8")
    js = (ROOT / "src/hive_connectome/static/app.js").read_text(encoding="utf-8")
    workers = json.loads((ROOT / "config/workers.default.json").read_text(encoding="utf-8"))["workers"]
    templates = json.loads((ROOT / "config/experiment_templates.json").read_text(encoding="utf-8"))
    packs = json.loads((ROOT / "config/connectomes.json").read_text(encoding="utf-8"))["packs"]
    for pack in packs:
        pack["installed"] = False
        pack["file_status"] = []

    html = re.sub(
        r'<link rel="stylesheet" href="/static/style.css">',
        f"<style>{css}</style>",
        html,
    )
    html = re.sub(r'<script src="/static/app.js"></script>', "", html)

    async with async_playwright() as pw:
        kwargs = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            kwargs["executable_path"] = executable
        browser = await pw.chromium.launch(**kwargs)
        page = await browser.new_page(viewport={"width": 1440, "height": 1050})
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        await page.set_content(html, wait_until="domcontentloaded")
        fixtures = {"workers": workers, "templates": templates, "packs": packs}
        await page.evaluate(
            """(fx) => {
              window.__fx = fx;
              window.fetch = async (url, opts = {}) => {
                const u = new URL(url, 'http://hive.local');
                const path = u.pathname;
                let body = null;
                let status = 200;
                if (path === '/api/health') body = {ok:true, version:'0.3.2', workers:fx.workers.map(x=>x.id)};
                else if (path === '/api/experiment-templates') body = fx.templates;
                else if (path === '/api/workers' && (!opts.method || opts.method === 'GET')) body = fx.workers;
                else if (path === '/api/connectomes') body = fx.packs;
                else if (path === '/api/providers/status') body = {
                  venice:{configured:false, ok:false, model:'jev-latest'},
                  lmstudio:{configured:true, ok:false, base_url:'http://host.docker.internal:1234/v1', models:[], error:'offline'}
                };
                else if (path === '/api/pipeline/run') body = {
                  decisions:{provider:'brain-readout', answers:{route:{choice:'store'}}},
                  labels:['worker:scout','jev:off','llm:off'], unresolved:[]
                };
                else if (path === '/api/evals/run') body = {
                  summary:{
                    jev_off_llm_off:{cases:1}, jev_on_llm_off:{cases:1},
                    jev_off_llm_on:{cases:1}, jev_on_llm_on:{cases:1}
                  }, rows:[]
                };
                else if (path === '/api/pipeline/reset') body = {ok:true};
                else if (path.includes('/run-environment')) body = {worker_id:'scout', results:[]};
                else if (path.includes('/install')) body = {status:'queued'};
                else if (path.startsWith('/api/workers/') && !path.slice('/api/workers/'.length).includes('/') && opts.method === 'PUT') body = JSON.parse(opts.body);
                else { status = 404; body = {detail:'mock missing ' + path}; }
                return {ok: status < 400, status, json: async () => body, statusText: status === 404 ? 'Not Found' : 'OK'};
              };
            }""",
            fixtures,
        )
        await page.add_script_tag(content=js)

        await page.wait_for_function("document.getElementById('workerName').value.length > 0")
        assert await page.locator("#workerName").input_value() == "Scout"
        card_color = await page.evaluate("getComputedStyle(document.querySelector('.card')).backgroundColor")
        assert card_color == "rgb(24, 25, 20)", f"stylesheet was not applied: {card_color}"

        await page.select_option("#dataMode", "browser_dom")
        assert await page.locator("#envBrowser").is_visible()
        assert not await page.locator("#envFiles").is_visible()
        await page.select_option("#dataMode", "manual")

        await page.click('button:has-text("Run selected worker")')
        await page.wait_for_function("document.getElementById('runResult').textContent.includes('brain-readout')")
        await page.click('button:has-text("Run 4 combinations")')
        await page.wait_for_function("document.getElementById('evalResult').textContent.includes('jev_on_llm_on')")
        await page.click('button:has-text("Test Venice + LM Studio")')
        await page.wait_for_function("document.getElementById('providers').textContent.includes('host.docker.internal')")

        assert not console_errors, f"console errors: {console_errors}"
        assert not page_errors, f"page errors: {page_errors}"

        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            await page.evaluate("window.scrollTo(0,0)")
            await page.screenshot(path=str(screenshot), full_page=True)

        print("GUI smoke: PASS")
        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", help="Chromium/Chrome executable; omit to use Playwright-managed Chromium")
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    asyncio.run(run(args.executable, args.screenshot))


if __name__ == "__main__":
    main()
