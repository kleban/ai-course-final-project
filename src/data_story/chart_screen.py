"""One heatmap at a time and an independent configuration page."""

from typing import Any

from nicegui import ui
from pydantic import ValidationError

from .chart_configuration import FONTS, THEMES, ChartConfiguration, ChartOptions, preset
from .charts import contrast_warnings, heatmap_svg
from .contracts import Failure, ProjectView, Success
from .service import ProjectService


def options_editor(options: ChartOptions, changed) -> Any:
    controls: dict[str, Any] = {}

    def notify() -> None:
        changed()

    with ui.element("div").classes("chart-options"):
        controls["font"] = ui.select(FONTS, value=options.font, label="Шрифт", on_change=notify)
        for name, title, low, high in (
            ("title_size", "Розмір заголовка", 16, 32),
            ("label_size", "Розмір підписів", 12, 22),
            ("decimals", "Знаків після коми", 1, 4),
        ):
            controls[name] = ui.number(
                title, value=getattr(options, name), min=low, max=high, step=1, on_change=notify
            ).props("outlined square")
        for name, title in (
            ("positive", "Додатні значення"),
            ("negative", "Від’ємні значення"),
            ("neutral", "Нуль / слабкий зв’язок"),
            ("text", "Текст"),
            ("background", "Фон"),
        ):
            controls[name] = ui.input(
                title + " · HEX", value=getattr(options, name), on_change=notify
            ).props("outlined square")
        for name, title in (
            ("numbers", "Числа в клітинках"),
            ("lower_triangle", "Лише нижній трикутник"),
            ("frame", "Рамка області графіка"),
            ("threshold_enabled", "Акцент за порогом |r|"),
        ):
            controls[name] = ui.checkbox(title, value=getattr(options, name), on_change=notify)
        controls["threshold"] = ui.number(
            "Поріг акценту |r|", value=options.threshold, min=0, max=1, step=0.05, on_change=notify
        ).props("outlined square")

    def read() -> ChartOptions:
        values = {k: c.value for k, c in controls.items()}
        for key in ("title_size", "label_size", "decimals"):
            value = values[key]
            if value is not None and float(value).is_integer():
                values[key] = int(value)
        return ChartOptions.model_validate(values)

    return read


def show_heatmap(svg: str) -> None:
    with ui.element("div").classes("heatmap-wrap"):
        ui.html(svg, sanitize=False).classes("heatmap-scroll")
        ui.label(
            "Оберіть клітинку мишею або клавішею Tab: тут з’являться r, n і виключення."
        ).classes("heatmap-detail").props('aria-live="polite"')


def formulas() -> None:
    with ui.element("details").classes("howto"):
        with ui.element("summary"):
            ui.label("Як розраховано · формули")
        ui.label(
            "Pearson показує лінійний зв’язок, а не причинність. Для кожної пари беремо лише "
            "спільні скінченні значення: n ≥ 3, обидва поля мають варіацію."
        )
        for tex, explanation in (
            (
                r"r=\frac{\sum_{i=1}^{n}(x_i-\bar{x})(y_i-\bar{y})}{\sqrt{\sum_{i=1}^{n}(x_i-\bar{x})^2\sum_{i=1}^{n}(y_i-\bar{y})^2}}",
                "xᵢ, yᵢ — значення спільної пари; середні x̄, ȳ обчислено саме на цих n парах.",
            ),
            (
                r"\bar{x}=\frac{1}{n}\sum_{i=1}^{n}x_i",
                "Середнє: сума придатних значень, поділена на n.",
            ),
            (
                r"s=\sqrt{\frac{1}{n-1}\sum_{i=1}^{n}(x_i-\bar{x})^2}",
                "Вибіркове стандартне відхилення: знаменник n−1; потрібні хоча б два значення.",
            ),
            (
                r"p_{\mathrm{missing}}=100\frac{m}{N}",
                "m — кількість пропусків поля за метаданими; N — усі рядки. Нескінченності не є пропусками.",
            ),
        ):
            formula = ui.element("div").classes("math-formula")
            formula._props["data-formula"] = tex
            ui.label(explanation)
        ui.label(
            "Якщо формула не завантажилась, пояснення методу вище залишається доступним."
        ).classes("muted")


def heatmap_screen(service: ProjectService, active: ProjectView, dataset_id: str | None) -> None:
    from .screen import button, datasets_section, error_line, error_text, page_header

    project_id = str(active.id)
    page_header(
        "Графіки · " + active.name,
        "formula",
        "Теплова карта кореляцій",
        "Один графік, увесь набір даних. Pearson з перевіреного ядра статистики.",
    )
    listing = service.list_datasets(project_id)
    configuration = service.chart_configuration()
    if isinstance(listing, Failure):
        error_line(listing)
        return
    if isinstance(configuration, Failure):
        error_line(configuration)
        return
    if not listing.data:
        ui.label("Для графіка потрібен набір даних. Завантажте CSV у цей проєкт.")
        datasets_section(service, active, listing)
        return
    choices = {str(d.id): d.name for d in listing.data}
    if dataset_id and dataset_id not in choices:
        ui.label("Набір не належить цьому проєкту або не знайдений.").classes("error-message")
        return
    selected = dataset_id or next(iter(choices))
    ui.select(
        choices,
        value=selected,
        label="Набір даних",
        on_change=lambda e: ui.navigate.to(f"/?project={project_id}&dataset={e.value}&view=charts"),
    ).props("outlined square")
    meta = service.metadata(selected)
    if isinstance(meta, Failure):
        error_line(meta)
        return
    eligible = {
        c.name: (c.label or c.name) + (f" · {c.name}" if c.label and c.label != c.name else "")
        for c in meta.data.document.columns
        if c.kind == "number" and c.role not in ("id", "ignore")
    }
    # Explicit selection: never silently take a subset when >12 fields are available.
    fields = (
        ui.select(
            eligible,
            value=list(eligible) if len(eligible) <= 12 else [],
            multiple=True,
            label="Числові поля · оберіть 2–12",
        )
        .props("outlined square use-chips")
        .classes("w-full")
    )
    ui.label(
        "Тема: "
        + THEMES[configuration.data.theme]
        + " · тимчасові зміни діють лише після побудови."
    )
    button("Налаштування графіків", lambda: ui.navigate.to("/settings/charts"), "settings")
    title = (
        ui.input("Заголовок (необов’язково)")
        .props("outlined square maxlength=180")
        .classes("w-full")
    )
    with ui.expansion("Тимчасове оформлення графіка").classes("w-full"):
        read_options = options_editor(configuration.data.effective(), lambda: None)
    message = ui.label("").classes("error-message").props('role="alert"')
    state: dict[str, Any] = {"result": None}

    @ui.refreshable
    def render() -> None:
        result = state["result"]
        if result is None:
            ui.label("Оберіть поля й натисніть «Побудувати».").classes("section-lead")
            return
        metadata_title = {"none": "не збережено", "draft": "чернетка", "confirmed": "підтверджено"}[
            result.metadata_state
        ]
        ui.label(f"Увесь набір · {result.row_count:,} рядків · метадані: {metadata_title}").classes(
            "stat-summary"
        )
        ui.label("Тема при побудові: " + THEMES[result.theme])
        for warning in result.warnings:
            ui.label(warning).classes("metadata-warning")
        if result.options.threshold_enabled:
            ui.label(
                f"Акцент: |r| ≥ {result.options.threshold:g}. Інші значення приглушені, доступні в підказках."
            )
        show_heatmap(result.svg)
        with ui.element("details").classes("howto"):
            with ui.element("summary"):
                ui.label("Повні назви полів, кількість значень і виключення")
            for field in result.fields:
                ui.label(f"{field.label} · {field.name} · одиниці: {field.unit or 'не задані'}")
            for name, reason in result.excluded.items():
                ui.label(name + ": " + reason)
            for i, field in enumerate(result.fields):
                for j in range(i + 1):
                    value = result.r[i][j]
                    ui.label(
                        f"{field.name} ↔ {result.fields[j].name}: r={value if value is not None else '—'}; "
                        f"n={result.n[i][j]}; виключено пар={result.row_count - result.n[i][j]}"
                        + ("; " + result.reasons[i][j] if result.reasons[i][j] else "")
                    )
        formulas()

    def build() -> None:
        try:
            options = read_options()
        except ValidationError:
            message.set_text("Перевірте HEX-кольори, розміри тексту та поріг 0…1.")
            return
        result = service.heatmap(
            project_id,
            {
                "dataset_id": selected,
                "fields": fields.value,
                "options": options.model_dump(),
                "title": title.value or "",
            },
        )
        if isinstance(result, Failure):
            message.set_text(error_text(result))
            return
        state["result"] = result.data
        message.set_text("")
        render.refresh()

    button("Побудувати", build, "formula", "primary")
    render()


def chart_settings_screen(service: ProjectService) -> None:
    from .screen import Shell, button, error_line, error_text, page_header

    ui.page_title("Налаштування графіків · Data Story")
    Shell(service, "chart_settings", trail=[("Налаштування", None), ("Графіки", None)])
    with ui.column().classes("page"):
        page_header(
            "Налаштування",
            "settings",
            "Графіки й теми",
            "Спільні для сервісу. Попередній перегляд не змінює збережені налаштування. "
            "Зараз доступні параметри теплової карти; інші додамо разом із графіками.",
        )
        response = service.chart_configuration()
        if isinstance(response, Failure):
            error_line(response)
            return
        original = response.data
        options_state = {"value": original.effective()}
        read_state: dict[str, Any] = {}
        message = ui.label("").classes("error-message")

        @ui.refreshable
        def preview() -> None:
            try:
                options = read_state["read"]() if "read" in read_state else options_state["value"]
            except ValidationError:
                ui.label("Перевірте HEX-кольори, розміри тексту та поріг 0…1.").classes(
                    "error-message"
                )
                return
            for warning in contrast_warnings(options):
                ui.label(warning).classes("metadata-warning")
            ui.label("Попередній перегляд · демонстраційні значення, не ваші дані").classes(
                "section-lead"
            )
            columns = [{"name": n, "label": n, "unit": ""} for n in ("Поле A", "Поле B", "Поле C")]
            demo = {
                "columns": columns,
                "fields": [c["name"] for c in columns],
                "row_count": 100,
                "r": [[1, 0.5, -0.7], [0.5, 1, None], [-0.7, None, 1]],
                "n": [[100, 90, 80], [90, 100, 2], [80, 2, 100]],
                "reasons": [
                    [None] * 3,
                    [None, None, "Потрібно 3 пари."],
                    [None, "Потрібно 3 пари.", None],
                ],
            }
            show_heatmap(heatmap_svg(demo, options))

        @ui.refreshable
        def editor() -> None:
            read_state["read"] = options_editor(options_state["value"], preview.refresh)

        def choose(e) -> None:
            options_state["value"] = (
                (original.custom or preset("storytelling"))
                if e.value == "custom"
                else preset(e.value)
            )
            read_state.clear()
            editor.refresh()
            preview.refresh()

        theme = ui.select(THEMES, value=original.theme, label="Тема", on_change=choose).props(
            "outlined square"
        )
        ui.label(
            "Змінені параметри збережуться як одна власна тема. Готові теми залишаються незмінними."
        )
        editor()
        preview()

        def save() -> None:
            try:
                options = read_state["read"]()
                active = theme.value
                custom = original.custom
                if active == "custom" or options != preset(active):
                    active, custom = "custom", options
                request = ChartConfiguration(theme=active, custom=custom)
            except ValidationError:
                message.set_text("Перевірте кольори, розміри та поріг перед збереженням.")
                return
            result = service.save_chart_configuration(request.model_dump())
            if isinstance(result, Failure):
                message.set_text(error_text(result))
                return
            ui.notify("Налаштування графіків збережено", type="positive")
            ui.navigate.to("/settings/charts")

        def reset() -> None:
            result = service.reset_chart_configuration()
            if isinstance(result, Failure):
                message.set_text(error_text(result))
                return
            ui.navigate.to("/settings/charts")

        with ui.element("div").classes("dialog-actions left"):
            button("Зберегти налаштування", save, "check", "primary")
            button("Відновити початкові налаштування", reset, "reset")
        events = service.chart_configuration_events()
        if isinstance(events, Success):
            with ui.element("details").classes("howto"):
                with ui.element("summary"):
                    ui.label("Журнал налаштувань · останні 10 дій")
                for event in events.data:
                    ui.label(
                        str(event["occurred_at"])
                        + " · "
                        + ("Збережено" if event["operation"].endswith("saved") else "Відновлено")
                    )
