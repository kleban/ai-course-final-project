"""Model block: explicit choice of saved splits, LinearRegression training and its result."""

from functools import partial

from nicegui import run, ui

from .assistant_panel import ai_shortcut
from .contracts import Failure, ProjectView
from .model import explain
from .screen import button, error_line, kpi, number, page_header, progress_line
from .service import ProjectService

FORMULAS = [
    (
        r"\hat y = a_0 + a_1 x_1 + \dots + a_p x_p",
        "Прогноз — вільний член a₀ плюс сума ознак, помножених на коефіцієнти a₁…aₚ. "
        "Коефіцієнти знаходить LinearRegression методом найменших квадратів на навчальній частині.",
    ),
    (
        r"R^2 = 1 - \frac{\sum_i (y_i - \hat y_i)^2}{\sum_i (y_i - \bar y)^2}",
        "Частка мінливості цілі в тестовій частині, яку пояснює модель; ȳ — середнє тестової цілі.",
    ),
    (
        r"\mathrm{MAE} = \frac{1}{n}\sum_i \lvert y_i - \hat y_i \rvert",
        "Середня абсолютна помилка в одиницях цілі.",
    ),
    (
        r"\mathrm{RMSE} = \sqrt{\frac{1}{n}\sum_i (y_i - \hat y_i)^2}",
        "Корінь середнього квадрата помилки: великі помилки важать більше.",
    ),
]


def precise(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) < 1e-10:
        return "≈ 0"
    return number(value) if abs(value) >= 1000 else f"{value:.6g}".replace(".", ",")


def run_title(item: dict) -> str:
    doc = item["document"]
    when = item["created_at"][:16].replace("T", " ")
    return (
        f"{doc['dataset_name']} · ціль {doc['choices']['target']} · "
        f"{doc['report']['feature_count']} ознак · {when} UTC"
    )


def p_text(value: float | None) -> str:
    """Use the same threshold-preserving format as reports and conclusion facts."""
    if value is None:
        return "—"
    from .model import format_p_value

    return format_p_value(value)


def panel(title: str, extra: str = ""):
    box = ui.element("section").classes(f"model-panel {extra}".strip())
    with box:
        ui.label(title).classes("panel-title")
    return box


def coefficient_row(name: str, value: float, stats: dict) -> None:
    with ui.element("div").classes("trow"):
        ui.label(name).classes("name")
        ui.label(precise(value)).classes("num")
        ui.label(precise(stats.get("std_error"))).classes("num se")
        ui.label(precise(stats.get("t"))).classes("num tval")
        ui.label(p_text(stats.get("p_value"))).classes("num")
        ui.label(stats.get("stars", "")).classes("stars").props(
            f'title="{stats.get("reason") or "Позначка значущості"}"'
        )


def model_result(item: dict, project_id: str | None = None) -> None:
    doc = item["document"]
    test, train = doc["metrics"]["test"], doc["metrics"]["train"]
    target = doc["choices"]["target"]
    tests = doc.get("inference") or {}
    if project_id:
        button(
            "Перевірити модель: графіки",
            partial(ui.navigate.to, f"/?project={project_id}&view=validation&run={item['id']}"),
            "check",
            "small",
        )
        with ui.row().classes("gap-1"):
            ai_shortcut(
                "Поясни результат",
                "explain",
                "Поясни результат цієї моделі: показники, значущі коефіцієнти й обмеження.",
            )
            ai_shortcut("Що робити далі?", "advise", "Що зробити далі з цією моделлю?")
    with ui.element("div").classes("grid grid-4 model-kpis"):
        kpi(
            "regression",
            "R² · тест",
            precise(test["r2"]),
            "не визначений" if test["r2"] is None else "частка поясненої мінливості",
            accent=True,
        )
        kpi("compare", "MAE · тест", precise(test["mae"]), f"в одиницях «{target}»")
        kpi("compare", "RMSE · тест", precise(test["rmse"]), f"в одиницях «{target}»")
        kpi(
            "methods",
            "R² · навчальна",
            precise(train["r2"]),
            f"для порівняння · навчальних {doc['train_count']}, тестових {doc['test_count']}",
        )
    with ui.element("div").classes("model-grid model-grid-main"):
        with panel("Коефіцієнти"):
            ui.label(
                "Зміна прогнозу при зростанні ознаки на одиницю за незмінних інших ознак."
            ).classes("section-lead")
            with ui.element("div").classes("trows coefs"):
                with ui.element("div").classes("trow-head"):
                    ui.label("Ознака")
                    ui.label("Коефіцієнт").classes("num")
                    ui.label("Ст. помилка").classes("num se")
                    ui.label("t").classes("num tval")
                    ui.label("p-value").classes("num")
                    ui.label("")
                coefficient_row(
                    "Вільний член (a₀)", doc["intercept"], doc.get("intercept_inference") or {}
                )
                for coefficient in doc["coefficients"]:
                    coefficient_row(coefficient["name"], coefficient["value"], coefficient)
            if tests:
                ui.label(tests["significance_note"]).classes("model-note")
                if tests.get("reason"):
                    ui.label(tests["reason"]).classes("model-note")
                elif any(c.get("reason") for c in doc["coefficients"]):
                    ui.label(
                        "«—»: коефіцієнт окремо не визначений через лінійну залежність ознак."
                    ).classes("model-note")
                baselines = [
                    f"{name} = {t['baseline']}"
                    for name, t in doc.get("transforms", {}).items()
                    if t.get("baseline") is not None
                ]
                if baselines:
                    ui.label(
                        "Базові категорії (коефіцієнти інших — зсув відносно них): "
                        + ", ".join(baselines)
                    ).classes("model-note")
                ui.label(
                    f"Залишкових ступенів свободи: {tests['df_residual']} · "
                    f"стандартна помилка залишків: {precise(tests['sigma'])}"
                ).classes("model-note")
        with panel("Що означають показники"):
            for line in explain(doc):
                ui.label(line).classes("model-explain")
            for warning in doc["warnings"] + doc["preparation_warnings"]:
                with ui.element("div").classes("model-warning"):
                    ui.label(warning)
    with ui.element("div").classes("model-grid model-grid-three"):
        with panel("Обмеження"):
            with ui.element("ul").classes("model-limits"):
                for limitation in doc["limitations"] + (tests.get("notes") or []):
                    with ui.element("li"):
                        ui.label(limitation)
        with panel("Як розраховано"):
            for tex, explanation in FORMULAS:
                formula = ui.element("div").classes("math-formula")
                formula._props["data-formula"] = tex
                ui.label(explanation).classes("model-note")
        # Author feedback 11 (history 097): no hashes, ids or internal versions on screen —
        # they stay in the saved model for reports and checks.
        with panel("Налаштування моделі"):
            choices = doc["choices"]
            for text in (
                f"Набір: {doc['dataset_name']}",
                f"Ціль: {choices['target']} · ознаки: {', '.join(choices['features'])}",
                f"Поділ {100 - choices['test_percent']}/{choices['test_percent']} · "
                f"кодування категорій: {'one-hot' if choices['encoding'] == 'onehot' else choices['encoding']}",
                f"Пропуски: числа — {choices['numeric_missing']}, "
                f"категорії — {choices['category_missing']}",
                f"Модель: лінійна регресія (scikit-learn {doc['sklearn_version']})",
            ):
                ui.label(text).classes("model-note")


def model_screen(service: ProjectService, active: ProjectView, run_id: str | None) -> None:
    project_id = str(active.id)
    page_header(
        "Модель",
        "regression",
        "Лінійна регресія",
        "Оберіть збережені вибірки й навчіть модель кнопкою. "
        "Навчання — лише на навчальній частині, оцінювання — на тестовій.",
    )
    saved = saved_models(service, project_id)
    runs = service.training_runs(project_id)
    if isinstance(runs, Failure):
        error_line(runs)
        return
    if not runs.data:
        ui.label("Збережених вибірок ще немає. Підготуйте їх у блоці «Підготовка даних».").classes(
            "section-lead"
        )
        button(
            "Вибірки для регресії",
            partial(ui.navigate.to, f"/?project={project_id}&view=training"),
            "next",
        )
        saved()
        return
    options = {item["id"]: run_title(item) for item in runs.data}
    by_id = {item["id"]: item for item in runs.data}
    if run_id and run_id not in options:
        ui.label("Ці вибірки не належать проєкту або не знайдені.").classes("error-message")
        run_id = None
    with ui.element("div").classes("model-grid model-top"):
        left = panel("Збережені вибірки")
        right = panel("Навчання")
    with left:
        selector = (
            ui.select(options, value=run_id, label="Збережені вибірки")
            .props("outlined square")
            .classes("model-select")
        )
    busy = False

    def models_by_run() -> dict[str, dict]:
        listing = service.model_runs(project_id)
        if isinstance(listing, Failure):
            return {}
        return {m["training_run_id"]: m for m in listing.data}

    @ui.refreshable
    def summary() -> None:
        if not selector.value:
            ui.label("Оберіть вибірки, щоб побачити їхній опис і навчити модель.").classes(
                "section-lead"
            )
            return
        doc = by_id[selector.value]["document"]
        report, choices = doc["report"], doc["choices"]
        ui.label(
            f"Навчальних рядків: {report['train_count']} · Тестових: {report['test_count']} · "
            f"Ознак після кодування: {report['feature_count']}"
        ).classes("stat-context")
        ui.label(
            f"Ціль: {choices['target']} · Ознаки: {', '.join(choices['features'])} · "
            f"Поділ {100 - choices['test_percent']}/{choices['test_percent']}, "
            f"число відтворення {choices['seed']}"
        ).classes("section-lead")
        existing = models_by_run().get(selector.value)
        if existing:
            ui.label("Для цих вибірок є збережена модель; результат показано нижче.").classes(
                "section-lead"
            )

    def selection_changed(_event) -> None:
        feedback.clear()
        summary.refresh()
        existing = models_by_run().get(selector.value) if selector.value else None
        if existing:
            with feedback:
                model_result(existing, project_id)

    selector.on_value_change(selection_changed)
    with left:
        summary()

    async def train() -> None:
        nonlocal busy
        if busy:
            return
        feedback.clear()
        if not selector.value:
            with feedback:
                ui.label("Оберіть збережені вибірки.").classes("error-message")
            return
        busy = True
        train_button.props("disabled")
        with feedback:
            progress_line("Навчаємо модель…")
        try:
            response = await run.io_bound(
                service.model_train, project_id, {"training_run_id": selector.value}
            )
            feedback.clear()
            with feedback:
                if isinstance(response, Failure):
                    error_line(response)
                else:
                    ui.label(
                        "Показано збережений результат для цих вибірок."
                        if response.data["reused"]
                        else "Модель навчено й збережено."
                    ).classes("stat-context")
                    model_result(response.data, project_id)
            summary.refresh()
            saved.refresh()
        finally:
            busy = False
            train_button.props(remove="disabled")

    with right:
        ui.label(
            "LinearRegression (scikit-learn): коефіцієнти знаходяться лише на навчальній "
            "частині, показники R², MAE, RMSE — на тестовій. p-value — на навчальній, як у R."
        ).classes("section-lead")
        train_button = button("Навчити лінійну регресію", train, "regression", "primary")
    feedback = ui.column().classes("w-full")
    if selector.value:
        selection_changed(None)
    saved()


def saved_models(service: ProjectService, project_id: str):
    """Persisted models of the project; the caller places it with ``saved()``."""

    @ui.refreshable
    def listing() -> None:
        ui.label("Збережені моделі проєкту").classes("section-title")
        response = service.model_runs(project_id)
        if isinstance(response, Failure):
            error_line(response)
            return
        if not response.data:
            ui.label("Моделей ще немає.").classes("section-lead")
        for item in response.data:
            doc = item["document"]
            r2 = doc["metrics"]["test"]["r2"]
            with ui.expansion(
                f"{doc['dataset_name']} · {doc['choices']['target']} · R² {precise(r2)} · "
                f"{item['created_at'][:16].replace('T', ' ')} UTC"
            ).classes("w-full"):
                model_result(item, project_id)

    return listing
