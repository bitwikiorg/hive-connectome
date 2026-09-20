from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_docker_desktop_contract():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert '127.0.0.1:8088:8080' in compose
    assert '127.0.0.1:8090:8000' in compose
    assert 'http://host.docker.internal:1234/v1' in compose
    assert 'extra_hosts' not in compose
    assert 'hive_connectome.app:create_app' in dockerfile
    assert '"--factory"' in dockerfile


def test_mcp_container_bind_and_security_contract():
    source = (ROOT / "src/hive_connectome/mcp_server.py").read_text(encoding="utf-8")
    assert "from mcp.server import MCPServer" in source
    assert 'host="0.0.0.0"' in source
    assert "port=8000" in source
    assert "TransportSecuritySettings" in source
    assert 'allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"]' in source


def test_public_copy_has_no_project_specific_profile_leakage():
    blocked = ["based nut", "basednut", "private personal hivemind"]
    for base in [ROOT / "README.md", ROOT / "docs", ROOT / "config"]:
        paths = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for path in paths:
            if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8").lower()
            for phrase in blocked:
                assert phrase not in text, f"{phrase!r} leaked into {path.relative_to(ROOT)}"
