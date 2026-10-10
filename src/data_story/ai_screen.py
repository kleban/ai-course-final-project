"""Settings → AI models: OpenAI model per pipeline task, limits, key state from .env."""

from nicegui import ui

from .contracts import Failure
from .model_screen import panel
from .screen import Shell, button, error_line, error_text, page_header
from .service import ProjectService

# The key field is deliberately inert: the value stays in the browser, is never sent to the
# server and is cleared on click (D-76: the key comes only from .env).
FAKE_KEY = """
<div class="fake-key">
  <input type="password" autocomplete="off" spellcheck="false" placeholder="sk-…"
         aria-label="Новий ключ OpenAI (не зберігається)">
  <button type="button" class="btn small" onclick="
    this.previousElementSibling.value='';
    this.nextElementSibling.textContent='Ключ не надіслано й не збережено. Щоб змінити ключ, ' +
      'відредагуйте OPENAI_API_KEY у файлі .env і перезапустіть сервіс.';">Замінити ключ</button>
  <div class="model-note" aria-live="polite"></div>
</div>
"""
KEY_STATES = {
    "found": "Ключ знайдено",
    "empty": "Ключ не вписано",
    "missing_file": "Немає файла .env",
    "suspicious": "Перевірте ключ",
}


def ai_settings_screen(service: ProjectService) -> None:
    ui.page_title("Моделі AI · Data Story")
    Shell(service, "ai_settings", trail=[("Налаштування", None), ("Моделі AI", None)])
    with ui.column().classes("page"):
        page_header(
            "Налаштування",
            "spark",
            "Моделі AI",
            "Яка модель OpenAI виконує яку задачу аналізу. Налаштування спільні для сервісу; "
            "AI викликається лише явною дією користувача.",
        )
        response = service.ai_configuration()
        if isinstance(response, Failure):
            error_line(response)
            return
        data = response.data
        config, key = data["configuration"], data["key"]
        models = {m["id"]: m for m in data["models"]}
        selects: dict[str, ui.select] = {}
        with ui.element("div").classes("model-grid model-top"):
            with panel("Ключ OpenAI"):
                ui.label(
                    KEY_STATES[key["state"]] + (f" · {key['masked']}" if key["masked"] else "")
                ).classes("stat-context ai-key-state")
                ui.label(key["message"]).classes("model-note")
                ui.label(
                    "Джерело ключа — лише файл .env у корені проєкту (OPENAI_API_KEY). "
                    "Поле нижче не передає ключ на сервер."
                ).classes("model-note")
                ui.html(FAKE_KEY, sanitize=False)
            with panel("Ліміти"):
                tokens = ui.number(
                    "Максимум вихідних токенів на відповідь",
                    value=config["max_output_tokens"],
                    min=256,
                    max=32000,
                    step=256,
                ).props("outlined square")
                steps = ui.number(
                    "Максимум кроків агента", value=config["max_agent_steps"], min=1, max=20, step=1
                ).props("outlined square")
                ui.label(
                    "Ліміти зупиняють відповідь або агента зі зрозумілим станом; грошовий облік "
                    "не ведемо, лише токени."
                ).classes("model-note")
        with ui.element("div").classes("model-grid model-grid-three ai-stages"):
            for stage in data["stages"]:
                with panel(stage):
                    for task in [t for t in data["tasks"] if t["stage"] == stage]:
                        allowed = {
                            m: "Без OpenAI (локально)" if m == "local" else m
                            for m in models
                            if models[m]["kind"] in (task["kind"], "local")
                        }
                        with ui.element("div").classes("ai-task"):
                            ui.label(f"{task['title']} · {task['mode']}").classes(
                                "knowledge-section"
                            )
                            ui.label(task["purpose"]).classes("model-note")
                            selects[task["key"]] = (
                                ui.select(
                                    allowed,
                                    value=config["models"][task["key"]],
                                    label="Модель",
                                )
                                .props(f'outlined square dense data-task="{task["key"]}"')
                                .classes("model-select")
                            )
        message = ui.label("").classes("model-note")

        def save() -> None:
            raw = {
                "models": {key: select.value for key, select in selects.items()},
                "max_output_tokens": int(tokens.value or 0),
                "max_agent_steps": int(steps.value or 0),
            }
            result = service.save_ai_configuration(raw)
            if isinstance(result, Failure):
                message.set_text(error_text(result))
                message.classes(replace="error-message")
            else:
                message.set_text("Налаштування збережено. Ключ не змінювався.")
                message.classes(replace="stat-context")

        def reset() -> None:
            result = service.reset_ai_configuration()
            if isinstance(result, Failure):
                message.set_text(error_text(result))
                return
            for key, select in selects.items():
                select.set_value(result.data["models"][key])
            tokens.set_value(result.data["max_output_tokens"])
            steps.set_value(result.data["max_agent_steps"])
            message.set_text("Повернуто типові моделі й ліміти.")

        with ui.row().classes("gap-2"):
            button("Зберегти", save, "check", "primary")
            button("Повернути типові", reset, "undo")
        for model in data["models"]:
            ui.label(model["title"]).classes("model-note")
        ui.label(
            "Моделі — кандидати з офіційного каталогу OpenAI (перевірено 2026-10-10); доступ "
            "у вашому обліковому записі ще не перевірявся. Розрахунки, статистика й регресія "
            "AI не використовують."
        ).classes("footnote")
