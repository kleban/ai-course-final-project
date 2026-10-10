"""Dashboard screens of Data Story: top bar, compact left navigation, working area on the right.

Only presentation lives here; every read and write goes through ProjectService.
Design follows the author's dashboard «Keeping the Lights On» (see assets/style.css).
"""

import hashlib
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import partial
from pathlib import Path

from nicegui import app, ui

from .contracts import (
    DatasetView,
    EventView,
    Failure,
    InstructionView,
    ProjectTypeView,
    ProjectView,
    Success,
)
from .data_grid import data_grid
from .datasets import KIND_TITLES, MAX_BYTES, date_format_title
from .icons import GROUPS, ICONS
from .markdown_editor import MarkdownEditor
from .metadata import KIND_TITLES as META_KINDS
from .metadata import ROLE_TITLES, SOURCE_FORMATS
from .project_types import DEFAULT_TYPE, PROJECT_TYPES
from .service import ProjectService

ASSETS = Path(__file__).parent / "assets"

# Тимчасово: маршрут MVP з planning/plan.md — лише показ плану, не кнопки.
STAGES = [
    ("01", "Проєкти", "folder"),
    ("02", "Дані", "data"),
    ("03", "Статистика", "compare"),
    ("04", "Графіки й формули", "formula"),
    ("05", "Підготовка даних", "methods"),
    ("06", "Регресія", "regression"),
    ("07", "База знань (RAG)", "sources"),
    ("08", "Налаштування AI", "settings"),
    ("09", "AI-агент", "spark"),
    ("10", "Звіти", "doc"),
    ("11", "Підсумок-історія", "story"),
]
DONE_STAGES = {"01"}
NAV = [
    ("Робота", [("projects", "/", "Проєкти", "overview")]),
    (
        "Налаштування",
        [
            ("settings", "/settings", "Типи проєктів", "settings"),
            ("icons", "/icons", "Іконки", "gallery"),
        ],
    ),
]
EVENT_TITLES = {
    "project.created": ("Проєкт створено", "check"),
    "project.opened": ("Проєкт відкрито", "when"),
    "dataset.uploaded": ("Завантажено набір даних", "data"),
    "metadata.saved": ("Збережено метадані", "doc"),
    "metadata.confirmed": ("Підтверджено метадані", "check"),
    "metadata.source_added": ("Додано опис даних", "doc"),
}
FORMAT_TITLES = {"csv": "CSV"}


def asset_version(name: str) -> str:
    """Short content hash: the browser reloads a stylesheet only when it really changed."""
    return hashlib.sha256((ASSETS / name).read_bytes()).hexdigest()[:10]


def icon(name: str, extra: str = "") -> ui.element:
    return ui.element("span").classes(f"ico ico-{name} {extra}".strip()).props('aria-hidden="true"')


def button(
    text: str,
    on_click: Callable[[], None | Awaitable[None]],
    ico: str | None = None,
    kind: str = "",
) -> ui.element:
    with (
        ui.element("button")
        .classes(f"btn {kind}".strip())
        .props('type="button"')
        .on("click", on_click) as b
    ):
        if ico:
            icon(ico)
        ui.label(text)
    return b


def error_text(result: Failure) -> str:
    detail = " ".join(issue.message for issue in result.error.fields)
    return detail or result.error.message


def error_line(result: Failure) -> None:
    with ui.element("div").classes("error-message"):
        icon("warning")
        ui.label(error_text(result))


def date(value) -> str:
    return value.strftime("%d.%m.%Y")


def iso_date(value: str | None) -> str:
    """Profile dates are ISO text; show them as 28.01.2016 (with time when it is known)."""
    if not value:
        return "—"
    moment = datetime.fromisoformat(value)
    return moment.strftime("%d.%m.%Y %H:%M" if "T" in value else "%d.%m.%Y")


def type_of(project: ProjectView):
    return PROJECT_TYPES[project.project_type]


class Shell:
    """Top bar, navigation and the create-project dialog shared by every page."""

    def __init__(
        self,
        service: ProjectService,
        current: str,
        active: ProjectView | None = None,
        trail: list[tuple[str, str | None]] | None = None,
    ):
        self.service = service
        for sheet in ("icons.css", "style.css"):
            version = asset_version(sheet)
            ui.add_head_html(f'<link rel="stylesheet" href="/assets/{sheet}?v={version}">')
        ui.colors(primary="#174690", negative="#c0392b")
        self._dialog()
        self._header(trail or [])
        self._navigation(current)

    def open_project(self, project_id: str) -> None:
        result = self.service.get(project_id, opened=True)
        if isinstance(result, Failure):
            ui.notify(error_text(result), type="negative")
        else:
            ui.navigate.to(f"/?project={result.data.id}")

    # --- діалог створення проєкту з вибором типу
    def _dialog(self) -> None:
        listing = self.service.project_types()
        types = listing.data if isinstance(listing, Success) else []
        self.chosen: str = DEFAULT_TYPE
        with ui.dialog() as self.dialog, ui.card().classes("create-dialog"):
            with ui.element("div").classes("dialog-title"):
                icon("folder")
                ui.label("Новий проєкт")
            self.name = (
                ui.input("Назва проєкту").props("outlined square maxlength=120").classes("w-full")
            )
            ui.label("Тип проєкту").classes("field-label")
            with ui.element("div").classes("type-trigger").props('tabindex="0"'):
                self.trigger = ui.element("div").classes("type-current")
                icon("chevron", "chevron")
                with ui.menu().props("fit square").classes("type-menu"):
                    for item in types:
                        self._type_option(item)
            self.purpose = (
                ui.textarea("Мета дослідження (необов’язково)")
                .props("outlined square maxlength=2000")
                .classes("w-full")
            )
            self.error_label = ui.label("").classes("error-message")
            with ui.element("div").classes("dialog-actions"):
                button("Скасувати", self.dialog.close, kind="ghost")
                button("Зберегти проєкт", self._save, ico="check", kind="primary")
        self._show_choice()

    def _type_option(self, item: ProjectTypeView) -> None:
        option = ui.menu_item(on_click=partial(self._choose, item.key)).classes("type-option")
        if not item.enabled:
            option.props("disable").classes("disabled")
        with option:
            icon(item.icon, "type-ico")
            with ui.element("div").classes("type-text"):
                with ui.element("div").classes("type-title"):
                    ui.label(item.title)
                    if not item.enabled:
                        ui.label("згодом").classes("tag")
                ui.label(item.description).classes("type-desc")

    def _choose(self, key: str) -> None:
        self.chosen = key
        self._show_choice()

    def _show_choice(self) -> None:
        chosen = PROJECT_TYPES[self.chosen]
        self.trigger.clear()
        with self.trigger:
            icon(chosen.icon, "type-ico")
            with ui.element("div").classes("type-text"):
                ui.label(chosen.title).classes("type-title")
                ui.label(chosen.description).classes("type-desc")

    def create_dialog(self) -> None:
        self.name.set_value("")
        self.purpose.set_value("")
        self.error_label.set_text("")
        self.chosen = DEFAULT_TYPE
        self._show_choice()
        self.dialog.open()

    def _save(self) -> None:
        result = self.service.create(
            {
                "name": self.name.value,
                "purpose": self.purpose.value or "",
                "project_type": self.chosen,
            }
        )
        if isinstance(result, Failure):
            self.error_label.set_text(error_text(result))
            return
        self.dialog.close()
        self.open_project(str(result.data.id))

    # --- верхня панель
    # --- тонка верхня смуга праворуч від панелі: де ми зараз
    def _header(self, trail: list[tuple[str, str | None]]) -> None:
        with ui.header().classes("topbar"):
            with ui.element("div").classes("crumbs"):
                self.menu = ui.element("span").classes("icon-btn menu-btn").props('title="Меню"')
                with self.menu:
                    icon("menu")
                for n, (title, target) in enumerate(trail):
                    if n:
                        icon("next", "crumb-sep")
                    item = ui.label(title).classes("crumb" + ("" if target else " here"))
                    if target:
                        item.on("click", partial(ui.navigate.to, target))
            with ui.element("div").classes("header-right"):
                with (
                    ui.element("span")
                    .classes("badge")
                    .props('title="Сервер слухає лише 127.0.0.1; входу немає"')
                ):
                    icon("shield")
                    ui.label("Локально")

    # --- компактна ліва навігація: пункти-блоки на всю ширину
    def _navigation(self, current: str) -> None:
        mini = bool(app.storage.general.get(NAV_MINI_KEY, False))
        with (
            ui.left_drawer(value=None, top_corner=True, bottom_corner=True)
            .props("width=240 mini-width=64" + (" mini" if mini else ""))
            .classes("nav") as drawer
        ):
            brand()
            for group, items in NAV:
                ui.label(group).classes("nav-group")
                for key, target, title, ico in items:
                    with (
                        ui.element("div")
                        .classes("nav-link current" if key == current else "nav-link")
                        .props(f'role="link" tabindex="0" title="{title}"')
                        .on("click", lambda target=target: ui.navigate.to(target))
                    ):
                        icon(ico)
                        ui.label(title).classes("label")
            ui.label("Етапи MVP · тимчасово").classes("nav-group stages-title")
            with ui.element("div").classes("stages"):
                for number, title, ico in STAGES:
                    done = number in DONE_STAGES
                    with ui.element("div").classes("nav-item done" if done else "nav-item"):
                        ui.label(number).classes("num")
                        icon("check" if done else ico)
                        ui.label(title)

            def collapse() -> None:
                state = not bool(app.storage.general.get(NAV_MINI_KEY, False))
                app.storage.general[NAV_MINI_KEY] = state
                if state:
                    drawer.props("mini")
                else:
                    drawer.props(remove="mini")

            with (
                ui.element("div")
                .classes("nav-link nav-toggle")
                .props('role="button" tabindex="0" title="Згорнути або розгорнути меню"')
                .on("click", collapse)
            ):
                icon("prev", "collapse-ico")
                ui.label("Згорнути меню").classes("label")
        self.menu.on("click", drawer.toggle)


TAGLINE = "AI-powered analytics & storytelling"
LOGO = ASSETS / "logo" / "logo-panel.svg"
MARK = ASSETS / "logo" / "logo-mark.svg"
NAV_MINI_KEY = "nav_mini"


def brand() -> None:
    """Logo at the top of the side panel: full logo when expanded, the mark when collapsed."""
    with ui.element("div").classes("brand-block").on("click", lambda: ui.navigate.to("/")):
        if LOGO.is_file() and MARK.is_file():
            for name, cls in (("logo-panel.svg", "brand-logo"), ("logo-mark.svg", "brand-mini")):
                version = asset_version(f"logo/{name}")
                ui.element("img").props(
                    f'src="/assets/logo/{name}?v={version}" alt="Data Story"'
                ).classes(cls)
            return
        with ui.element("div").classes("brand-row"):
            icon("story", "brand-ico")
            with ui.element("div").classes("brand-words brand-logo"):
                ui.label("DATA").classes("brand-data")
                ui.label("STORY").classes("brand-story")
        ui.label(TAGLINE).classes("brand-tagline brand-logo")


def page_header(kicker: str, ico: str, title: str, lead: str | None) -> None:
    with ui.element("div").classes("page-header"):
        with ui.element("div").classes("kicker"):
            icon(ico)
            ui.label(kicker)
        ui.label(title).classes("page-title")
        if lead:
            ui.label(lead).classes("lead")


def kpi(
    ico: str,
    label: str,
    value: str,
    sub: str | None = None,
    accent: bool = False,
    mono: bool = False,
) -> None:
    with ui.element("div").classes("kpi"):
        with ui.element("div").classes("kpi-label"):
            icon(ico)
            ui.label(label)
        classes = "kpi-value" + (" accent" if accent else "") + (" mono" if mono else "")
        ui.label(value).classes(classes)
        if sub:
            ui.label(sub).classes("kpi-sub")


# ---------------------------------------------------------------- сторінка «Проєкти»


def projects_screen(
    service: ProjectService,
    selected: str | None,
    dataset_id: str | None = None,
    view: str | None = None,
) -> None:
    active_result = service.get(selected) if selected else None
    active = active_result.data if isinstance(active_result, Success) else None
    ui.page_title(f"{active.name} · Data Story" if active else "Data Story · Проєкти")
    trail: list[tuple[str, str | None]] = [("Проєкти", "/" if active else None)]
    if active:
        trail.append((active.name, f"/?project={active.id}" if dataset_id else None))
    if active and dataset_id:
        found = service.dataset(dataset_id)
        name = found.data.name if isinstance(found, Success) else "Набір даних"
        link = f"/?project={active.id}&dataset={dataset_id}"
        trail.append((name, link if view == "metadata" else None))
        if view == "metadata":
            trail.append(("Метадані", None))
    shell = Shell(service, "projects", active, trail)
    with ui.column().classes("page"):
        if isinstance(active_result, Failure):
            error_line(active_result)
        if active and dataset_id and view == "metadata":
            metadata_editor(service, active, dataset_id)
        elif active and dataset_id:
            dataset_view(service, active, dataset_id)
        elif active:
            project_view(service, active)
        else:
            overview(service, shell)


def overview(service: ProjectService, shell: Shell) -> None:
    listing = service.list_projects()
    projects: list[ProjectView] = listing.data if isinstance(listing, Success) else []
    page_header(
        "Проєкти",
        "overview",
        "Ваші дослідження",
        "Кожне дослідження — окремий проєкт: власні дані, аналіз і пояснення. "
        "Створіть новий проєкт або відкрийте збережений.",
    )
    if isinstance(listing, Failure):
        error_line(listing)
    latest = max(projects, key=lambda p: p.created_at) if projects else None
    with ui.element("div").classes("grid grid-3"):
        kpi("folder", "Проєктів", str(len(projects)), "збережено на цьому комп’ютері", accent=True)
        kpi(
            "when",
            "Останній створений",
            latest.name if latest else "—",
            date(latest.created_at) if latest else "ще немає",
        )
        kpi("data", "Сховище", "SQLite", "runtime/data-story.sqlite3")

    with ui.element("div").classes("section-bar"):
        ui.label("Усі проєкти").classes("section-title")
        button("Створити проєкт", shell.create_dialog, ico="plus", kind="primary")

    if not projects:
        with ui.element("div").classes("empty"):
            ui.label("Тут з’являться ваші проєкти").classes("t")
            ui.label("Для початку потрібні назва, тип аналізу й, за бажанням, мета дослідження.")
    else:
        with ui.element("div").classes("trows projects"):
            with ui.element("div").classes("trow-head"):
                for title in ("Назва", "Тип", "Мета", "Створено", ""):
                    ui.label(title)
            for project in reversed(projects):
                kind = type_of(project)
                with ui.element("div").classes("trow"):
                    with ui.element("div").classes("name"):
                        icon("folder")
                        ui.label(project.name)
                    with ui.element("div").classes("kind"):
                        icon(kind.icon)
                        ui.label(kind.title)
                    ui.label(project.purpose or "Мету ще не зазначено").classes("purpose")
                    ui.label(date(project.created_at)).classes("date")
                    button(
                        "Відкрити", partial(shell.open_project, str(project.id)), "next", "small"
                    )

    with ui.element("details").classes("howto"):
        with ui.element("summary"):
            icon("info")
            ui.label("Як працювати з Data Story")
        with ui.element("ol"):
            for step in (
                "Створіть проєкт: назва, тип аналізу (зараз доступна регресія) і мета.",
                "Відкрийте проєкт у таблиці; поточний проєкт видно у верхній панелі.",
                "Тип проєкту визначає інструкцію для AI-агента — її можна змінити "
                "в розділі «Типи проєктів».",
            ):
                with ui.element("li"):
                    ui.label(step)


def project_view(service: ProjectService, active: ProjectView) -> None:
    kind = type_of(active)
    page_header(
        "Поточний проєкт",
        kind.icon,
        active.name,
        active.purpose or "Мету дослідження ще не зазначено.",
    )
    events_result = service.events(str(active.id))
    events: list[EventView] = events_result.data if isinstance(events_result, Success) else []
    opened = sum(1 for e in events if e.operation == "project.opened")
    datasets_result = service.list_datasets(str(active.id))
    datasets: list[DatasetView] = (
        datasets_result.data if isinstance(datasets_result, Success) else []
    )
    with ui.element("div").classes("grid grid-4"):
        kpi(kind.icon, "Тип аналізу", kind.title, kind.description, accent=True)
        kpi("data", "Наборів даних", str(len(datasets)), f"CSV до {MAX_BYTES // (1024 * 1024)} МБ")
        kpi("when", "Створено", date(active.created_at), active.created_at.strftime("%H:%M UTC"))
        kpi("journal", "Подій у журналі", str(len(events)), f"відкрито {opened} раз(и)")

    datasets_section(service, active, datasets_result)

    ui.label("Інструкція аналізу").classes("section-title")
    instruction = service.instruction(active.project_type)
    if isinstance(instruction, Failure):
        error_line(instruction)
    else:
        state = "типова" if instruction.data.is_default else "змінена"
        ui.label(
            f"Підготовлений промпт для AI-агента для типу «{kind.title}» ({state}). "
            "Його можна змінити в розділі «Типи проєктів»."
        ).classes("section-lead")
        with ui.element("details").classes("howto instruction"):
            with ui.element("summary"):
                icon("doc")
                ui.label("Показати інструкцію")
            ui.markdown(instruction.data.text).classes("md")
        button(
            "Змінити інструкцію",
            lambda: ui.navigate.to(f"/settings?type={active.project_type}"),
            "edit",
            "small",
        )

    ui.label("Журнал дій").classes("section-title")
    if isinstance(events_result, Failure):
        error_line(events_result)
        return
    with ui.element("div").classes("trows log"):
        for event in reversed(events):
            title, ico = EVENT_TITLES.get(event.operation, (event.operation, "info"))
            if event.operation.startswith(("dataset.", "metadata.")):
                title = f"{title}: {event.payload.get('name', '')}"
            with ui.element("div").classes("trow"):
                icon(ico)
                ui.label(title)
                ui.label(event.occurred_at.strftime("%d.%m.%Y %H:%M UTC")).classes("date")
    with ui.element("div").classes("footnote"):
        icon("shield")
        ui.label(
            f"Ідентифікатор проєкту {active.id}. Журнал зберігається разом із проєктом; "
            "секрети й мережеві заголовки не записуються."
        )


# ---------------------------------------------------------------- дані проєкту


def number(value: float | None) -> str:
    """Ukrainian number format: thin-space thousands, decimal comma."""
    if value is None:
        return "—"
    if float(value).is_integer() and abs(value) < 1e15:
        text = f"{value:,.0f}"
    elif abs(value) >= 1000:
        text = f"{value:,.1f}"
    else:
        text = f"{value:.4g}"
    return text.replace(",", "\u202f").replace(".", ",")


def file_size(size: int) -> str:
    if size < 1024:
        return f"{size} Б"
    if size < 1024 * 1024:
        return f"{number(round(size / 1024, 1))} КБ"
    return f"{number(round(size / 1024 / 1024, 1))} МБ"


def datasets_section(service: ProjectService, active: ProjectView, listing) -> None:
    project_id = str(active.id)
    with ui.element("div").classes("section-bar"):
        ui.label("Дані").classes("section-title")
    ui.label(
        "Завантажте таблицю CSV (UTF-8 або Windows-1251, роздільник визначається автоматично) "
        f"до {MAX_BYTES // (1024 * 1024)} МБ. Оригінал зберігається без змін."
    ).classes("section-lead")
    message = ui.label("").classes("error-message")

    async def uploaded(event) -> None:
        content = await event.file.read()
        result = service.upload(project_id, event.file.name, content)
        upload.reset()
        if isinstance(result, Failure):
            message.set_text(error_text(result))
            ui.notify(error_text(result), type="negative")
            return
        ui.notify(f"Набір «{result.data.name}» завантажено", type="positive")
        ui.navigate.to(f"/?project={project_id}&dataset={result.data.id}")

    def rejected() -> None:
        message.set_text(f"Файл не прийнято: підтримується CSV до {MAX_BYTES // (1024 * 1024)} МБ.")

    upload = (
        ui.upload(
            label="Завантажити дані — перетягніть файл або натисніть «+»",
            auto_upload=True,
            max_file_size=MAX_BYTES,
            on_upload=uploaded,
            on_rejected=rejected,
        )
        .props('accept=".csv" flat bordered square')
        .classes("uploader")
    )

    if isinstance(listing, Failure):
        error_line(listing)
        return
    datasets: list[DatasetView] = listing.data
    if not datasets:
        with ui.element("div").classes("empty"):
            ui.label("У проєкті ще немає даних").classes("t")
            ui.label("Після завантаження тут з’явиться список наборів і їхній огляд.")
        return
    with ui.element("div").classes("trows datasets"):
        with ui.element("div").classes("trow-head"):
            for title in ("Набір", "Формат", "Рядків × стовпців", "Розмір", "Завантажено", ""):
                ui.label(title)
        for item in reversed(datasets):
            with ui.element("div").classes("trow"):
                with ui.element("div").classes("name"):
                    icon("data")
                    ui.label(item.name)
                ui.label(FORMAT_TITLES[item.file_format]).classes("date")
                ui.label(f"{number(item.row_count)} × {number(item.column_count)}").classes("date")
                ui.label(file_size(item.size_bytes)).classes("date")
                ui.label(date(item.created_at)).classes("date")
                button(
                    "Огляд",
                    partial(ui.navigate.to, f"/?project={project_id}&dataset={item.id}"),
                    "next",
                    "small",
                )


def dataset_view(service: ProjectService, active: ProjectView, dataset_id: str) -> None:
    result = service.dataset(dataset_id)
    if isinstance(result, Success) and result.data.project_id != active.id:
        result = Failure.model_validate(
            {"error": {"code": "not_found", "message": "Набір даних не належить цьому проєкту."}}
        )
    back = f"/?project={active.id}"
    button("До проєкту", partial(ui.navigate.to, back), "prev", "small back")
    if isinstance(result, Failure):
        error_line(result)
        return
    data = result.data
    source = data.source
    delimiter = {"\t": "табуляція", ";": "крапка з комою", ",": "кома", "|": "риска"}
    details = [
        FORMAT_TITLES[data.file_format],
        file_size(data.size_bytes),
        f"кодування {source.get('encoding', '?')}",
        f"роздільник: {delimiter.get(source.get('delimiter', ''), source.get('delimiter', '?'))}",
    ]
    page_header("Набір даних · " + active.name, "data", data.name, " · ".join(details))

    cells = data.row_count * data.column_count
    missing = sum(c.missing for c in data.columns)
    kinds = {k: sum(1 for c in data.columns if c.kind == k) for k in KIND_TITLES}
    with ui.element("div").classes("grid grid-4"):
        kpi("journal", "Рядків", number(data.row_count), "без рядка заголовків", accent=True)
        kpi(
            "overview",
            "Стовпців",
            number(data.column_count),
            ", ".join(f"{KIND_TITLES[k]}: {n}" for k, n in kinds.items() if n),
        )
        share = f"{missing / cells:.1%}".replace(".", ",") if cells else "0%"
        kpi("warning", "Пропущених значень", number(missing), f"{share} усіх клітинок")
        kpi("when", "Завантажено", date(data.created_at), data.created_at.strftime("%H:%M UTC"))

    meta_result = service.metadata(dataset_id)
    metadata_section(service, active, dataset_id, meta_result)

    ui.label("Стовпці").classes("section-title")
    ui.label("Тип і статистику визначено з даних; назву, опис і роль задають метадані.").classes(
        "section-lead"
    )
    described = (
        {c.name: c for c in meta_result.data.document.columns}
        if isinstance(meta_result, Success)
        else {}
    )
    with ui.element("div").classes("trows columns"):
        with ui.element("div").classes("trow-head"):
            for title in ("Стовпець", "Тип", "Роль", "Пропуски", "Мін", "Макс", "Середнє"):
                ui.label(title)
        for column in data.columns:
            meta = described.get(column.name)
            with ui.element("div").classes("trow"):
                with ui.element("div").classes("colname"):
                    ui.label(column.name).classes("name")
                    if meta and (meta.label or meta.description):
                        ui.label(
                            " — ".join(x for x in (meta.label, meta.description) if x)
                        ).classes("hint")
                kind_label = ui.label(
                    META_KINDS[meta.kind] if meta else KIND_TITLES[column.kind]
                ).classes("date")
                if column.date_format:
                    hint = f"Дата у файлі: {date_format_title(column.date_format)}"
                    if column.date_ambiguous:
                        hint += "; значення також підходять під порядок місяць/день"
                    kind_label.tooltip(hint)
                ui.label(ROLE_TITLES[meta.role] if meta else "—").classes(
                    "role target" if meta and meta.role == "target" else "role"
                )
                ui.label(number(column.missing)).classes("num warn" if column.missing else "num")
                if column.kind == "date":
                    ui.label(iso_date(column.first)).classes("num")
                    ui.label(iso_date(column.last)).classes("num")
                else:
                    ui.label(number(column.min)).classes("num")
                    ui.label(number(column.max)).classes("num")
                ui.label(number(column.mean)).classes("num")

    ui.label("Таблиця даних").classes("section-title")
    total = data.row_count
    counter = ui.label("").classes("section-lead")

    def show_count(shown: int) -> None:
        if shown >= total:
            counter.set_text(
                f"Усі {number(total)} рядків, сторінками. Сортування — клік на заголовку, "
                "фільтр — поле під заголовком стовпця. Дати показано як ДД.ММ.РРРР, "
                "порожні клітинки — «—»."
            )
        else:
            counter.set_text(f"За фільтрами знайдено {number(shown)} з {number(total)} рядків.")

    show_count(total)
    data_grid(dataset_id, [(c.name, c.kind) for c in data.columns], show_count)


# ---------------------------------------------------------------- метадані (етап 02b)


def metadata_status(meta) -> str:
    if meta.confirmed_at:
        return f"Підтверджено {meta.confirmed_at.strftime('%d.%m.%Y %H:%M')} UTC"
    if meta.saved and meta.updated_at:
        return f"Чернетка, збережено {meta.updated_at.strftime('%d.%m.%Y %H:%M')} UTC"
    return "Чернетка з даних — ще не збережено"


def issue_list(found) -> None:
    if not found:
        return
    with ui.element("div").classes("issues"):
        for item in found:
            with ui.element("div").classes(f"issue {item.level}"):
                icon("warning" if item.level == "warning" else "info")
                ui.label(f"{item.column}: {item.message}" if item.column else item.message)


def metadata_section(service: ProjectService, active: ProjectView, dataset_id: str, result) -> None:
    base = f"/?project={active.id}&dataset={dataset_id}"
    with ui.element("div").classes("section-bar"):
        ui.label("Метадані").classes("section-title")
        with ui.element("div").classes("dialog-actions"):
            button("Додати опис", lambda: describe.open(), "plus")
            button(
                "Редагувати метадані",
                partial(ui.navigate.to, base + "&view=metadata"),
                "edit",
                "primary",
            )
    if isinstance(result, Failure):
        error_line(result)
        return
    meta = result.data
    ui.label(
        f"{metadata_status(meta)}. Опис полів допомагає статистиці, вибору цільової змінної "
        "й поясненням. Перетворення текстового опису в поля через AI з’явиться на етапі 08."
    ).classes("section-lead")
    if meta.document.dataset.description:
        ui.label(meta.document.dataset.description).classes("lead small")
    issue_list(meta.issues)

    with ui.dialog() as describe, ui.card().classes("create-dialog"):
        with ui.element("div").classes("dialog-title"):
            icon("doc")
            ui.label("Додати опис даних")
        ui.label(
            "Вставте текст або завантажте файл з описом полів (TXT, MD, CSV, JSON, XLSX до 2 МБ). "
            "Опис зберігається без змін і показується поруч із формою метаданих."
        ).classes("type-desc")
        text = ui.textarea("Текст опису").props("outlined square autogrow").classes("w-full")
        problem = ui.label("").classes("error-message")

        def save_text() -> None:
            saved = service.add_metadata_text(dataset_id, {"text": text.value or ""})
            if isinstance(saved, Failure):
                problem.set_text(error_text(saved))
                return
            describe.close()
            ui.navigate.to(base)

        async def uploaded(event) -> None:
            content = await event.file.read()
            saved = service.add_metadata_file(dataset_id, event.file.name, content)
            if isinstance(saved, Failure):
                problem.set_text(error_text(saved))
                return
            describe.close()
            ui.navigate.to(base)

        ui.upload(
            label="Або завантажте файл опису",
            auto_upload=True,
            max_file_size=2 * 1024 * 1024,
            on_upload=uploaded,
            on_rejected=lambda: problem.set_text(
                "Файл не прийнято: TXT, MD, CSV, JSON, XLSX до 2 МБ."
            ),
        ).props(f'accept="{",".join(sorted(SOURCE_FORMATS))}" flat bordered square').classes(
            "uploader"
        )
        with ui.element("div").classes("dialog-actions"):
            button("Скасувати", describe.close, kind="ghost")
            button("Зберегти текст", save_text, "check", "primary")

    sources_panel(service, dataset_id)


def sources_panel(service: ProjectService, dataset_id: str) -> None:
    sources = service.metadata_sources(dataset_id)
    if isinstance(sources, Failure):
        error_line(sources)
        return
    if not sources.data:
        return
    with ui.element("details").classes("howto"):
        with ui.element("summary"):
            icon("doc")
            ui.label(f"Сирі описи даних ({len(sources.data)})")
        for item in sources.data:
            with ui.element("div").classes("source"):
                ui.label(f"{item.name} · {item.created_at.strftime('%d.%m.%Y %H:%M')} UTC").classes(
                    "kicker"
                )
                ui.label(item.text).classes("source-text")


def _categories_text(column) -> str:
    return "\n".join(
        f"{c.value} = {c.meaning}" if c.meaning else c.value for c in column.categories
    )


def _parse_categories(raw: str) -> list[dict]:
    values = []
    for line in (raw or "").splitlines():
        if not line.strip():
            continue
        value, _, meaning = line.partition("=")
        values.append({"value": value.strip(), "meaning": meaning.strip()})
    return values


def metadata_editor(service: ProjectService, active: ProjectView, dataset_id: str) -> None:
    base = f"/?project={active.id}&dataset={dataset_id}"
    button("До огляду набору", partial(ui.navigate.to, base), "prev", "small back")
    dataset = service.dataset(dataset_id)
    result = service.metadata(dataset_id)
    if isinstance(dataset, Failure):
        error_line(dataset)
        return
    if isinstance(result, Failure):
        error_line(result)
        return
    if dataset.data.project_id != active.id:
        ui.label("Набір даних не належить цьому проєкту.").classes("error-message")
        return
    meta = result.data
    document = meta.document.model_dump()
    page_header(
        "Метадані · " + dataset.data.name,
        "doc",
        "Опис набору й полів",
        f"{metadata_status(meta)}. Факти з даних (тип, пропуски, діапазон, значення) "
        "показано сірим і не змінюються вручну.",
    )
    issue_list(meta.issues)
    sources_panel(service, dataset_id)

    ui.label("Набір даних").classes("section-title")
    fields = {
        "title": "Назва для людей",
        "description": "Опис",
        "source": "Джерело (звідки дані, посилання)",
        "unit_of_observation": "Одиниця спостереження (рядок = …)",
        "period": "Період і географія",
        "license": "Ліцензія або обмеження",
    }
    dataset_inputs = {}
    with ui.element("div").classes("meta-grid three"):
        for key, label in fields.items():
            widget = ui.textarea if key == "description" else ui.input
            dataset_inputs[key] = (
                widget(label, value=document["dataset"][key])
                .props("outlined square dense" + (" autogrow" if key == "description" else ""))
                .classes("w-full" + (" full" if key == "description" else ""))
            )

    ui.label("Поля").classes("section-title")
    column_inputs = []
    for column in meta.document.columns:
        seen = column.observed
        facts = [f"у даних: {META_KINDS[seen.kind]}", f"пропусків {number(seen.missing)}"]
        if seen.min is not None:
            facts.append(f"від {number(seen.min)} до {number(seen.max)}")
        if seen.values:
            facts.append("значення: " + ", ".join(seen.values[:8]))
        with ui.element("div").classes("meta-card"):
            with ui.element("div").classes("meta-head"):
                ui.label(column.name).classes("name")
                ui.label(" · ".join(facts)).classes("facts")
            with ui.element("div").classes("meta-grid"):
                inputs = {
                    "label": ui.input("Назва для людей", value=column.label),
                    "kind": ui.select(dict(META_KINDS), label="Тип", value=column.kind),
                    "role": ui.select(dict(ROLE_TITLES), label="Роль", value=column.role),
                    "unit": ui.input("Одиниці", value=column.unit),
                    "description": ui.textarea("Опис", value=column.description),
                    "computation": ui.input("Як пораховано", value=column.computation),
                    "range_min": ui.number("Мінімум (очікуваний)", value=column.range_min),
                    "range_max": ui.number("Максимум (очікуваний)", value=column.range_max),
                    "categories": ui.textarea(
                        "Категорії: значення = пояснення, по рядку",
                        value=_categories_text(column),
                    ),
                    "missing_codes": ui.input(
                        "Коди пропуску через кому", value=", ".join(column.missing_codes)
                    ),
                }
                for key, element in inputs.items():
                    element.props("outlined square dense").classes("w-full")
                    if key in ("description", "categories", "computation"):
                        element.classes("wide")
                    if key in ("description", "categories"):
                        element.props("autogrow")
                kind = inputs["kind"]
                inputs["categories"].bind_visibility_from(
                    kind, "value", backward=lambda v: v == "category"
                )
                for key in ("range_min", "range_max", "unit"):
                    inputs[key].bind_visibility_from(
                        kind, "value", backward=lambda v: v == "number"
                    )
            column_inputs.append(inputs)

    message = ui.label("").classes("error-message")

    def save(confirm: bool) -> None:
        payload = dict(document)
        payload["dataset"] = {k: (w.value or "") for k, w in dataset_inputs.items()}
        columns = []
        for original, inputs in zip(document["columns"], column_inputs, strict=True):
            item = dict(original)
            for key in ("label", "kind", "role", "unit", "description", "computation"):
                item[key] = inputs[key].value or ""
            item["range_min"] = inputs["range_min"].value
            item["range_max"] = inputs["range_max"].value
            item["categories"] = _parse_categories(inputs["categories"].value)
            item["missing_codes"] = [
                c.strip() for c in (inputs["missing_codes"].value or "").split(",") if c.strip()
            ]
            columns.append(item)
        payload["columns"] = columns
        saved = service.save_metadata(dataset_id, {"document": payload, "confirm": confirm})
        if isinstance(saved, Failure):
            message.set_text(error_text(saved))
            return
        ui.notify("Метадані підтверджено" if confirm else "Чернетку збережено", type="positive")
        ui.navigate.to(base)

    with ui.element("div").classes("dialog-actions left sticky-actions"):
        button("Зберегти чернетку", lambda: save(False), "check")
        button("Зберегти й підтвердити", lambda: save(True), "check", "primary")
        button("Скасувати", partial(ui.navigate.to, base), kind="ghost")


# ---------------------------------------------------------------- «Типи проєктів»


def settings_screen(service: ProjectService, selected: str | None) -> None:
    ui.page_title("Типи проєктів · Data Story")
    Shell(service, "settings", trail=[("Налаштування", None), ("Типи проєктів", None)])
    key = selected if selected in PROJECT_TYPES else DEFAULT_TYPE
    kind = PROJECT_TYPES[key]
    with ui.column().classes("page"):
        page_header(
            "Налаштування",
            "settings",
            "Типи проєктів та інструкції",
            "Для кожного типу аналізу є інструкція — підготовлений промпт, за яким AI-агент "
            "проводить аналіз. Інструкції зберігаються на цьому комп’ютері; типову версію "
            "можна відновити. Налаштування моделей AI з’являться тут на етапі 08.",
        )
        with ui.element("div").classes("seg"):
            for item in PROJECT_TYPES.values():
                with (
                    ui.element("div")
                    .classes("seg-item current" if item.key == key else "seg-item")
                    .props('role="tab" tabindex="0"')
                    .on("click", lambda k=item.key: ui.navigate.to(f"/settings?type={k}"))
                ):
                    icon(item.icon)
                    ui.label(item.title)
                    if not item.enabled:
                        ui.label("згодом").classes("tag")

        result = service.instruction(key)
        if isinstance(result, Failure):
            error_line(result)
            return
        instruction: InstructionView = result.data
        with ui.element("div").classes("type-head"):
            icon(kind.icon, "type-ico big")
            with ui.element("div"):
                ui.label(kind.title).classes("section-title flush")
                ui.label(kind.description).classes("section-lead")
            with ui.element("div").classes("type-state"):
                ui.label("Доступний для нових проєктів" if kind.enabled else "Поки неактивний")
                ui.label(
                    "Типова інструкція"
                    if instruction.is_default or instruction.updated_at is None
                    else f"Змінено {instruction.updated_at.strftime('%d.%m.%Y %H:%M')} UTC"
                ).classes("muted")

        editor = MarkdownEditor(instruction.text)
        message = ui.label("").classes("error-message")

        async def save() -> None:
            try:
                text = await editor.markdown()
            except TimeoutError:
                message.set_text("Редактор не відповів. Спробуйте зберегти ще раз.")
                return
            saved = service.save_instruction(key, {"text": text})
            if isinstance(saved, Failure):
                message.set_text(error_text(saved))
                return
            ui.notify("Інструкцію збережено", type="positive")
            ui.navigate.to(f"/settings?type={key}")

        def reset() -> None:
            restored = service.reset_instruction(key)
            if isinstance(restored, Failure):
                message.set_text(error_text(restored))
                return
            ui.notify("Відновлено типову інструкцію", type="info")
            ui.navigate.to(f"/settings?type={key}")

        with ui.element("div").classes("dialog-actions left"):
            button("Зберегти інструкцію", save, "check", "primary")
            button("Відновити типову", reset, "reset")
        with ui.element("div").classes("footnote"):
            icon("info")
            ui.label(
                "Формат — Markdown. Типові тексти: src/data_story/instructions/*.md; "
                "кожна зміна записується в журнал конфігурації."
            )


# ---------------------------------------------------------------- «Іконки»


def icons_screen(service: ProjectService) -> None:
    ui.page_title("Іконки · Data Story")
    Shell(service, "icons", trail=[("Налаштування", None), ("Іконки", None)])
    with ui.column().classes("page"):
        page_header(
            "Налаштування",
            "gallery",
            "Бібліотека іконок",
            "Єдине джерело іконок для всього Data Story: src/data_story/icons.py. "
            "Лінійні SVG 24×24 у стилі дашборда автора; колір береться з тексту. "
            'У коді: icon("назва").',
        )
        for group, names in GROUPS.items():
            ui.label(group).classes("section-title")
            with ui.element("div").classes("icon-grid"):
                for name in names:
                    with ui.element("div").classes("icon-tile"):
                        icon(name, "big")
                        ui.label(name).classes("mono")
        ui.label(f"Усього іконок: {len(ICONS)}").classes("footnote")
