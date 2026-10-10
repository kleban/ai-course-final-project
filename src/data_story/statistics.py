"""Stage 03 calculation core. No AI, UI, rounding or changes to source data."""

import hashlib
import math
from time import perf_counter
from typing import Any, Literal

import pandas as pd
from pandas.api import types as ptypes

from .datasets import DatasetError, DatasetStore, _date_text, read_table
from .metadata import Metadata, MetadataStore, issues
from .projects import ProjectStore
from .storage import connect

View = Literal["descriptive", "missing", "correlations"]
METHODS = {
    "descriptive": "sample std (n-1); linear quantiles (n-1)*p",
    "missing": "parser NA + explicit codes; union of rows",
    "correlations": "Pearson; pairwise finite observations; n>=3",
}


class StatisticsError(ValueError):
    """Safe Ukrainian calculation error."""


def _finite(value: Any) -> float | None:
    return float(value) if pd.notna(value) and math.isfinite(float(value)) else None


def calculate(
    frame: pd.DataFrame,
    profile: dict,
    metadata: Metadata,
    view: View,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate one view from a snapshot; invalid field rules do not hide other fields.

    A malformed numeric missing code invalidates that field's additional count and the
    dataset-wide missing union. Known base counts stay visible, never presented as totals.
    """
    if view not in METHODS:
        raise StatisticsError("Невідомий вид розрахунку.")
    if list(frame.columns) != [c.name for c in metadata.document.columns]:
        raise StatisticsError("Стовпці файла не збігаються зі збереженими метаданими.")
    described = {c["name"]: c for c in profile["columns"]}
    rows = len(frame)
    state = "confirmed" if metadata.confirmed_at else "draft" if metadata.saved else "none"
    result: dict[str, Any] = {
        "view": view,
        "method": METHODS[view],
        "row_count": rows,
        "metadata_state": state,
        "metadata_updated_at": metadata.updated_at,
        "warnings": [] if metadata.confirmed_at else ["Метадані не підтверджено"],
        "issues": [vars(issue) for issue in issues(metadata.document)],
        "columns": [],
    }
    numeric: dict[str, pd.Series] = {}
    excluded: dict[str, str] = {}
    union = pd.Series(False, index=frame.index)
    union_valid = True
    for column in metadata.document.columns:
        name = column.name
        series = frame[name]
        actual = described.get(name, {})
        is_number = ptypes.is_numeric_dtype(series) and not ptypes.is_bool_dtype(series)
        base = series.isna()
        extra = pd.Series(False, index=frame.index)
        error = None
        if is_number:
            try:
                codes = [float(code.strip()) for code in column.missing_codes]
                if not all(math.isfinite(code) for code in codes):
                    raise ValueError
                extra = series.isin(codes) & ~base
            except ValueError:
                error = "Код пропуску має бути скінченним числом."
                union_valid = False
        else:
            extra = (
                series.astype("string")
                .str.strip()
                .isin([code.strip() for code in column.missing_codes])
                & ~base
            )
        missing = base | extra
        union |= missing
        invalid = series.isin([math.inf, -math.inf]) & ~missing if is_number else extra & False
        values = series[~missing & ~invalid]
        item: dict[str, Any] = {
            "name": name,
            "label": column.label,
            "unit": column.unit,
            "kind": column.kind,
            "role": column.role,
            "base_missing": int(base.sum()),
            "additional_missing": int(extra.sum()) if error is None else None,
            "missing": int(missing.sum()) if error is None else None,
            "missing_percent": 100 * int(missing.sum()) / rows if rows and error is None else None,
            "invalid_infinite": int(invalid.sum()),
            "error": error,
            "statistics": None,
            "reason": None,
        }
        reason = error
        if reason is None and (column.role in ("id", "ignore") or column.kind == "id"):
            reason = "Поле виключено за типом або роллю."
        if reason is None and column.kind == "number" and not is_number:
            reason = "Описано як число, але фактичні значення не є числовими."
        if reason is None and column.kind == "date":
            fmt = actual.get("date_format")
            if actual.get("kind") != "date" or not fmt:
                reason = "У профілі немає розпізнаного формату дати."
            else:
                dates = pd.to_datetime(
                    values.astype("string").str.strip(), format=fmt, errors="coerce"
                )
                if dates.isna().any():
                    reason = "Значення не відповідають розпізнаному формату дати."
                else:
                    item["date_format"] = fmt
                    item["date_ambiguous"] = bool(actual.get("date_ambiguous"))
                    if item["date_ambiguous"]:
                        item["warning"] = "Неоднозначні дати: використано формат " + fmt
                    item["statistics"] = {
                        "count": len(dates),
                        "unique": int(dates.nunique()),
                        "first": _date_text(dates.min(), fmt) if len(dates) else None,
                        "last": _date_text(dates.max(), fmt) if len(dates) else None,
                    }
        if reason is None and column.kind == "number":
            numeric[name] = series.where(~missing & ~invalid)
            item["statistics"] = {
                "count": len(values),
                "mean": _finite(values.mean()),
                "std": _finite(values.std(ddof=1)) if len(values) >= 2 else None,
                "min": _finite(values.min()),
                "q1": _finite(values.quantile(0.25)),
                "median": _finite(values.quantile(0.5)),
                "q3": _finite(values.quantile(0.75)),
                "max": _finite(values.max()),
                "std_reason": "Потрібно щонайменше 2 значення." if len(values) < 2 else None,
                "empty_reason": "Немає придатних значень." if not len(values) else None,
            }
            item["statistics"]["reasons"] = {
                key: (
                    "Немає придатних значень."
                    if not len(values)
                    else "Потрібно щонайменше 2 значення."
                    if key == "std" and len(values) < 2
                    else "Результат виходить за межі числової точності."
                )
                for key in ("mean", "std", "min", "q1", "median", "q3", "max")
                if item["statistics"][key] is None
            }
        elif reason is None and column.kind in ("category", "text", "bool"):
            counts = values.astype(str).value_counts()
            top = (
                sorted(str(v) for v in counts[counts == counts.max()].index) if len(counts) else []
            )
            item["statistics"] = {
                "count": len(values),
                "unique": len(counts),
                "top": top[0] if top else None,
                "frequency": int(counts.max()) if len(counts) else None,
                "tied": len(top) > 1,
                "empty_reason": "Немає придатних значень." if not len(values) else None,
            }
        item["reason"] = reason
        if name not in numeric:
            excluded[name] = reason or "До Pearson входять лише числові поля."
        if view == "missing":
            item.pop("statistics")
        result["columns"].append(item)
    if view == "missing":
        result["rows_with_missing"] = int(union.sum()) if union_valid else None
        result["rows_with_missing_percent"] = (
            100 * int(union.sum()) / rows if rows and union_valid else None
        )
        result["reason"] = (
            None if union_valid else "Виправте помилкові коди пропуску для підсумку набору."
        )
    if view == "correlations":
        selected = list(numeric) if fields is None else fields
        if len(set(selected)) != len(selected) or any(name not in numeric for name in selected):
            raise StatisticsError("Оберіть різні поля серед придатних числових.")
        result.update(fields=selected, excluded=excluded, r=[], n=[], reasons=[])
        result["reason"] = (
            "Оберіть щонайменше два придатні числові поля." if len(selected) < 2 else None
        )
        if len(selected) >= 2:
            for left in selected:
                r_row, n_row, reasons = [], [], []
                for right in selected:
                    pairs = pd.concat([numeric[left], numeric[right]], axis=1).dropna()
                    count = len(pairs)
                    reason = "Потрібно щонайменше 3 спільні значення." if count < 3 else None
                    if reason is None and any(pairs.iloc[:, i].nunique() < 2 for i in (0, 1)):
                        reason = "Одне з полів має нульову варіацію."
                    value = None if reason else _finite(pairs.iloc[:, 0].corr(pairs.iloc[:, 1]))
                    if value is None and reason is None:
                        reason = "Числова точність не дозволяє обчислити кореляцію."
                    r_row.append(value)
                    n_row.append(count)
                    reasons.append(reason)
                result["r"].append(r_row)
                result["n"].append(n_row)
                result["reasons"].append(reasons)
    return result


class StatisticsStore:
    """Load a fresh file/metadata snapshot and record exactly one event per request."""

    def __init__(self, datasets: DatasetStore):
        self.datasets = datasets
        self.metadata = MetadataStore(datasets.database, datasets)

    def calculate(
        self,
        project_id: str,
        dataset_id: str,
        view: View,
        fields: list[str] | None = None,
        *,
        operation: str = "statistics.calculated",
        audit_extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = perf_counter()
        ProjectStore(self.datasets.database).get(project_id)
        audit: dict[str, Any] = {
            "dataset_id": dataset_id,
            "view": view,
            "fields": fields,
            "method": METHODS.get(view),
            "sha256": None,
            "metadata_state": None,
            "metadata_updated_at": None,
            "row_count": None,
        }
        if audit_extra:
            audit.update(audit_extra)
        try:
            dataset = self.datasets.get(dataset_id)
            if dataset.project_id != project_id:
                raise StatisticsError("Набір не належить поточному проєкту.")
            audit["dataset_name"] = dataset.name
            path = (self.datasets.files_root / dataset.stored_path).resolve()
            if not path.is_relative_to(self.datasets.files_root) or not path.is_file():
                raise StatisticsError("Файл набору даних відсутній у сховищі.")
            content = path.read_bytes()
            audit["sha256"] = hashlib.sha256(content).hexdigest()
            if audit["sha256"] != dataset.sha256:
                raise StatisticsError(
                    "Файл набору змінився або пошкоджений. Завантажте його заново."
                )
            frame, _ = read_table(content, dataset.file_format, meta=dataset.profile)
            metadata = self.metadata.get(dataset_id)
            audit.update(
                row_count=len(frame),
                metadata_state="confirmed"
                if metadata.confirmed_at
                else "draft"
                if metadata.saved
                else "none",
                metadata_updated_at=metadata.updated_at,
            )
            result = calculate(frame, dataset.profile, metadata, view, fields)
            result.update(project_id=project_id, dataset_id=dataset_id, sha256=audit["sha256"])
            audit.update(
                {key: result[key] for key in ("metadata_state", "metadata_updated_at", "row_count")}
            )
            audit["fields"] = result.get("fields", [c["name"] for c in result["columns"]])
            if operation == "chart.built":
                audit["pair_counts"] = result.get("n", [])
            audit["status"] = "success"
            return result
        except (StatisticsError, DatasetError, LookupError, OSError, ValueError) as error:
            message = (
                str(error)
                if isinstance(error, (StatisticsError, DatasetError, LookupError))
                else "Не вдалося прочитати файл або метадані набору."
            )
            audit.update(status="error", error=message)
            raise StatisticsError(message) from error
        finally:
            audit["duration_ms"] = (perf_counter() - started) * 1000
            with connect(self.datasets.database) as connection:
                ProjectStore._event(connection, project_id, operation, audit)
