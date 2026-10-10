"""Model block: explicit choice of saved splits, LinearRegression training and its result."""

from functools import partial

from nicegui import run, ui

from .contracts import Failure, ProjectView
from .model import explain
from .screen import button, error_line, kpi, number, page_header
from .service import ProjectService

FORMULAS = [
    (
        r"\hat y = b_0 + b_1 x_1 + \dots + b_p x_p",
        "Прогноз — вільний член плюс сума ознак, помножених на коефіцієнти. "
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


def formulas() -> None:
    with ui.element("details").classes("howto"):
        with ui.element("summary"):
            ui.label("Як розраховано · формули")
        for tex, explanation in FORMULAS:
            formula = ui.element("div").classes("math-formula")
            formula._props["data-formula"] = tex
            ui.label(explanation)
        ui.label("Якщо формула не завантажилась, пояснення залишається доступним.").classes("muted")


def model_result(item: dict) -> None:
    doc = item["document"]
    test, train = doc["metrics"]["test"], doc["metrics"]["train"]
    target = doc["choices"]["target"]
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
    ui.label("Що означають показники").classes("section-title")
    for line in explain(doc):
        ui.label(line).classes("model-explain")
    for warning in doc["warnings"] + doc["preparation_warnings"]:
        with ui.element("div").classes("model-warning"):
            ui.label(warning)
    formulas()
    ui.label("Коефіцієнти").classes("section-title")
    ui.label(
        "Зміна прогнозу при зростанні ознаки на одиницю за незмінних інших ознак. "
        "Порядок — як у матриці ознак."
    ).classes("section-lead")
    with ui.element("div").classes("trows coefs"):
        with ui.element("div").classes("trow-head"):
            ui.label("Ознака")
            ui.label("Коефіцієнт").classes("num")
        with ui.element("div").classes("trow"):
            ui.label("Вільний член").classes("name")
            ui.label(precise(doc["intercept"])).classes("num")
        for coefficient in doc["coefficients"]:
            with ui.element("div").classes("trow"):
                ui.label(coefficient["name"]).classes("name")
                ui.label(precise(coefficient["value"])).classes("num")
    ui.label("Обмеження").classes("section-title")
    with ui.element("ul").classes("model-limits"):
        for limitation in doc["limitations"]:
            with ui.element("li"):
                ui.label(limitation)
    with ui.element("details").classes("howto"):
        with ui.element("summary"):
            ui.label("Походження результату")
        choices = doc["choices"]
        for text in (
            f"Оцінювач: {doc['estimator']} · scikit-learn {doc['sklearn_version']} · "
            f"параметри: {', '.join(f'{k}={v}' for k, v in doc['params'].items())}",
            f"Набір: {doc['dataset_name']} · SHA-256 джерела: {doc['source_sha256']}",
            f"Вибірки: {doc['training_run_id']} · SHA-256 матриць: {doc['matrix_sha256']}",
            f"Ціль: {choices['target']} · ознаки: {', '.join(choices['features'])}",
            f"Поділ: навчання/тест {100 - choices['test_percent']}/{choices['test_percent']} · "
            f"число відтворення {choices['seed']} · кодування {choices['encoding']} · "
            f"пропуски чисел {choices['numeric_missing']}, категорій {choices['category_missing']}",
            f"Версія метаданих: {doc['metadata_updated_at'] or 'не збережені'} · "
            f"ранг матриці з вільним членом: {doc['rank']} з {doc['feature_count'] + 1}",
            f"Ідентифікатор моделі: {item['id']}",
        ):
            ui.label(text)


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
                model_result(existing)

    selector.on_value_change(selection_changed)
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
            ui.label("Навчаємо модель…").classes("section-lead")
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
                    model_result(response.data)
            summary.refresh()
            saved.refresh()
        finally:
            busy = False
            train_button.props(remove="disabled")

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
                model_result(item)

    return listing
