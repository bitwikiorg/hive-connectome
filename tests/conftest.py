from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hive_connectome.app import create_app
from hive_connectome.settings import Settings
from connectome_fixtures import install_runtime_fixtures


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    install_runtime_fixtures(data_dir)
    return Settings(
        data_dir=data_dir,
        config_dir=Path(__file__).parents[1] / "config",
        venice_base_url="https://api.venice.ai/api/v1",
        venice_api_key=None,
        venice_decision_model="jev-latest",
        lmstudio_base_url="http://127.0.0.1:9/v1",
        lmstudio_api_token=None,
        llm_provider="lmstudio",
        llm_model=None,
    )


@pytest.fixture
def app(test_settings: Settings):
    return create_app(test_settings, start_heartbeat=False)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
