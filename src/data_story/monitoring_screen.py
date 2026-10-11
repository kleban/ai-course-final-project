"""Settings → Monitoring: state of every part of the service, checked locally on demand."""

from nicegui import run, ui

from .contracts import Failure
from .monitoring import STATE_TITLES
from .screen import Shell, button, error_line, kpi, page_header
from .service import ProjectService

ICONS = {"ok": "check", "warning": "warning", "error": "warning", "not_configured": "info",
         "not_implemented": "when"}  # fmt: skip


def monitoring_screen(service: ProjectService) -> None:
    ui.page_title("Моніторинг · Data Story")
    Shell(service, "monitoring", trail=[("Налаштування", None), ("Моніторинг", None)])
    with ui.column().classes("page"):
        page_header(
            "Налаштування",
            "shield",
            "Моніторинг сервісу",
            "Які частини Data Story працюють. Перевірки локальні й швидкі; OpenAI тут не "
            "викликається.",
        )

        async def check() -> None:
            response = await run.io_bound(service.monitoring)
            output.clear()
            with output:
                if isinstance(response, Failure):
                    error_line(response)
                    return
                data = response.data
                summary = data["summary"]
                with ui.element("div").classes("grid grid-4"):
                    kpi("check", STATE_TITLES["ok"], str(summary["ok"]), accent=True)
                    kpi("warning", "Із зауваженнями", str(summary["warning"]))
                    kpi("warning", STATE_TITLES["error"], str(summary["error"]))
                    kpi("info", "Не налаштовані / заплановані",
                        str(summary["not_configured"] + summary["not_implemented"]))  # fmt: skip
                with ui.element("div").classes("model-grid model-grid-three monitor-grid"):
                    for row in data["rows"]:
                        with ui.element("section").classes(f"model-panel monitor-{row['state']}"):
                            ui.label(row["title"]).classes("panel-title")
                            with ui.element("div").classes("monitor-state"):
                                ui.element("span").classes(f"ico ico-{ICONS[row['state']]}").props(
                                    'aria-hidden="true"'
                                )
                                ui.label(row["state_title"])
                            ui.label(row["detail"]).classes("model-note mono-wrap")
                ui.label(
                    f"Перевірено {data['checked_at'][:19].replace('T', ' ')} UTC · "
                    f"{data['duration_ms']:.0f} мс"
                ).classes("footnote")

        button("Перевірити", check, "check", "primary")
        output = ui.column().classes("w-full")
        ui.timer(0.05, check, once=True)
