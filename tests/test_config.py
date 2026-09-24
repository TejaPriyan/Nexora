from nexora.config import Config


def test_defaults_are_private_by_default():
    config = Config()
    assert config.telemetry is False
    assert config.cloud_sync is False


def test_env_override(monkeypatch):
    monkeypatch.setenv("NEXORA_TELEMETRY", "true")
    monkeypatch.setenv("NEXORA_LOG_LEVEL", "DEBUG")
    config = Config.load()
    assert config.telemetry is True
    assert config.log_level == "DEBUG"


def test_explicit_overrides_take_precedence_over_env(monkeypatch):
    monkeypatch.setenv("NEXORA_LOG_LEVEL", "DEBUG")
    config = Config.load(overrides={"log_level": "WARNING"})
    assert config.log_level == "WARNING"


def test_toml_file_is_read(tmp_path, monkeypatch):
    toml_path = tmp_path / "nexora.toml"
    toml_path.write_text('[nexora]\nlog_level = "ERROR"\ntelemetry = false\n')
    config = Config.load(config_path=toml_path)
    assert config.log_level == "ERROR"
