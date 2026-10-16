"""Tool input and output models.

The input models are the single source of validation: the security middleware
validates every call against them (so rejected calls are audited) and the tool
signatures reuse the same annotated types, so the JSON schema the client sees
matches what is enforced.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

_CONTROL = re.compile("[\x00-\x08\x0b-\x1f\x7f​-‏‪-‮⁠-⁤﻿]")


def _clean(value: str) -> str:
    return _CONTROL.sub("", value).strip()


Query = Annotated[
    str,
    Field(min_length=3, max_length=500, description="Question or keywords to search for."),
    AfterValidator(_clean),
]
MachineTypeParam = Annotated[
    Literal["pump", "motor", "compressor"] | None,
    Field(description="Restrict to one equipment family. General documents are always included."),
]
TopK = Annotated[int, Field(ge=1, le=10, description="Maximum number of passages to return.")]
MachineId = Annotated[
    str,
    Field(pattern=r"^[A-Za-z]-\d{1,3}$", description="Machine identifier, for example P-3."),
    AfterValidator(str.upper),
]
Minutes = Annotated[int, Field(ge=1, le=1440, description="How many minutes of history to read.")]
Title = Annotated[str, Field(min_length=5, max_length=120), AfterValidator(_clean)]
Description = Annotated[str, Field(min_length=10, max_length=2000), AfterValidator(_clean)]
Priority = Annotated[
    Literal["low", "medium", "high", "critical"],
    Field(
        description="CMS-001: warning -> medium, alarm -> high, trip or safety risk -> critical."
    ),
]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchManualsInput(_Input):
    query: Query
    machine_type: MachineTypeParam = None
    top_k: TopK = 5


class SensorReadingsInput(_Input):
    machine_id: MachineId
    minutes: Minutes = 10


class CreateTicketInput(_Input):
    machine_id: MachineId
    title: Title
    description: Description
    priority: Priority


class ListMachinesInput(_Input):
    pass


TOOL_INPUTS: dict[str, type[_Input]] = {
    "search_manuals": SearchManualsInput,
    "get_sensor_readings": SensorReadingsInput,
    "create_maintenance_ticket": CreateTicketInput,
    "list_machines": ListMachinesInput,
}


# Outputs


class Passage(BaseModel):
    doc_id: str
    document: str
    title: str
    page: int
    score: float
    text: str
    flagged: bool = Field(
        description="True if instruction-like text was removed from this passage."
    )
    findings: list[str] = []
    source_url: str | None = Field(
        default=None, description="Manufacturer URL for downloaded third-party manuals."
    )


class SearchManualsOutput(BaseModel):
    query: str
    min_score: float
    results: list[Passage]
    note: str | None = None


class MachineInfo(BaseModel):
    id: str
    name: str
    type: str
    model: str
    location: str
    rated_current_a: float
    data_source: str = Field(
        description="Where the readings come from: 'simulated', or the name of a replayed dataset."
    )


class ReadingOut(BaseModel):
    ts: str
    temperature_c: float | None
    vibration_mm_s: float | None
    pressure_bar: float | None
    current_a: float | None
    bearing_accel_g: float | None = None
    load_duty_pct: float | None = None


class FlagOut(BaseModel):
    metric: str
    level: Literal["warning", "alarm"]
    value: float
    limit: float
    message: str
    source: str


class StatsOut(BaseModel):
    latest: float
    min: float
    max: float
    mean: float


class SensorReadingsOutput(BaseModel):
    machine: MachineInfo
    window_minutes: int
    count: int
    status: Literal["ok", "warning", "alarm", "no_data"]
    flags: list[FlagOut]
    stats: dict[str, StatsOut]
    recent: list[ReadingOut] = Field(description="Most recent readings, newest last.")


class MachineStatus(MachineInfo):
    status: Literal["ok", "warning", "alarm", "no_data"]
    flags: list[FlagOut]
    latest: ReadingOut | None


class ListMachinesOutput(BaseModel):
    machines: list[MachineStatus]


class TicketOut(BaseModel):
    ticket_id: int
    machine_id: str
    title: str
    description: str
    priority: str
    status: str
    created_by: str
    created_at: str
