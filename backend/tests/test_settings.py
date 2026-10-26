from pathlib import Path

from app.core.config import ENV_FILE, PROJECT_ROOT, Settings, settings


def test_env_file_is_anchored_at_project_root():
    assert PROJECT_ROOT == Path(__file__).resolve().parents[2]
    assert ENV_FILE == PROJECT_ROOT / ".env"


def test_settings_accept_explicit_environment_values_without_dotenv():
    settings = Settings(
        _env_file=None,
        HF_TOKEN="test-hf-token",
        GOOGLE_API_KEY="test-google-key",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-key",
    )

    assert settings.is_hf_configured
    assert settings.is_gemini_configured
    assert settings.is_supabase_configured


def test_empty_provider_values_are_unconfigured():
    settings = Settings(_env_file=None, HF_TOKEN="", GOOGLE_API_KEY="", DATABASE_URL="")

    assert not settings.is_hf_configured
    assert not settings.is_gemini_configured
    assert not settings.is_database_configured


def test_process_environment_overrides_dotenv(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "process-priority-test")

    loaded = Settings(_env_file=ENV_FILE)

    assert loaded.hf_token == "process-priority-test"
