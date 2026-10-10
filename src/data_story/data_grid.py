"""Read-only interactive table of a dataset: AG Grid Community bundled with NiceGUI (MIT).

All rows are sent once; AG Grid virtualises rendering, so a 5 MB CSV stays responsive.
Numbers sort as numbers, recognised dates as ISO text shown as ДД.ММ.РРРР. Nothing is edited.
"""

from collections.abc import Callable

from nicegui import ui

from .contracts import DatasetTable

MISSING = "—"
TEXT = f"p => p.value == null || p.value === '' ? '{MISSING}' : p.value"
# Decimal comma as in the rest of the interface; no thousands separator (years, postcodes).
NUMBER = f"p => p.value == null ? '{MISSING}' : String(p.value).replace('.', ',')"
DATE = (
    f"p => p.value == null ? '{MISSING}' : p.value.slice(8, 10) + '.' + p.value.slice(5, 7)"
    " + '.' + p.value.slice(0, 4) + (p.value.length > 10 ? ' ' + p.value.slice(11, 16) : '')"
)
# agDateColumnFilter compares a local midnight Date with the cell value (ISO text).
DATE_COMPARATOR = (
    "(filter, value) => { if (value == null) return -1;"
    " const d = new Date(+value.slice(0, 4), +value.slice(5, 7) - 1, +value.slice(8, 10));"
    " return d < filter ? -1 : d > filter ? 1 : 0; }"
)
FILTERS = {"number": "agNumberColumnFilter", "date": "agDateColumnFilter"}

LOCALE = {
    "noRowsToShow": "Немає рядків",
    "loadingOoo": "Завантаження…",
    "filterOoo": "Значення…",
    "dateFormatOoo": "дд.мм.рррр",
    "equals": "Дорівнює",
    "notEqual": "Не дорівнює",
    "contains": "Містить",
    "notContains": "Не містить",
    "startsWith": "Починається з",
    "endsWith": "Закінчується на",
    "blank": "Порожнє",
    "notBlank": "Не порожнє",
    "lessThan": "Менше",
    "greaterThan": "Більше",
    "lessThanOrEqual": "Менше або дорівнює",
    "greaterThanOrEqual": "Більше або дорівнює",
    "inRange": "Між",
    "inRangeStart": "Від",
    "inRangeEnd": "До",
    "before": "До",
    "after": "Після",
    "andCondition": "І",
    "orCondition": "АБО",
    "applyFilter": "Застосувати",
    "resetFilter": "Скинути",
    "clearFilter": "Очистити",
    "cancelFilter": "Скасувати",
    "columnFilter": "Фільтр стовпця",
    "sortAscending": "За зростанням",
    "sortDescending": "За спаданням",
    "sortUnSort": "Без сортування",
    "pinColumn": "Закріпити стовпець",
    "pinLeft": "Ліворуч",
    "pinRight": "Праворуч",
    "noPin": "Не закріплювати",
    "autosizeThisColumn": "Підігнати ширину",
    "autosizeAllColumns": "Підігнати всі стовпці",
    "resetColumns": "Скинути стовпці",
    "ariaFilterInput": "Значення фільтра",
    "ariaSearch": "Пошук",
}


def column_def(index: int, name: str, kind: str) -> dict:
    column: dict = {
        "headerName": name,
        "field": f"c{index}",
        "filter": FILTERS.get(kind, "agTextColumnFilter"),
        ":valueFormatter": {"date": DATE, "number": NUMBER}.get(kind, TEXT),
    }
    if kind == "number":
        column["type"] = "rightAligned"
        column["cellClass"] = "num"
    if kind == "date":
        column["filterParams"] = {":comparator": DATE_COMPARATOR}
    return column


def grid_options(table: DatasetTable) -> dict:
    return {
        "columnDefs": [column_def(i, c.name, c.kind) for i, c in enumerate(table.columns)],
        "rowData": [{f"c{i}": value for i, value in enumerate(row)} for row in table.rows],
        "defaultColDef": {
            "sortable": True,
            "resizable": True,
            "floatingFilter": True,
            "minWidth": 90,
        },
        "autoSizeStrategy": {"type": "fitCellContents"},
        "localeText": LOCALE,
        "enableCellTextSelection": True,
        "ensureDomOrder": True,
        "animateRows": False,
        "suppressMovableColumns": True,
    }


def data_grid(table: DatasetTable, on_count: Callable[[int], None] | None = None) -> ui.aggrid:
    grid = ui.aggrid(grid_options(table), auto_size_columns=False).classes("data-grid")

    async def filtered() -> None:
        if on_count is not None:
            on_count(int(await grid.run_grid_method("getDisplayedRowCount")))

    grid.on("filterChanged", filtered)
    return grid
