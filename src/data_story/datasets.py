"""Uploaded datasets: validation, safe storage of the original file, column profile and preview.

No UI or AI here. pandas reads the file once at upload time to reject broken files early and to
compute a profile; the original bytes are kept unchanged so later stages can derive new versions.
"""

import csv
import hashlib
import io
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any
from uuid import uuid4

import pandas as pd
from pandas.api import types as ptypes

from .projects import ProjectStore
from .storage import connect, ensure_schema

MAX_BYTES = 20 * 1024 * 1024
FORMATS = {".csv": "csv", ".xlsx": "xlsx"}
PREVIEW_ROWS = 20
NAME_LIMIT = 200
ENCODINGS = ("utf-8-sig", "cp1251")
DELIMITERS = ",;\t|"
KIND_TITLES = {"number": "число", "text": "текст", "date": "дата", "bool": "так/ні"}


class DatasetError(ValueError):
    """The uploaded file cannot become a dataset; the message is safe to show to the user."""


class DatasetNotFound(LookupError):
    """A requested dataset does not exist."""


@dataclass(frozen=True)
class Dataset:
    id: str
    project_id: str
    name: str
    file_format: str
    stored_path: str
    size_bytes: int
    sha256: str
    row_count: int
    column_count: int
    profile: dict
    created_at: str


@dataclass(frozen=True)
class Preview:
    columns: list[str]
    rows: list[list[str | None]]
    total_rows: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_name(filename: object) -> str:
    """Display name only — never used as a path."""
    if not isinstance(filename, str):
        raise DatasetError("Файл: не вдалося визначити назву файла.")
    name = PurePath(filename.replace("\\", "/")).name.strip()
    if not name:
        raise DatasetError("Файл: не вдалося визначити назву файла.")
    return name[:NAME_LIMIT]


def file_format(name: str) -> str:
    suffix = PurePath(name).suffix.lower()
    if suffix not in FORMATS:
        raise DatasetError("Формат: підтримуються лише файли CSV і XLSX.")
    return FORMATS[suffix]


# ------------------------------------------------------------------ reading


def _decode(content: bytes) -> tuple[str, str]:
    for encoding in ENCODINGS:
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise DatasetError("CSV: не вдалося прочитати текст (очікується UTF-8 або Windows-1251).")


def _delimiter(text: str) -> str:
    sample = text[:65536]
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample else ""
        counts = {d: first.count(d) for d in DELIMITERS}
        best = max(counts, key=lambda d: counts[d])
        return best if counts[best] else ","


def read_table(
    content: bytes, fmt: str, *, meta: dict | None = None, nrows: int | None = None
) -> tuple[pd.DataFrame, dict]:
    """Parse bytes into a DataFrame. `meta` (encoding, delimiter) repeats an earlier detection."""
    meta = dict(meta or {})
    try:
        if fmt == "csv":
            if "encoding" in meta:
                text = content.decode(meta["encoding"])
            else:
                text, meta["encoding"] = _decode(content)
            if not text.strip():
                raise DatasetError("Файл порожній.")
            meta.setdefault("delimiter", _delimiter(text))
            frame = pd.read_csv(io.StringIO(text), sep=meta["delimiter"], nrows=nrows)
        else:
            if not content.startswith(b"PK"):
                raise DatasetError("XLSX: файл пошкоджений або не є книгою Excel.")
            book = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
            meta.setdefault("sheet", str(book.sheet_names[0]))
            meta["sheets"] = len(book.sheet_names)
            frame = book.parse(meta["sheet"], nrows=nrows)
    except DatasetError:
        raise
    except pd.errors.EmptyDataError as error:
        raise DatasetError("Файл порожній: немає заголовків і даних.") from error
    except pd.errors.ParserError as error:
        raise DatasetError(f"CSV: неправильна структура рядків ({error}).") from error
    except Exception as error:  # broken zip, xml, unexpected bytes
        raise DatasetError("Файл пошкоджений або має непідтримувану структуру.") from error
    frame.columns = [str(c) for c in frame.columns]
    if frame.shape[1] == 0:
        raise DatasetError("Файл не містить стовпців.")
    return frame, meta


# ------------------------------------------------------------------ profile


def _kind(series: pd.Series) -> str:
    if ptypes.is_bool_dtype(series):
        return "bool"
    if ptypes.is_numeric_dtype(series):
        return "number"
    if ptypes.is_datetime64_any_dtype(series):
        return "date"
    return "text"


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 6)


def profile(frame: pd.DataFrame) -> list[dict]:
    columns = []
    for name in frame.columns:
        series = frame[name]
        kind = _kind(series)
        item: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
            "min": None,
            "max": None,
            "mean": None,
        }
        if kind == "number" and series.notna().any():
            item.update(
                min=_number(series.min()), max=_number(series.max()), mean=_number(series.mean())
            )
        columns.append(item)
    return columns


def _cell(value: Any) -> str | None:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ------------------------------------------------------------------ store


class DatasetStore:
    def __init__(self, database: Path, files_root: Path | None = None):
        self.database = ensure_schema(database)
        self.files_root = Path(files_root or self.database.parent / "projects").resolve()

    def add(self, project_id: str, filename: object, content: bytes) -> Dataset:
        name = clean_name(filename)
        fmt = file_format(name)
        if not content:
            raise DatasetError("Файл порожній.")
        if len(content) > MAX_BYTES:
            raise DatasetError(f"Розмір: максимум {MAX_BYTES // (1024 * 1024)} МБ.")
        with connect(self.database) as connection:  # fail fast for an unknown project
            ProjectStore._get(connection, project_id)
        frame, meta = read_table(content, fmt)

        dataset_id = str(uuid4())
        relative = Path(project_id) / "datasets" / dataset_id / f"original.{fmt}"
        target = self.files_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".part")
        partial.write_bytes(content)
        os.replace(partial, target)

        dataset = Dataset(
            id=dataset_id,
            project_id=project_id,
            name=name,
            file_format=fmt,
            stored_path=relative.as_posix(),
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            row_count=int(frame.shape[0]),
            column_count=int(frame.shape[1]),
            profile={**meta, "columns": profile(frame)},
            created_at=_now(),
        )
        try:
            with connect(self.database) as connection:
                ProjectStore._get(connection, project_id)
                connection.execute(
                    "INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        dataset.id,
                        dataset.project_id,
                        dataset.name,
                        dataset.file_format,
                        dataset.stored_path,
                        dataset.size_bytes,
                        dataset.sha256,
                        dataset.row_count,
                        dataset.column_count,
                        json.dumps(dataset.profile, ensure_ascii=False),
                        dataset.created_at,
                    ),
                )
                ProjectStore._event(
                    connection,
                    project_id,
                    "dataset.uploaded",
                    {
                        "dataset_id": dataset.id,
                        "name": name,
                        "rows": str(dataset.row_count),
                        "columns": str(dataset.column_count),
                    },
                )
        except BaseException:
            shutil.rmtree(target.parent, ignore_errors=True)
            raise
        return dataset

    @staticmethod
    def _row(row) -> Dataset:
        data = dict(row)
        data["profile"] = json.loads(data["profile"])
        return Dataset(**data)

    def list_datasets(self, project_id: str) -> list[Dataset]:
        with connect(self.database) as connection:
            ProjectStore._get(connection, project_id)
            rows = connection.execute(
                "SELECT * FROM datasets WHERE project_id = ? ORDER BY created_at, id", (project_id,)
            ).fetchall()
        return [self._row(row) for row in rows]

    def get(self, dataset_id: str) -> Dataset:
        with connect(self.database) as connection:
            row = connection.execute(
                "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
        if row is None:
            raise DatasetNotFound("Набір даних не знайдено. Оновіть список і виберіть інший.")
        return self._row(row)

    def preview(self, dataset_id: str, rows: int = PREVIEW_ROWS) -> Preview:
        dataset = self.get(dataset_id)
        path = (self.files_root / dataset.stored_path).resolve()
        if not path.is_relative_to(self.files_root) or not path.is_file():
            raise DatasetNotFound("Файл набору даних відсутній у сховищі.")
        frame, _ = read_table(
            path.read_bytes(), dataset.file_format, meta=dataset.profile, nrows=rows
        )
        values = [[_cell(v) for v in record] for record in frame.itertuples(index=False)]
        return Preview(list(frame.columns), values, dataset.row_count)
