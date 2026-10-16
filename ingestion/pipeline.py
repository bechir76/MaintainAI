from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from psycopg_pool import ConnectionPool

from core.llm.base import Embedder
from ingestion.chunking import chunk_pages
from ingestion.pdf import parse_pdf

log = logging.getLogger(__name__)

# Bump when parsing or chunking changes so existing documents are re-ingested.
PIPELINE_VERSION = 3


@dataclass(frozen=True)
class DocumentMeta:
    file: str
    doc_id: str
    title: str
    machine_type: str
    access_level: str
    source_url: str | None = None  # where a downloaded manufacturer manual came from


@dataclass(frozen=True)
class IngestReport:
    ingested: list[str]
    skipped: list[str]
    chunks: int


def load_manifest(directory: Path) -> list[DocumentMeta]:
    data: dict[str, Any] = yaml.safe_load((directory / "manifest.yaml").read_text("utf-8"))
    return [
        DocumentMeta(
            file=d["file"],
            doc_id=d["doc_id"],
            title=d["title"],
            machine_type=d["machine_type"],
            access_level=d["access_level"],
            source_url=d.get("source_url"),
        )
        for d in data["documents"]
    ]


def embedding_text(title: str, chunk: str) -> str:
    # Prefixing the document title gives every chunk its context (equipment
    # family, document type), which helps short, ambiguous chunks such as table rows.
    return f"{title}\n{chunk}"


async def ingest_document(
    pool: ConnectionPool,
    embedder: Embedder,
    path: Path,
    meta: DocumentMeta,
    *,
    chunk_size: int,
    chunk_overlap: int,
    force: bool = False,
) -> int | None:
    """Ingest one PDF. Returns the number of chunks, or None if it was already up to date."""
    # Re-ingest when the file, the parsing/chunking code or the chunk settings change.
    settings_key = f"{PIPELINE_VERSION}:{chunk_size}:{chunk_overlap}".encode()
    sha = hashlib.sha256(path.read_bytes() + settings_key).hexdigest()
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT d.sha256,
                   (SELECT min(c.embedding_model) FROM chunks c WHERE c.document_id = d.id)
            FROM documents d WHERE d.doc_id = %s
            """,
            (meta.doc_id,),
        ).fetchone()
    if row and row[0] == sha and row[1] == embedder.name and not force:
        return None

    pages = parse_pdf(path)
    chunks = chunk_pages(pages, chunk_size, chunk_overlap)
    vectors = await embedder.embed([embedding_text(meta.title, c.text) for c in chunks])

    with pool.connection() as conn, conn.transaction():
        conn.execute("DELETE FROM documents WHERE doc_id = %s", (meta.doc_id,))
        doc_row = conn.execute(
            """
            INSERT INTO documents
                (doc_id, filename, title, machine_type, access_level, pages, sha256,
                 source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                meta.doc_id,
                meta.file,
                meta.title,
                meta.machine_type,
                meta.access_level,
                len(pages),
                sha,
                meta.source_url,
            ),
        ).fetchone()
        assert doc_row is not None
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO chunks (document_id, page, chunk_index, content, machine_type,
                                    access_level, embedding_model, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        doc_row[0],
                        c.page,
                        c.index,
                        c.text,
                        meta.machine_type,
                        meta.access_level,
                        embedder.name,
                        np.asarray(v, dtype=np.float32),
                    )
                    for c, v in zip(chunks, vectors, strict=True)
                ],
            )
    return len(chunks)


async def ingest_directory(
    pool: ConnectionPool,
    embedder: Embedder,
    directory: Path,
    *,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
    force: bool = False,
) -> IngestReport:
    ingested, skipped, total = [], [], 0
    for meta in load_manifest(directory):
        count = await ingest_document(
            pool,
            embedder,
            directory / meta.file,
            meta,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            force=force,
        )
        if count is None:
            skipped.append(meta.doc_id)
            log.info("%s unchanged, skipped", meta.doc_id)
        else:
            ingested.append(meta.doc_id)
            total += count
            log.info("%s: %d chunks", meta.doc_id, count)
    return IngestReport(ingested=ingested, skipped=skipped, chunks=total)
