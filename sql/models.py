from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class SqlProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    sql: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sql")
    @classmethod
    def validate_non_empty_sql(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("SQL proposal cannot be empty.")
        return value.strip()


class SemanticColumn(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    description: str
    source_columns: tuple[str, ...] = ()


class SemanticView(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    columns: dict[str, SemanticColumn]


class SemanticContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile: str
    dataset_version: str
    data_as_of: str
    semantic_schema_version: str
    policy_version: str
    views: dict[str, SemanticView]
    relations: tuple[dict[str, str], ...] = ()
    kpis: dict[str, str] = Field(default_factory=dict)
    ambiguities: dict[str, str] = Field(default_factory=dict)
    examples: tuple[dict[str, Any], ...] = ()

    @property
    def allowed_views(self) -> frozenset[str]:
        return frozenset(self.views)

    def allowed_columns(self, view_name: str) -> frozenset[str]:
        view = self.views.get(view_name)
        if view is None:
            return frozenset()
        return frozenset(view.columns)


class ResolvedQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    sql: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    views: tuple[str, ...]
    columns: tuple[str, ...]
    max_rows: int


class QueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sql: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    columns: list[str]
    rows: list[list[Any]]
    backend: str
    dataset_version: str = ""
    data_as_of: str = ""
    semantic_schema_version: str = ""
    policy_version: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def row_count(self) -> int:
        return len(self.rows)


class SqlToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
