"""Local, preserved motivation and architecture document inside the application."""

from nicegui import ui

from .screen import Shell, page_header
from .service import ProjectService


def about_screen(service: ProjectService) -> None:
    ui.page_title("Про проєкт · Data Story")
    Shell(service, "about", trail=[("Про проєкт", None)])
    with ui.column().classes("page w-full"):
        page_header("Data Story", "doc", "Про проєкт", "Мотивація та архітектура сервісу.")
        ui.element("iframe").props(
            'src="/assets/about/index.html" title="Мотивація та архітектура Data Story"'
        ).classes("w-full").style("height: calc(100vh - 180px); min-height: 480px; border: 0;")
