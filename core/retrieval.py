from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import numpy as np
from psycopg_pool import ConnectionPool

from core.config import Role
from core.llm.base import Embedder

# Which document access levels each role may read.
READABLE_LEVELS: dict[Role, tuple[str, ...]] = {
    "viewer": ("viewer",),
    "technician": ("viewer", "technician"),
}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    doc_id: str
    document: str  # file name
    title: str
    page: int
    content: str
    score: float
    machine_type: str


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    rejected: int  # candidates found but below the relevance threshold
    best_score: float | None


async def search(
    pool: ConnectionPool,
    embedder: Embedder,
    query: str,
    *,
    role: Role,
    machine_type: str | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> RetrievalResult:
    """Top-k cosine search, filtered by role and machine type, with a relevance cut-off.

    Chunks for a specific machine type also match general documents (safety
    procedures, site standards), which apply to every machine.
    """
    [vector] = await embedder.embed([query])
    params: dict[str, object] = {
        "q": np.asarray(vector, dtype=np.float32),
        "model": embedder.name,
        "levels": list(READABLE_LEVELS[role]),
        "k": top_k,
    }
    type_filter = ""
    if machine_type:
        type_filter = "AND c.machine_type IN (%(machine_type)s, 'general')"
        params["machine_type"] = machine_type

    sql = f"""
        SELECT c.id, d.doc_id, d.filename, d.title, c.page, c.content,
               1 - (c.embedding <=> %(q)s) AS score, c.machine_type
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE c.embedding_model = %(model)s
          AND c.access_level = ANY(%(levels)s)
          {type_filter}
        ORDER BY c.embedding <=> %(q)s
        LIMIT %(k)s
    """

    def run_query() -> list[tuple[Any, ...]]:
        with pool.connection() as conn:
            return conn.execute(sql, params).fetchall()

    rows = await asyncio.to_thread(run_query)

    candidates = [
        RetrievedChunk(
            chunk_id=r[0],
            doc_id=r[1],
            document=r[2],
            title=r[3],
            page=r[4],
            content=r[5],
            score=round(float(r[6]), 4),
            machine_type=r[7],
        )
        for r in rows
    ]
    kept = [c for c in candidates if c.score >= min_score]
    return RetrievalResult(
        chunks=kept,
        rejected=len(candidates) - len(kept),
        best_score=candidates[0].score if candidates else None,
    )
