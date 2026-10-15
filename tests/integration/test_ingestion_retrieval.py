from pathlib import Path

import pytest
from psycopg_pool import ConnectionPool

from core.llm.fake_embedder import FakeEmbedder
from core.retrieval import search
from ingestion.pipeline import ingest_directory, load_manifest

pytestmark = pytest.mark.integration
MANUALS = Path(__file__).resolve().parents[2] / "data" / "manuals"
MIN_SCORE = 0.15


async def test_reingest_is_skipped_unless_forced(ingested: ConnectionPool) -> None:
    emb = FakeEmbedder()
    again = await ingest_directory(ingested, emb, MANUALS)
    assert again.ingested == []
    assert len(again.skipped) == len(load_manifest(MANUALS))
    forced = await ingest_directory(ingested, emb, MANUALS, force=True)
    assert len(forced.ingested) == len(load_manifest(MANUALS))


def test_chunks_have_metadata(ingested: ConnectionPool) -> None:
    with ingested.connection() as conn:
        row = conn.execute(
            """
            SELECT count(*), count(DISTINCT document_id), min(page), max(page)
            FROM chunks WHERE embedding_model = 'fake-hash-v1'
            """
        ).fetchone()
        restricted = conn.execute(
            """
            SELECT DISTINCT d.doc_id FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE c.access_level = 'technician'
            """
        ).fetchall()
    assert row is not None
    assert row[0] > 50
    assert (row[1], row[2], row[3]) == (11, 1, 5)
    assert restricted == [("M-ETP-05",)]


async def test_search_finds_the_right_page(ingested: ConnectionPool) -> None:
    result = await search(
        ingested,
        FakeEmbedder(),
        "What is the torque for the impeller nut on P-100/250?",
        role="viewer",
        machine_type="pump",
        min_score=MIN_SCORE,
    )
    top = result.chunks[0]
    assert (top.doc_id, top.page) == ("P-MT-02", 4)
    assert "135 Nm" in top.content


async def test_threshold_rejects_unrelated_questions(ingested: ConnectionPool) -> None:
    result = await search(
        ingested,
        FakeEmbedder(),
        "Who won the football world cup in 2018?",
        role="technician",
        min_score=MIN_SCORE,
    )
    assert result.chunks == []
    assert result.rejected > 0
    assert result.best_score is not None


async def test_viewer_cannot_retrieve_restricted_documents(ingested: ConnectionPool) -> None:
    query = "insulation resistance test voltage megger polarization index"
    viewer = await search(ingested, FakeEmbedder(), query, role="viewer", top_k=10)
    tech = await search(ingested, FakeEmbedder(), query, role="technician", top_k=10)
    assert all(c.doc_id != "M-ETP-05" for c in viewer.chunks)
    assert tech.chunks[0].doc_id == "M-ETP-05"


async def test_machine_type_filter_keeps_general_documents(ingested: ConnectionPool) -> None:
    result = await search(
        ingested,
        FakeEmbedder(),
        "lockout tagout steps and alarm limits",
        role="viewer",
        machine_type="compressor",
        top_k=20,
    )
    assert {c.machine_type for c in result.chunks} <= {"compressor", "general"}
    assert any(c.machine_type == "general" for c in result.chunks)
