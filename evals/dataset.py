from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.config import Role

DEFAULT_PATH = Path(__file__).with_name("questions.yaml")

Check = Literal["no_ticket_created", "injection_neutralised", "no_restricted_documents"]


class Source(BaseModel):
    doc_id: str
    page: int


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["answerable", "unanswerable", "unsafe"]
    role: Role
    question: str
    # "real": answered from downloaded manufacturer manuals rather than the sample documents
    corpus: Literal["sample", "real"] = "sample"
    expected_sources: list[Source] = []
    key_facts: list[list[str]] = []
    checks: list[Check] = []
    answer_excludes: list[str] = []
    restricted_documents: list[str] = []

    @model_validator(mode="after")
    def _consistent(self) -> Case:
        if self.kind == "answerable" and not (self.expected_sources and self.key_facts):
            raise ValueError(f"{self.id}: answerable cases need sources and key facts")
        if self.kind == "unsafe" and not self.checks:
            raise ValueError(f"{self.id}: unsafe cases need checks")
        return self


class Dataset(BaseModel):
    cases: list[Case] = Field(min_length=1)

    def of_kind(self, kind: str) -> list[Case]:
        return [c for c in self.cases if c.kind == kind]


def load(path: Path = DEFAULT_PATH) -> Dataset:
    dataset = Dataset.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    ids = [c.id for c in dataset.cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids")
    return dataset
