"""Settings → knowledge base: rule documents and a local search check for RAG (stage 07)."""

from nicegui import run, ui

from .contracts import Failure
from .model_screen import panel
from .screen import Shell, button, error_line, page_header
from .service import ProjectService


def hit_card(hit: dict) -> None:
    with ui.element("div").classes("knowledge-hit"):
        ui.label(f"{hit['title']} · {hit['section']}").classes("knowledge-section")
        ui.label(hit["text"]).classes("model-explain")
        ui.label(f"Джерело: {hit['source']} · схожість {hit['score']:.2f}").classes(
            "model-note mono-wrap"
        )


def knowledge_screen(service: ProjectService) -> None:
    ui.page_title("База знань · Data Story")
    Shell(service, "knowledge", trail=[("Налаштування", None), ("База знань", None)])
    with ui.column().classes("page"):
        page_header(
            "Налаштування",
            "doc",
            "База знань",
            "Базові правила, на які спиратиметься AI-помічник. Пошук працює локально, "
            "без інтернету; редагування правил з'явиться окремим інструментом.",
        )
        documents = service.knowledge_documents()
        if isinstance(documents, Failure):
            error_line(documents)
            return
        with ui.element("div").classes("model-grid model-grid-main"):
            search_box = panel("Перевірити пошук")
            docs_box = panel("Документи")
        with search_box:
            query = (
                ui.input(
                    "Запитання", placeholder="Наприклад: що означають зірочки біля коефіцієнта"
                )
                .props("outlined square")
                .classes("model-select")
            )

            async def search() -> None:
                results.clear()
                if not (query.value or "").strip():
                    with results:
                        ui.label("Введіть запитання.").classes("error-message")
                    return
                response = await run.io_bound(
                    service.knowledge_search, {"query": query.value, "limit": 3}
                )
                results.clear()
                with results:
                    if isinstance(response, Failure):
                        error_line(response)
                        return
                    data = response.data
                    if not data["hits"]:
                        ui.label(data["reason"]).classes("section-lead")
                    for hit in data["hits"]:
                        hit_card(hit)
                    ui.label(
                        f"Метод: {data['method']} · фрагментів: {data['fragment_count']}"
                    ).classes("model-note")

            query.on("keydown.enter", search)
            button("Знайти", search, "search", "primary")
            results = ui.column().classes("w-full")
        with docs_box:
            total = sum(d["fragments"] for d in documents.data)
            ui.label(f"Документів: {len(documents.data)} · фрагментів (розділів): {total}").classes(
                "model-note"
            )
            for document in documents.data:
                state = "типовий" if document["is_default"] else "змінений"
                with ui.expansion(
                    f"{document['title']} · {document['fragments']} розд. · {state}"
                ).classes("w-full"):
                    ui.label(f"Джерело: {document['source']}").classes("model-note mono-wrap")
                    ui.markdown(document["text"].split("\n", 3)[-1]).classes("md")
