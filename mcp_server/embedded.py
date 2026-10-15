"""Run the MCP HTTP app in a background thread (tests and the evaluation runner)."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import uvicorn

from mcp_server.server import ServerDeps, build_http_app


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@contextmanager
def serve_in_background(deps: ServerDeps, timeout: float = 15.0) -> Iterator[str]:
    """Start the server on a free local port and yield its MCP endpoint URL."""
    port = free_port()
    server = uvicorn.Server(
        uvicorn.Config(build_http_app(deps), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("MCP server did not start")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
