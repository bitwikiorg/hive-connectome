from pathlib import Path

from hive_connectome.settings import Settings, _secret


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HIVE_DATA_DIR", "my-data")
    monkeypatch.setenv("HIVE_CONFIG_DIR", "my-config")
    monkeypatch.setenv("VENICE_BASE_URL", "https://x.test/")
    monkeypatch.setenv("VENICE_API_KEY", " vk ")
    monkeypatch.setenv("VENICE_DECISION_MODEL", "jev-test")
    monkeypatch.setenv("LMSTUDIO_BASE_URL", "http://lm:1234/v1/")
    monkeypatch.setenv("LMSTUDIO_API_TOKEN", " lk ")
    monkeypatch.setenv("HIVE_LLM_PROVIDER", "lmstudio")
    monkeypatch.setenv("HIVE_LLM_MODEL", " tiny ")
    s = Settings.from_env()
    assert s.data_dir == (tmp_path / "my-data").resolve()
    assert s.config_dir == (tmp_path / "my-config").resolve()
    assert s.venice_base_url == "https://x.test"
    assert s.venice_api_key == "vk"
    assert s.venice_decision_model == "jev-test"
    assert s.lmstudio_base_url == "http://lm:1234/v1"
    assert s.lmstudio_api_token == "lk"
    assert s.llm_model == "tiny"


def test_secret_empty_env(monkeypatch):
    monkeypatch.delenv("NOT_SET_SECRET", raising=False)
    assert _secret("definitely-not-present", "NOT_SET_SECRET") is None
