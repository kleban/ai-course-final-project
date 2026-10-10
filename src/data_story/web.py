"""Thin NiceGUI and HTTP adapters over the same project service."""

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from nicegui import app, ui

from .config import Settings
from .contracts import (
    HTTP_STATUS,
    DatasetCandidate,
    DatasetCopyRequest,
    DatasetPreview,
    DatasetView,
    EventView,
    Failure,
    InstructionUpdate,
    InstructionView,
    MetadataSourceView,
    MetadataText,
    MetadataUpdate,
    MetadataView,
    ProjectCreate,
    ProjectTypeView,
    ProjectView,
    RowsPage,
    RowsQuery,
    StatisticsPage,
    StatisticsQuery,
    Success,
)
from .datasets import MAX_BYTES
from .metadata import SOURCE_BYTES
from .projects import ProjectStore
from .screen import icons_screen, projects_screen, settings_screen
from .service import ProjectService, validation_failure


def router(service: ProjectService) -> APIRouter:
    api = APIRouter(prefix="/api")

    def response(result):
        status = HTTP_STATUS[result.error.code] if isinstance(result, Failure) else 200
        return JSONResponse(result.model_dump(mode="json"), status_code=status)

    @api.get("/projects", response_model=Success[list[ProjectView]] | Failure)
    def list_projects():
        return response(service.list_projects())

    @api.post("/projects/{project_id}/statistics", response_model=Success[StatisticsPage] | Failure)
    def statistics(project_id: str, query: StatisticsQuery):
        return response(service.statistics(project_id, query.model_dump(mode="json")))

    @api.post(
        "/projects",
        response_model=Success[ProjectView] | Failure,
        responses={422: {"model": Failure}},
    )
    def create_project(request: ProjectCreate):
        return response(service.create(request))

    @api.get("/projects/{project_id}", response_model=Success[ProjectView] | Failure)
    def get_project(project_id: str):
        return response(service.get(project_id))

    @api.post("/projects/{project_id}/open", response_model=Success[ProjectView] | Failure)
    def open_project(project_id: str):
        return response(service.get(project_id, opened=True))

    @api.get("/projects/{project_id}/events", response_model=Success[list[EventView]] | Failure)
    def events(project_id: str):
        return response(service.events(project_id))

    @api.post(
        "/projects/{project_id}/datasets",
        response_model=Success[DatasetView] | Failure,
        responses={422: {"model": Failure}},
    )
    async def upload_dataset(project_id: str, file: UploadFile):
        content = await file.read(MAX_BYTES + 1)
        return response(service.upload(project_id, file.filename, content))

    @api.get("/projects/{project_id}/datasets", response_model=Success[list[DatasetView]] | Failure)
    def list_datasets(project_id: str):
        return response(service.list_datasets(project_id))

    @api.get("/datasets/{dataset_id}", response_model=Success[DatasetView] | Failure)
    def get_dataset(dataset_id: str):
        return response(service.dataset(dataset_id))

    @api.get(
        "/projects/{project_id}/dataset-candidates",
        response_model=Success[list[DatasetCandidate]] | Failure,
    )
    def dataset_candidates(project_id: str):
        return response(service.dataset_candidates(project_id))

    @api.post(
        "/projects/{project_id}/datasets/copy",
        response_model=Success[DatasetView] | Failure,
        responses={422: {"model": Failure}},
    )
    def copy_dataset(project_id: str, request: DatasetCopyRequest):
        return response(service.copy_dataset(project_id, request))

    @api.get("/datasets/{dataset_id}/preview", response_model=Success[DatasetPreview] | Failure)
    def preview_dataset(dataset_id: str):
        return response(service.preview(dataset_id))

    @api.post(
        "/datasets/{dataset_id}/rows",
        response_model=Success[RowsPage] | Failure,
        responses={422: {"model": Failure}},
    )
    def dataset_rows(dataset_id: str, request: RowsQuery):
        return response(service.rows(dataset_id, request))

    @api.get("/datasets/{dataset_id}/metadata", response_model=Success[MetadataView] | Failure)
    def get_metadata(dataset_id: str):
        return response(service.metadata(dataset_id))

    @api.put(
        "/datasets/{dataset_id}/metadata",
        response_model=Success[MetadataView] | Failure,
        responses={422: {"model": Failure}},
    )
    def save_metadata(dataset_id: str, request: MetadataUpdate):
        return response(service.save_metadata(dataset_id, request.model_dump()))

    @api.get(
        "/datasets/{dataset_id}/metadata/sources",
        response_model=Success[list[MetadataSourceView]] | Failure,
    )
    def metadata_sources(dataset_id: str):
        return response(service.metadata_sources(dataset_id))

    @api.post(
        "/datasets/{dataset_id}/metadata/sources/text",
        response_model=Success[MetadataSourceView] | Failure,
        responses={422: {"model": Failure}},
    )
    def add_metadata_text(dataset_id: str, request: MetadataText):
        return response(service.add_metadata_text(dataset_id, request.model_dump()))

    @api.post(
        "/datasets/{dataset_id}/metadata/sources/file",
        response_model=Success[MetadataSourceView] | Failure,
        responses={422: {"model": Failure}},
    )
    async def add_metadata_file(dataset_id: str, file: UploadFile):
        content = await file.read(SOURCE_BYTES + 1)
        return response(service.add_metadata_file(dataset_id, file.filename, content))

    @api.get("/project-types", response_model=Success[list[ProjectTypeView]] | Failure)
    def project_types():
        return response(service.project_types())

    @api.get(
        "/project-types/{project_type}/instruction",
        response_model=Success[InstructionView] | Failure,
    )
    def instruction(project_type: str):
        return response(service.instruction(project_type))

    @api.put(
        "/project-types/{project_type}/instruction",
        response_model=Success[InstructionView] | Failure,
        responses={422: {"model": Failure}},
    )
    def save_instruction(project_type: str, request: InstructionUpdate):
        return response(service.save_instruction(project_type, request.model_dump()))

    @api.delete(
        "/project-types/{project_type}/instruction",
        response_model=Success[InstructionView] | Failure,
    )
    def reset_instruction(project_type: str):
        return response(service.reset_instruction(project_type))

    return api


def install_error_handlers(target: FastAPI) -> None:
    @target.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        result = validation_failure(error.errors())
        return JSONResponse(result.model_dump(mode="json"), status_code=422)


def configure(settings: Settings) -> None:
    service = ProjectService(ProjectStore(settings.database))
    app.include_router(router(service))
    install_error_handlers(app)
    assets = Path(__file__).parent / "assets"
    app.add_static_files("/assets", assets)

    @app.get("/health")
    def health():
        return {"application": "data-story", "instance": settings.instance, "stage": "statistics"}

    @app.post("/shutdown")
    async def shutdown(request: Request):
        if request.headers.get("X-Data-Story-Instance") != settings.instance:
            return JSONResponse({"message": "Це інший локальний екземпляр."}, status_code=409)
        app.shutdown()
        return {"status": "stopping"}

    @ui.page("/")
    def projects_page(request: Request):
        query = request.query_params
        projects_screen(service, query.get("project"), query.get("dataset"), query.get("view"))

    @ui.page("/settings")
    def settings_page(request: Request):
        settings_screen(service, request.query_params.get("type"))

    @ui.page("/icons")
    def icons_page():
        icons_screen(service)


def run(settings: Settings) -> None:
    configure(settings)
    mark = Path(__file__).parent / "assets" / "logo" / "logo-icon.svg"
    ui.add_head_html(
        '<link rel="apple-touch-icon" href="/assets/logo/apple-touch-icon.png">', shared=True
    )
    ui.run(
        host="127.0.0.1",
        port=settings.port,
        title="Data Story · Проєкти",
        reload=False,
        show=False,
        language="uk",
        favicon=mark if mark.is_file() else "📘",
    )
