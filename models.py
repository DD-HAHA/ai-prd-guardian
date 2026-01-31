from pydantic import BaseModel, Field
from typing import List


class Finding(BaseModel):
    id: str
    title: str
    severity: str  # P0 / P1 / P2
    rationale: str


class Advice(BaseModel):
    for_pm: str
    for_eng: str


class PanelItem(BaseModel):
    role: str
    findings: List[Finding]
    advice: Advice
    score: int = Field(ge=0, le=100)


class ExecSummary(BaseModel):
    total_score: int = Field(ge=0, le=100)
    blockers: List[str]
    decision: str
    items: List[PanelItem]
