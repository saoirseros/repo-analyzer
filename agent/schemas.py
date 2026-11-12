"""Structured output models for repository analysis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalysisModel(BaseModel):
    """Base for strict report structures returned by the analysis model."""

    model_config = ConfigDict(extra="forbid")


class ArchitectureComponent(AnalysisModel):
    name: str = Field(description="Component name, as identified in the repository.")
    description: str = Field(description="Responsibilities of this component.")
    files: list[str] = Field(
        default_factory=list,
        description="Inspected repository file paths that support this description.",
    )


class CodeQualityIssue(AnalysisModel):
    title: str
    severity: Literal["low", "medium", "high"]
    description: str
    evidence: str = Field(description="A concise explanation grounded in inspected code.")
    files: list[str] = Field(
        default_factory=list,
        description="Inspected repository file paths supporting this issue.",
    )


class ImprovementSuggestion(AnalysisModel):
    title: str
    priority: Literal["low", "medium", "high"]
    rationale: str
    suggested_action: str
    files: list[str] = Field(
        default_factory=list,
        description="Inspected repository file paths related to this suggestion.",
    )


class RepositoryAnalysisReport(AnalysisModel):
    repository_url: str
    summary: str
    architecture_overview: str
    components: list[ArchitectureComponent] = Field(default_factory=list)
    data_flow: str
    tech_stack: list[str] = Field(default_factory=list)
    code_quality_issues: list[CodeQualityIssue] = Field(default_factory=list)
    improvements: list[ImprovementSuggestion] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=list,
        description="Important evidence gaps or analysis constraints.",
    )
