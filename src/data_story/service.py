"""Shared orchestration and error translation; adapters contain no domain logic."""

import logging
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .configuration import InstructionStore
from .contracts import (
    DatasetPreview,
    DatasetTable,
    DatasetView,
    ErrorInfo,
    EventView,
    Failure,
    FieldIssue,
    InstructionUpdate,
    InstructionView,
    MetadataIssue,
    MetadataSourceView,
    MetadataText,
    MetadataUpdate,
    MetadataView,
    ProjectCreate,
    ProjectId,
    ProjectTypeView,
    ProjectView,
    Success,
)
from .datasets import DatasetError, DatasetNotFound, DatasetStore
from .metadata import MetadataError, MetadataStore, issues
from .project_types import PROJECT_TYPES
from .projects import ProjectNotFound, ProjectStore

T = TypeVar("T")
SchemaT = TypeVar("SchemaT", bound=BaseModel)
LOG = logging.getLogger(__name__)


class UnknownProjectType(LookupError):
    """A requested project type does not exist."""


class InputValidation(Exception):
    def __init__(self, error: ValidationError):
        self.error = error


def validate_input(schema: type[SchemaT], raw: object) -> SchemaT:
    try:
        return schema.model_validate(raw)
    except ValidationError as error:
        raise InputValidation(error) from error


def validation_failure(errors: Sequence[Mapping[str, Any]]) -> Failure:
    issues = [
        FieldIssue(
            field=".".join(map(str, item["loc"])),
            message=str(item["msg"]).removeprefix("Value error, "),
        )
        for item in errors
    ]
    return Failure(
        error=ErrorInfo(code="invalid_input", message="Перевірте введені дані.", fields=issues)
    )


def execute(action: Callable[[], T]) -> Success[T] | Failure:
    try:
        return Success(data=action())
    except InputValidation as error:
        return validation_failure(error.error.errors(include_input=False))
    except (DatasetError, MetadataError) as error:
        return Failure(
            error=ErrorInfo(
                code="invalid_input",
                message=str(error),
                fields=[FieldIssue(field="file", message=str(error))],
            )
        )
    except (ProjectNotFound, UnknownProjectType, DatasetNotFound) as error:
        return Failure(error=ErrorInfo(code="not_found", message=str(error)))
    except sqlite3.Error:
        LOG.error("Project operation failed: storage_error")
        return Failure(
            error=ErrorInfo(
                code="storage_error",
                message="Не вдалося зберегти або прочитати дані. Спробуйте ще раз.",
            )
        )
    except Exception:
        LOG.error("Project operation failed: internal_error")
        return Failure(
            error=ErrorInfo(
                code="internal_error",
                message="Не вдалося виконати дію. Дані не показані як успішно змінені.",
            )
        )


class ProjectService:
    def __init__(
        self,
        store: ProjectStore,
        instructions: InstructionStore | None = None,
        datasets: DatasetStore | None = None,
    ):
        self.store = store
        self.instructions = instructions or InstructionStore(store.database)
        self.datasets = datasets or DatasetStore(store.database)
        self.metadata_store = MetadataStore(store.database, self.datasets)

    def create(self, raw: object) -> Success[ProjectView] | Failure:
        def action() -> ProjectView:
            request = validate_input(ProjectCreate, raw)
            project = self.store.create(request.name, request.purpose, request.project_type)
            return ProjectView.model_validate(project)

        return execute(action)

    def list_projects(self) -> Success[list[ProjectView]] | Failure:
        return execute(
            lambda: [ProjectView.model_validate(project) for project in self.store.list_projects()]
        )

    def get(self, project_id: str, *, opened: bool = False) -> Success[ProjectView] | Failure:
        def action() -> ProjectView:
            validated = str(validate_input(ProjectId, {"id": project_id}).id)
            project = self.store.open(validated) if opened else self.store.get(validated)
            return ProjectView.model_validate(project)

        return execute(action)

    def events(self, project_id: str) -> Success[list[EventView]] | Failure:
        def action() -> list[EventView]:
            validated = str(validate_input(ProjectId, {"id": project_id}).id)
            return [EventView.model_validate(event) for event in self.store.events(validated)]

        return execute(action)

    def project_types(self) -> Success[list[ProjectTypeView]] | Failure:
        return execute(
            lambda: [ProjectTypeView.model_validate(item) for item in PROJECT_TYPES.values()]
        )

    def instruction(self, project_type: str) -> Success[InstructionView] | Failure:
        def action() -> InstructionView:
            return InstructionView.model_validate(self.instructions.get(_known(project_type)))

        return execute(action)

    def save_instruction(
        self, project_type: str, raw: object
    ) -> Success[InstructionView] | Failure:
        def action() -> InstructionView:
            key = _known(project_type)
            request = validate_input(InstructionUpdate, raw)
            return InstructionView.model_validate(self.instructions.save(key, request.text))

        return execute(action)

    def reset_instruction(self, project_type: str) -> Success[InstructionView] | Failure:
        return execute(
            lambda: InstructionView.model_validate(self.instructions.reset(_known(project_type)))
        )

    def upload(
        self, project_id: str, filename: object, content: bytes
    ) -> Success[DatasetView] | Failure:
        def action() -> DatasetView:
            validated = str(validate_input(ProjectId, {"id": project_id}).id)
            return DatasetView.from_dataset(self.datasets.add(validated, filename, content))

        return execute(action)

    def list_datasets(self, project_id: str) -> Success[list[DatasetView]] | Failure:
        def action() -> list[DatasetView]:
            validated = str(validate_input(ProjectId, {"id": project_id}).id)
            return [DatasetView.from_dataset(d) for d in self.datasets.list_datasets(validated)]

        return execute(action)

    def dataset(self, dataset_id: str) -> Success[DatasetView] | Failure:
        def action() -> DatasetView:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            return DatasetView.from_dataset(self.datasets.get(validated))

        return execute(action)

    def preview(self, dataset_id: str) -> Success[DatasetPreview] | Failure:
        def action() -> DatasetPreview:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            return DatasetPreview.model_validate(self.datasets.preview(validated))

        return execute(action)

    def table(self, dataset_id: str) -> Success[DatasetTable] | Failure:
        def action() -> DatasetTable:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            return DatasetTable.model_validate(self.datasets.table(validated))

        return execute(action)

    def _metadata_view(self, item) -> MetadataView:
        return MetadataView(
            dataset_id=item.dataset_id,
            document=item.document,
            saved=item.saved,
            updated_at=item.updated_at,
            confirmed_at=item.confirmed_at,
            issues=[
                MetadataIssue(column=i.column, level=i.level, message=i.message)
                for i in issues(item.document)
            ],
        )

    def metadata(self, dataset_id: str) -> Success[MetadataView] | Failure:
        def action() -> MetadataView:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            return self._metadata_view(self.metadata_store.get(validated))

        return execute(action)

    def save_metadata(self, dataset_id: str, raw: object) -> Success[MetadataView] | Failure:
        def action() -> MetadataView:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            request = validate_input(MetadataUpdate, raw)
            saved = self.metadata_store.save(
                validated, request.document.model_dump(), confirm=request.confirm
            )
            return self._metadata_view(saved)

        return execute(action)

    def add_metadata_text(
        self, dataset_id: str, raw: object
    ) -> Success[MetadataSourceView] | Failure:
        def action() -> MetadataSourceView:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            request = validate_input(MetadataText, raw)
            source = self.metadata_store.add_text(validated, request.text)
            return MetadataSourceView.model_validate(source)

        return execute(action)

    def add_metadata_file(
        self, dataset_id: str, filename: object, content: bytes
    ) -> Success[MetadataSourceView] | Failure:
        def action() -> MetadataSourceView:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            source = self.metadata_store.add_file(validated, filename, content)
            return MetadataSourceView.model_validate(source)

        return execute(action)

    def metadata_sources(self, dataset_id: str) -> Success[list[MetadataSourceView]] | Failure:
        def action() -> list[MetadataSourceView]:
            validated = str(validate_input(ProjectId, {"id": dataset_id}).id)
            return [
                MetadataSourceView.model_validate(s) for s in self.metadata_store.sources(validated)
            ]

        return execute(action)


def _known(project_type: str) -> str:
    if project_type not in PROJECT_TYPES:
        raise UnknownProjectType("Тип проєкту не знайдено.")
    return project_type
