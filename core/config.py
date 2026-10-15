from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Role = Literal["viewer", "technician"]

# Cosine similarity cut-offs below which a chunk is treated as "not relevant".
# Calibrated on the eval set; the lexical fake embedder produces lower scores
# than mistral-embed, so each provider gets its own default.
DEFAULT_MIN_SCORE = {"fake": 0.15, "mistral": 0.75}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://maintainai:maintainai@localhost:5432/maintainai"

    # LLM / embeddings. "auto" picks Mistral when a key is set, otherwise the offline fake.
    llm_provider: Literal["auto", "mistral", "fake"] = "auto"
    mistral_api_key: SecretStr | None = None
    mistral_base_url: str = "https://api.mistral.ai/v1"
    mistral_chat_model: str = "mistral-small-latest"
    mistral_embed_model: str = "mistral-embed"
    llm_timeout_seconds: float = 30.0
    embedding_dim: int = 1024

    # Retrieval
    retrieval_top_k: int = Field(default=5, ge=1, le=20)
    retrieval_min_score: float | None = None
    chunk_size: int = 900
    chunk_overlap: int = 150

    # MCP server: comma separated "key:role" pairs
    mcp_api_keys: SecretStr = SecretStr("viewer-dev-key:viewer,technician-dev-key:technician")
    mcp_host: str = "0.0.0.0"  # noqa: S104 - bound inside a container
    mcp_port: int = 8001

    # Agent API
    mcp_server_url: str = "http://localhost:8001/mcp"
    mcp_viewer_key: SecretStr = SecretStr("viewer-dev-key")
    mcp_technician_key: SecretStr = SecretStr("technician-dev-key")
    agent_max_tool_calls: int = Field(default=6, ge=1, le=20)
    agent_timeout_seconds: float = 120.0
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Sensor simulator
    sim_interval_seconds: float = 5.0
    sim_faults: str = "P-3:high_vibration,M-2:overheating"
    sim_backfill_minutes: int = 15

    @property
    def resolved_provider(self) -> Literal["mistral", "fake"]:
        if self.llm_provider == "auto":
            return "mistral" if self.mistral_api_key else "fake"
        return self.llm_provider

    @property
    def min_score(self) -> float:
        if self.retrieval_min_score is not None:
            return self.retrieval_min_score
        return DEFAULT_MIN_SCORE[self.resolved_provider]

    def api_key_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for pair in self.mcp_api_keys.get_secret_value().split(","):
            if not pair.strip():
                continue
            key, _, role = pair.strip().rpartition(":")
            if role not in ("viewer", "technician") or not key:
                raise ValueError(f"invalid MCP_API_KEYS entry for role {role!r}")
            roles[key] = role  # type: ignore[assignment]
        return roles

    def key_for_role(self, role: Role) -> str:
        key = self.mcp_technician_key if role == "technician" else self.mcp_viewer_key
        return key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
