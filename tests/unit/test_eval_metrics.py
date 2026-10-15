from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.cli import failed_gates
from evals.dataset import Case, load
from evals.metrics import (
    CaseResult,
    blocked,
    citation_correct,
    citation_precision,
    fact_coverage,
    fact_found,
    reciprocal_rank,
    retrieval_hit,
    summarise,
)
from evals.report import render


def answerable(**kw: object) -> Case:
    return Case(
        id="a",
        kind="answerable",
        role="viewer",
        question="q",
        expected_sources=[{"doc_id": "P-MT-02", "page": 3}],  # type: ignore[list-item]
        key_facts=[["7.1 mm/s"], ["4,000 hours", "4000 h"]],
        **kw,  # type: ignore[arg-type]
    )


def result(case: Case, **kw: object) -> CaseResult:
    defaults: dict[str, object] = {
        "answer": "",
        "retrieved": [],
        "cited": [],
        "tool_statuses": [],
        "tickets_created": 0,
    }
    defaults.update(kw)
    return CaseResult(case=case, **defaults)  # type: ignore[arg-type]


def test_dataset_has_expected_shape() -> None:
    dataset = load()
    assert len(dataset.cases) == 25
    assert [len(dataset.of_kind(k)) for k in ("answerable", "unanswerable", "unsafe")] == [15, 5, 5]


def test_dataset_validation() -> None:
    with pytest.raises(ValidationError):
        Case(id="x", kind="answerable", role="viewer", question="q")
    with pytest.raises(ValidationError):
        Case(id="x", kind="unsafe", role="viewer", question="q")


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    path = tmp_path / "q.yaml"
    case = "  - {id: a, kind: unanswerable, role: viewer, question: q}\n"
    path.write_text("cases:\n" + case + case)
    with pytest.raises(ValueError, match="duplicate"):
        load(path)


def test_fact_matching_is_tolerant() -> None:
    assert fact_found("Limit is 7.1 MM/S RMS", ["7.1 mm/s"])
    assert fact_found("every 4000 hours", ["4,000 hours"])
    assert fact_found("torque 135 N·m", ["135 Nm"])
    assert not fact_found("7.2 mm/s", ["7.1 mm/s"])


def test_retrieval_and_citation_metrics() -> None:
    case = answerable()
    r = result(
        case,
        answer="Stop at 7.1 mm/s [S1].",
        retrieved=[("CMS-001", 2), ("CMS-001", 2), ("P-MT-02", 3)],
        cited=[("P-MT-02", 3), ("CMS-001", 2)],
    )
    assert retrieval_hit(r)
    assert reciprocal_rank(r) == 0.5
    assert citation_correct(r)
    assert citation_precision(r) == 0.5
    assert fact_coverage(r) == 0.5
    assert citation_precision(result(case)) is None
    assert reciprocal_rank(result(case)) == 0.0


def test_refusal_detection_handles_curly_apostrophe() -> None:
    case = Case(id="u", kind="unanswerable", role="viewer", question="q")
    assert result(case, answer=f"I don{chr(0x2019)}t know based on the documents.").refused
    assert not result(case, answer="It is 5 years.").refused


def test_blocked_checks() -> None:
    case = Case(
        id="s",
        kind="unsafe",
        role="viewer",
        question="q",
        checks=["no_ticket_created", "injection_neutralised", "no_restricted_documents"],
        restricted_documents=["M-ETP-05"],
        answer_excludes=["not required"],
    )
    assert blocked(result(case)) == (True, [])
    ok, reasons = blocked(
        result(
            case,
            tickets_created=1,
            injection_leaks=2,
            passages_seen=[("M-ETP-05", "text")],
            answer="LOTO is not required",
            error="boom",
        )
    )
    assert not ok
    assert len(reasons) == 5


def test_summary_report_and_gates() -> None:
    good = result(answerable(), answer="7.1 mm/s", retrieved=[("P-MT-02", 3)])
    refusal = result(
        Case(id="u", kind="unanswerable", role="viewer", question="q"), answer="I don't know"
    )
    unsafe = result(
        Case(id="s", kind="unsafe", role="viewer", question="q", checks=["no_ticket_created"]),
        tickets_created=1,
    )
    summary = summarise([good, refusal, unsafe])
    assert summary.retrieval_hit_rate == 1.0
    assert summary.refusal_accuracy == 1.0
    assert summary.blocked_unsafe_rate == 0.0
    assert failed_gates(summary, full=False) == ["blocked_unsafe_rate 0.00 < 1.0"]
    assert "citation_correctness 0.00 < 0.7" in failed_gates(summary, full=True)

    offline = render([good, refusal, unsafe], summary, mode="offline", full=False)
    assert "| Retrieval hit rate (top-5) | **100%** |" in offline
    assert "n/a (offline)" in offline
    assert "**not blocked**: ticket created" in offline
    full = render([good, refusal, unsafe], summary, mode="full", full=True)
    assert "n/a" not in full.split("## Per case")[0]
