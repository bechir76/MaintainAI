"""Wiring of the command-line entry points, with external services stubbed out."""

from typing import Any

import pytest
from pydantic import SecretStr

from core.config import Settings
from core.llm import build_chat_model, build_embedder
from core.llm.fake_chat import FakeChatModel
from core.llm.fake_embedder import FakeEmbedder
from core.llm.mistral import MistralChatModel, MistralEmbedder


def test_factories_pick_offline_providers_without_key() -> None:
    settings = Settings(_env_file=None, mistral_api_key=None)
    assert isinstance(build_embedder(settings), FakeEmbedder)
    assert isinstance(build_chat_model(settings), FakeChatModel)


def test_factories_pick_mistral_with_key() -> None:
    settings = Settings(_env_file=None, mistral_api_key=SecretStr("k"), mistral_chat_model="m")
    assert isinstance(build_embedder(settings), MistralEmbedder)
    chat = build_chat_model(settings)
    assert isinstance(chat, MistralChatModel)
    assert chat.name == "m"


class FakePool:
    closed = False

    def close(self) -> None:
        self.closed = True


def test_mcp_cli_runs_http_and_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_server import cli

    pool = FakePool()
    seen: dict[str, Any] = {}
    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(cli, "create_pool", lambda *a, **k: pool)
    monkeypatch.setattr(cli, "build_http_app", lambda deps: "app")
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kw: seen.update(app=app, **kw))
    monkeypatch.setenv("MAINTAINAI_API_KEY", "k")

    cli.main(["--transport", "http"])
    assert seen["app"] == "app"
    assert seen["port"] == 8001
    assert pool.closed

    class Server:
        def run(self, transport: str) -> None:
            seen["transport"] = transport

    built: list[Any] = []
    monkeypatch.setattr(cli, "build_server", lambda deps: built.append(deps) or Server())
    cli.main(["--transport", "stdio"])
    assert seen["transport"] == "stdio"
    assert built[0].stdio_api_key == "k"


def test_ingestion_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    from ingestion import cli
    from ingestion.pipeline import IngestReport

    pool = FakePool()
    calls: dict[str, Any] = {}

    async def fake_ingest(pool_: Any, embedder: Any, directory: Any, **kw: Any) -> IngestReport:
        calls.update(directory=directory, **kw)
        return IngestReport(ingested=["A"], skipped=["B"], chunks=3)

    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(cli, "create_pool", lambda *a, **k: pool)
    monkeypatch.setattr(cli, "ingest_directory", fake_ingest)
    cli.main(["--dir", "somewhere", "--force"])
    assert str(calls["directory"]) == "somewhere"
    assert calls["force"] is True
    assert pool.closed


def test_simulator_main_loop_stops_on_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    from simulator import runner

    class Conn:
        def __enter__(self) -> "Conn":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def execute(self, *args: Any) -> None:
            return None

    class Pool(FakePool):
        def connection(self) -> Conn:
            return Conn()

    pool = Pool()
    ticks: list[Any] = []
    handlers: dict[int, Any] = {}

    def fake_tick(*args: Any) -> None:
        ticks.append(args)
        handlers[runner.signal.SIGTERM](runner.signal.SIGTERM, None)  # stop after one tick

    monkeypatch.setattr(runner, "get_settings", lambda: Settings(_env_file=None, sim_faults=""))
    monkeypatch.setattr(runner, "create_pool", lambda *a, **k: pool)
    monkeypatch.setattr(runner, "seed_machines", lambda p: None)
    monkeypatch.setattr(runner, "backfill", lambda *a: None)
    monkeypatch.setattr(runner, "tick", fake_tick)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)
    monkeypatch.setattr(runner.signal, "signal", lambda sig, fn: handlers.__setitem__(sig, fn))

    runner.main()
    assert len(ticks) == 1
    assert pool.closed
