"""One public contract for UI, HTTP adapters, and future tool calls."""

from typing import Annotated, Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .configuration import INSTRUCTION_LIMIT
from .metadata import MetadataDocument
from .project_types import DEFAULT_TYPE, ProjectTypeKey, require_enabled
from .validation import NAME_LIMIT, PURPOSE_LIMIT, text

T = TypeVar("T")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProjectCreate(StrictModel):
    name: Annotated[str, Field(strict=True, min_length=1, max_length=NAME_LIMIT)]
    purpose: Annotated[str, Field(strict=True, max_length=PURPOSE_LIMIT)] = ""
    project_type: ProjectTypeKey = DEFAULT_TYPE

    @field_validator("project_type", mode="before")
    @classmethod
    def type_value(cls, value: object) -> str:
        return require_enabled(value)

    @field_validator("name", mode="before")
    @classmethod
    def name_value(cls, value: object) -> str:
        return text(value, "Назва", NAME_LIMIT, required=True)

    @field_validator("purpose", mode="before")
    @classmethod
    def purpose_value(cls, value: object) -> str:
        return text(value, "Мета", PURPOSE_LIMIT)


class ProjectId(StrictModel):
    id: UUID


class ProjectView(StrictModel):
    id: UUID
    name: Annotated[str, Field(strict=True, min_length=1, max_length=NAME_LIMIT)]
    purpose: Annotated[str, Field(strict=True, max_length=PURPOSE_LIMIT)]
    created_at: AwareDatetime
    project_type: ProjectTypeKey


class ProjectTypeView(StrictModel):
    key: ProjectTypeKey
    title: str
    description: str
    icon: str
    enabled: bool


class InstructionView(StrictModel):
    project_type: ProjectTypeKey
    text: str
    is_default: bool
    updated_at: AwareDatetime | None


class InstructionUpdate(StrictModel):
    text: Annotated[str, Field(strict=True, min_length=1, max_length=INSTRUCTION_LIMIT)]

    @field_validator("text", mode="before")
    @classmethod
    def text_value(cls, value: object) -> str:
        return text(value, "Інструкція", INSTRUCTION_LIMIT, required=True)


class EventView(StrictModel):
    id: UUID
    project_id: UUID
    operation: Literal[
        "project.created",
        "project.opened",
        "dataset.uploaded",
        "metadata.saved",
        "metadata.confirmed",
        "metadata.source_added",
    ]
    occurred_at: AwareDatetime
    payload: dict[str, str]


class ColumnProfile(StrictModel):
    name: str
    kind: Literal["number", "text", "date", "bool"]
    missing: int
    unique: int
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    date_format: str | None = None
    date_ambiguous: bool = False
    first: str | None = None
    last: str | None = None


class DatasetView(StrictModel):
    id: UUID
    project_id: UUID
    name: str
    file_format: Literal["csv"]
    size_bytes: int
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    source: dict[str, str]
    created_at: AwareDatetime

    @classmethod
    def from_dataset(cls, dataset) -> "DatasetView":
        details = dict(dataset.profile)
        columns = details.pop("columns", [])
        return cls(
            id=dataset.id,
            project_id=dataset.project_id,
            name=dataset.name,
            file_format=dataset.file_format,
            size_bytes=dataset.size_bytes,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            columns=[ColumnProfile.model_validate(c) for c in columns],
            source={k: str(v) for k, v in details.items()},
            created_at=dataset.created_at,
        )


class DatasetPreview(StrictModel):
    columns: list[str]
    rows: list[list[str | None]]
    total_rows: int


class SortItem(StrictModel):
    colId: Annotated[str, Field(strict=True, pattern=r"^c\d{1,4}$")]
    sort: Literal["asc", "desc"]


class RowsQuery(StrictModel):
    """One page request from the grid (AG Grid infinite row model): rows start..start+limit
    after the grid's filter model and sort model are applied on the server."""

    start: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=500)] = 100
    sort: Annotated[list[SortItem], Field(max_length=50)] = []
    filter: dict[str, dict[str, Any]] = {}


class RowsPage(StrictModel):
    rows: list[dict[str, int | float | str | None]]
    total: int
    all_rows: int


class MetadataIssue(StrictModel):
    column: str
    level: Literal["warning", "info"]
    message: str


class MetadataView(StrictModel):
    dataset_id: UUID
    document: MetadataDocument
    saved: bool
    updated_at: AwareDatetime | None
    confirmed_at: AwareDatetime | None
    issues: list[MetadataIssue]


class MetadataUpdate(StrictModel):
    document: MetadataDocument
    confirm: bool = False


class MetadataText(StrictModel):
    text: Annotated[str, Field(strict=True, min_length=1, max_length=50_000)]


class MetadataSourceView(StrictModel):
    id: UUID
    dataset_id: UUID
    kind: Literal["file", "text"]
    name: str
    text: str
    created_at: AwareDatetime


class FieldIssue(StrictModel):
    field: str
    message: str


class ErrorInfo(StrictModel):
    code: Literal["invalid_input", "not_found", "storage_error", "internal_error"]
    message: str
    fields: list[FieldIssue] = Field(default_factory=list)


class Success(StrictModel, Generic[T]):
    status: Literal["ok"] = "ok"
    data: T


class Failure(StrictModel):
    status: Literal["error"] = "error"
    error: ErrorInfo


HTTP_STATUS = {"invalid_input": 422, "not_found": 404, "storage_error": 503, "internal_error": 500}
