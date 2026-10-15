from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn

from core.config import get_settings
from core.db import create_pool
from core.llm import build_embedder
from mcp_server.server import ServerDeps, build_http_app, build_server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MaintainAI MCP server")
    parser.add_argument("--transport", choices=["http", "stdio"], default="http")
    args = parser.parse_args(argv)

    # stdout carries the protocol in stdio mode, so logs go to stderr.
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    pool = create_pool(settings.database_url, max_size=10)
    deps = ServerDeps(
        pool=pool,
        embedder=build_embedder(settings),
        settings=settings,
        stdio_api_key=os.environ.get("MAINTAINAI_API_KEY"),
    )
    try:
        if args.transport == "stdio":
            build_server(deps).run("stdio")
        else:
            uvicorn.run(
                build_http_app(deps),
                host=settings.mcp_host,
                port=settings.mcp_port,
                log_level="info",
                proxy_headers=False,
            )
    finally:
        pool.close()
