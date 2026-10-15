import pytest
from pydantic import SecretStr

from core.config import Settings


def test_auto_provider_falls_back_to_fake_without_key() -> None:
    settings = Settings(mistral_api_key=None, llm_provider="auto")
    assert settings.resolved_provider == "fake"


def test_auto_provider_uses_mistral_with_key() -> None:
    settings = Settings(mistral_api_key=SecretStr("x"), llm_provider="auto")
    assert settings.resolved_provider == "mistral"


def test_min_score_override() -> None:
    assert Settings(retrieval_min_score=0.5).min_score == 0.5


def test_api_key_roles_parsing() -> None:
    settings = Settings(mcp_api_keys=SecretStr("a:viewer, b:technician,"))
    assert settings.api_key_roles() == {"a": "viewer", "b": "technician"}


def test_api_key_roles_rejects_unknown_role() -> None:
    settings = Settings(mcp_api_keys=SecretStr("a:admin"))
    with pytest.raises(ValueError):
        settings.api_key_roles()


def test_key_for_role() -> None:
    settings = Settings(mcp_viewer_key=SecretStr("v"), mcp_technician_key=SecretStr("t"))
    assert settings.key_for_role("viewer") == "v"
    assert settings.key_for_role("technician") == "t"
