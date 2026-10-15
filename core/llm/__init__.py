from __future__ import annotations

from core.config import Settings
from core.llm.base import Embedder
from core.llm.fake_embedder import FakeEmbedder


def build_embedder(settings: Settings) -> Embedder:
    if settings.resolved_provider == "mistral":
        from core.llm.mistral import MistralEmbedder

        assert settings.mistral_api_key is not None
        return MistralEmbedder(
            settings.mistral_api_key.get_secret_value(),
            model=settings.mistral_embed_model,
            base_url=settings.mistral_base_url,
            timeout=settings.llm_timeout_seconds,
        )
    return FakeEmbedder(settings.embedding_dim)
