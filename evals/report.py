from __future__ import annotations

from datetime import UTC, datetime

from evals.metrics import (
    CaseResult,
    Summary,
    blocked,
    citation_correct,
    fact_coverage,
    retrieval_hit,
)


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def summary_table(summary: Summary, *, full: bool) -> str:
    na = "n/a (offline)"
    c = summary.counts
    rows = [
        (
            "Retrieval hit rate (top-5)",
            _pct(summary.retrieval_hit_rate),
            f"{c['answerable']} answerable questions: expected document page retrieved",
        ),
        ("Retrieval MRR", f"{summary.mrr:.2f}", "rank of the first expected page"),
        (
            "Citation correctness",
            _pct(summary.citation_correctness) if full else na,
            "answer cites an expected document page",
        ),
        (
            "Citation precision (document)",
            _pct(summary.citation_precision) if full else na,
            "cited documents that are among the expected ones",
        ),
        (
            "Answer fact coverage",
            _pct(summary.fact_coverage) if full else na,
            "expected key facts present in the answer",
        ),
        (
            "Refusal accuracy",
            _pct(summary.refusal_accuracy),
            f"{c['unanswerable']} questions outside the documents answered with I don't know",
        ),
        (
            "False refusal rate",
            _pct(summary.false_refusal_rate),
            "answerable questions wrongly refused (lower is better)",
        ),
        (
            "Blocked unsafe rate",
            _pct(summary.blocked_unsafe_rate),
            f"{c['unsafe']} unsafe requests (unauthorised writes, injections, restricted docs)",
        ),
    ]
    lines = ["| Metric | Result | What it measures |", "|---|---|---|"]
    lines += [f"| {name} | **{value}** | {note} |" for name, value, note in rows]
    return "\n".join(lines)


def case_rows(results: list[CaseResult], *, full: bool) -> str:
    lines = [
        "| Case | Kind | Docs | Role | Retrieved | Cited | Facts | Outcome |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        kind = r.case.kind
        if kind == "answerable":
            retrieved = "yes" if retrieval_hit(r) else "**no**"
            cited = ("yes" if citation_correct(r) else "**no**") if full else "-"
            facts = _pct(fact_coverage(r)) if full else "-"
            outcome = "**refused**" if r.refused else "answered"
        elif kind == "unanswerable":
            retrieved = cited = facts = "-"
            outcome = "I don't know" if r.refused else "**answered**"
        else:
            retrieved = cited = facts = "-"
            ok, reasons = blocked(r)
            outcome = "blocked" if ok else f"**not blocked**: {'; '.join(reasons)}"
        docs = r.case.corpus if kind == "answerable" else "-"
        cells = [f"`{r.case.id}`", kind, docs, r.case.role, retrieved, cited, facts, outcome]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def corpus_table(summary: Summary, *, full: bool) -> str:
    names = {"sample": "Sample documents", "real": "Real manufacturer manuals"}
    lines = [
        "| Document set | Questions | Retrieval hit rate | MRR | Citation correctness "
        "| Fact coverage | False refusals |",
        "|---|---|---|---|---|---|---|",
    ]
    for corpus, m in summary.by_corpus.items():
        cells = [
            names.get(corpus, corpus),
            str(int(m["cases"])),
            _pct(m["retrieval_hit_rate"]),
            f"{m['mrr']:.2f}",
            _pct(m["citation_correctness"]) if full else "n/a",
            _pct(m["fact_coverage"]) if full else "n/a",
            _pct(m["false_refusal_rate"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render(
    results: list[CaseResult],
    summary: Summary,
    *,
    mode: str,
    full: bool,
    skipped: list[str] | None = None,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    skipped_note = (
        f"Skipped {len(skipped)} cases whose documents are not ingested "
        f"(run `make real-manuals` to include them): {', '.join(skipped)}."
        if skipped
        else "All cases ran."
    )
    note = (
        "Full run: answers written by the configured LLM, so answer metrics are reported."
        if full
        else "Offline run (deterministic fake planner and hashing embedder, no API key). "
        "Retrieval and safety metrics are meaningful; answer-quality metrics need "
        "`MISTRAL_API_KEY` and are shown as n/a."
    )
    return (
        "\n\n".join(
            [
                "# Evaluation results",
                f"Mode: **{mode}** · {len(results)} cases · produced {now} by `make eval`.",
                note,
                skipped_note,
                summary_table(summary, full=full),
                "## By document set",
                corpus_table(summary, full=full),
                "## Per case",
                case_rows(results, full=full),
            ]
        )
        + "\n"
    )
