"""AI assistant panel: a quiet button in the corner, a side panel only when the user opens it.

Closed by default and never opens by itself; Escape or the close button hides it. The panel
knows the current page (block, selected dataset, chart, split or model), keeps a short
conversation and shows the assistant's clarifying questions with one-click answers.
"""

from typing import Any
from uuid import UUID

from nicegui import run, ui

from .assistant import BLOCKS, MAX_HISTORY, MODES, SUGGESTIONS
from .contracts import Failure
from .screen import button, error_line, icon
from .service import ProjectService

HINTS = {
    "advise": "Порада без змін у даних.",
    "execute": "Помічник може запустити дозволені дії сервісу (навчити модель, побудувати "
    "графік перевірки). Перед змінами він уточнить.",
    "explain": "Пояснення збережених результатів простими словами.",
}


def _clean_page(page: dict) -> dict:
    clean: dict = {}
    for key in ("dataset_id", "run_id"):
        try:
            if page.get(key):
                clean[key] = str(UUID(str(page[key])))
        except ValueError:
            pass
    if page.get("tool"):
        clean["tool"] = str(page["tool"])[:40]
    return clean


def assistant_panel(
    service: ProjectService, project_id: str, block: str, page: dict | None = None
) -> None:
    page = _clean_page(page or {})
    history: list[dict] = []
    ref: dict[str, Any] = {}
    drawer = (
        ui.right_drawer(value=False, fixed=True, elevated=False)
        .props("overlay bordered width=420 behavior=desktop")
        .classes("assistant-drawer")
    )
    with drawer:
        with ui.element("div").classes("assistant-head"):
            icon("spark")
            ui.label(f"AI-помічник · {BLOCKS[block]}").classes("panel-title")
            with (
                ui.element("button")
                .classes("assistant-close")
                .props('type="button" aria-label="Закрити помічника"')
                .on("click", drawer.hide)
            ):
                ui.label("×")
        where = [BLOCKS[block]]
        if page.get("dataset_id"):
            found = service.dataset(page["dataset_id"])
            if not isinstance(found, Failure):
                where.append(f"набір «{found.data.name}»")
        if page.get("tool"):
            where.append(f"інструмент «{page['tool']}»")
        ui.label("Бачу сторінку: " + " · ".join(where)).classes("model-note assistant-where")
        mode = ui.toggle(MODES, value="explain" if block in ("model", "validation") else "advise")
        mode.props("square no-caps unelevated dense").classes("assistant-modes")
        hint = ui.label(HINTS[mode.value]).classes("model-note")
        mode.on_value_change(lambda e: hint.set_text(HINTS[e.value]))
        thread = ui.column().classes("w-full assistant-thread")
        with ui.element("div").classes("assistant-chips") as chips:
            for text in SUGGESTIONS[block]:
                with (
                    ui.element("button")
                    .classes("assistant-chip")
                    .props('type="button"')
                    .on("click", lambda _, t=text: ref["question"].set_value(t))
                ):
                    ui.label(text)
        ref["question"] = (
            ui.textarea(placeholder="Напишіть завдання або оберіть підказку")
            .props("outlined square autogrow maxlength=2000")
            .classes("w-full assistant-input")
        )
        status = ui.column().classes("w-full")

        def bubble(role: str, text: str) -> None:
            with thread:
                with ui.element("div").classes(f"assistant-msg {role}"):
                    if role == "assistant":
                        ui.markdown(text).classes("md")
                    else:
                        ui.label(text)

        async def send(text: str | None = None) -> None:
            if ref.get("busy"):
                return
            question = (text if text is not None else ref["question"].value or "").strip()
            status.clear()
            if not question:
                with status:
                    ui.label("Напишіть завдання або оберіть підказку.").classes("error-message")
                return
            ref["busy"] = True
            ref["send"].props("disabled")
            bubble("user", question)
            ref["question"].set_value("")
            chips.set_visibility(False)
            with status:
                ui.label("Помічник працює… це може тривати до хвилини.").classes("model-note")
            try:
                response = await run.io_bound(
                    service.assistant_ask,
                    project_id,
                    {
                        "block": block,
                        "mode": mode.value,
                        "question": question,
                        "page": page,
                        "history": history[-MAX_HISTORY:],
                    },
                )
            finally:
                ref["busy"] = False
                ref["send"].props(remove="disabled")
            status.clear()
            if isinstance(response, Failure):
                with status:
                    error_line(response)
                return
            data = response.data
            history.extend(
                [{"role": "user", "text": question}, {"role": "assistant", "text": data["text"]}]
            )
            bubble("assistant", data["text"])
            with thread:
                if data.get("question") and data["question"]["options"]:
                    with ui.element("div").classes("assistant-chips"):
                        for option in data["question"]["options"]:
                            with (
                                ui.element("button")
                                .classes("assistant-chip answer")
                                .props('type="button"')
                                .on("click", lambda _, o=option: send(o))
                            ):
                                ui.label(option)
                details = []
                if data["tools"]:
                    details.append(
                        "виконано: "
                        + ", ".join(
                            f"{t['name']} ({'успіх' if t['ok'] else 'помилка'})"
                            for t in data["tools"]
                        )
                    )
                if data["sources"]:
                    details.append("джерела: " + "; ".join(s["section"] for s in data["sources"]))
                tokens = data["usage_total"]
                details.append(
                    f"{data['model']} · рівень {data['level']} · спроб {len(data['attempts'])} · "
                    f"токени: {tokens if tokens is not None else 'невідомо'}"
                )
                ui.label(" · ".join(details)).classes("model-note")

        def restart() -> None:
            history.clear()
            thread.clear()
            status.clear()
            chips.set_visibility(True)

        async def send_typed() -> None:
            await send()

        async def open_with(mode_value: str, text: str) -> None:
            """Open the panel from a shortcut in the page and run the prepared request."""
            drawer.show()
            mode.set_value(mode_value)
            await send(text)

        ui.context.client.assistant_open = open_with

        with ui.row().classes("gap-2"):
            ref["send"] = button("Надіслати", send_typed, "spark", "primary")
            button("Нова розмова", restart, "undo")
        ui.label("AI викликається лише за вашою дією; усі запити — у журналі проєкту.").classes(
            "footnote"
        )
    with (
        ui.element("button")
        .classes("assistant-fab")
        .props('type="button" aria-label="Відкрити AI-помічника" title="AI-помічник"')
        .on("click", drawer.toggle)
    ):
        icon("spark")
        ui.label("AI")
    ui.keyboard(
        on_key=lambda e: drawer.hide() if e.key == "Escape" and e.action.keydown else None,
        ignore=[],
    )


def ai_shortcut(label: str, mode: str, question: str) -> None:
    """A small «AI» link next to a result; does nothing visible without the panel."""
    opener = getattr(ui.context.client, "assistant_open", None)
    if opener is None:
        return
    with (
        ui.element("button")
        .classes("btn ghost small ai-shortcut")
        .props(f'type="button" title="AI-помічник: {question}"')
        .on("click", lambda: opener(mode, question))
    ):
        icon("spark")
        ui.label(label)
