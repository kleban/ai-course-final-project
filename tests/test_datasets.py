"""Stage 02: upload, validation, safe storage, profile and preview of datasets."""

import hashlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from data_story.datasets import MAX_BYTES, DatasetError, DatasetNotFound, DatasetStore
from data_story.projects import ProjectNotFound, ProjectStore

ROOT = Path(__file__).resolve().parents[1]
CSV = "площа;кімнат;район;ціна\n45,5;1;Центр;2100\n60;2;Поділ;\n81,2;3;Центр;3900\n".replace(
    ",", "."
).encode("utf-8")


def xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"x": [1, 2, 3], "y": [2.5, None, 7.0]}).to_excel(
            writer, sheet_name="Дані", index=False
        )
        pd.DataFrame({"other": ["a"]}).to_excel(writer, sheet_name="Інше", index=False)
    return buffer.getvalue()


class DatasetTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / "tmp" / "tests"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.directory.cleanup)
        database = Path(self.directory.name) / "story.sqlite3"
        self.projects = ProjectStore(database)
        self.store = DatasetStore(database)
        self.project = self.projects.create("Ціни на житло")

    def stored_files(self) -> list[Path]:
        root = self.store.files_root
        return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []

    def test_csv_with_semicolon_is_profiled_stored_unchanged_and_logged(self):
        dataset = self.store.add(self.project.id, "ціни.csv", CSV)
        self.assertEqual((dataset.row_count, dataset.column_count), (3, 4))
        self.assertEqual(dataset.profile["delimiter"], ";")
        columns = {c["name"]: c for c in dataset.profile["columns"]}
        self.assertEqual(columns["площа"]["kind"], "number")
        self.assertEqual(columns["район"]["kind"], "text")
        self.assertEqual(columns["ціна"]["missing"], 1)
        self.assertEqual((columns["площа"]["min"], columns["площа"]["max"]), (45.5, 81.2))
        [path] = self.stored_files()
        self.assertEqual(path.read_bytes(), CSV)
        self.assertEqual(dataset.sha256, hashlib.sha256(CSV).hexdigest())
        event = self.projects.events(self.project.id)[-1]
        self.assertEqual(event.operation, "dataset.uploaded")
        self.assertEqual(event.payload["rows"], "3")
        preview = self.store.preview(dataset.id)
        self.assertEqual(preview.columns, ["площа", "кімнат", "район", "ціна"])
        self.assertEqual(preview.rows[1], ["60", "2", "Поділ", None])

    def test_windows_1251_csv_with_comma_is_read(self):
        content = "Регіон,Значення\nКиїв,1\nЛьвів,2\n".encode("cp1251")
        dataset = self.store.add(self.project.id, "регіони.csv", content)
        self.assertEqual(dataset.profile["encoding"], "cp1251")
        self.assertEqual(self.store.preview(dataset.id).rows[1], ["Львів", "2"])

    def test_xlsx_uses_first_sheet_and_reports_sheet_count(self):
        dataset = self.store.add(self.project.id, "Книга.XLSX", xlsx_bytes())
        self.assertEqual(dataset.file_format, "xlsx")
        self.assertEqual((dataset.profile["sheet"], dataset.profile["sheets"]), ("Дані", 2))
        self.assertEqual((dataset.row_count, dataset.column_count), (3, 2))
        self.assertEqual(self.store.preview(dataset.id).rows[1], ["2", None])

    def test_bad_files_are_rejected_without_rows_or_files(self):
        cases = [
            ("notes.txt", b"a,b\n1,2\n"),
            ("empty.csv", b""),
            ("blank.csv", b"   \n"),
            ("broken.xlsx", b"PK\x03\x04 not really a workbook"),
            ("text.xlsx", b"a,b\n1,2\n"),
            ("big.csv", b"a\n" + b"1\n" * (MAX_BYTES // 2)),
            ("", b"a\n1\n"),
        ]
        for name, content in cases:
            with self.subTest(name=name), self.assertRaises(DatasetError):
                self.store.add(self.project.id, name, content)
        self.assertEqual(self.store.list_datasets(self.project.id), [])
        self.assertEqual(self.stored_files(), [])

    def test_unknown_project_and_unknown_dataset(self):
        with self.assertRaises(ProjectNotFound):
            self.store.add("00000000-0000-4000-8000-000000000000", "a.csv", CSV)
        with self.assertRaises(DatasetNotFound):
            self.store.get("00000000-0000-4000-8000-000000000000")
        self.assertEqual(self.stored_files(), [])

    def test_projects_are_isolated_and_same_file_twice_gives_two_datasets(self):
        other = self.projects.create("Інший")
        first = self.store.add(self.project.id, "a.csv", CSV)
        second = self.store.add(self.project.id, "a.csv", CSV)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(len(self.store.list_datasets(self.project.id)), 2)
        self.assertEqual(self.store.list_datasets(other.id), [])
        self.assertEqual(len(self.stored_files()), 2)

    def test_path_in_file_name_is_only_a_label(self):
        dataset = self.store.add(self.project.id, "..\\..\\evil.csv", CSV)
        self.assertEqual(dataset.name, "evil.csv")
        [path] = self.stored_files()
        self.assertTrue(path.resolve().is_relative_to(self.store.files_root))

    def test_journal_failure_rolls_back_dataset_and_removes_file(self):
        with patch.object(ProjectStore, "_event", side_effect=sqlite3.OperationalError("test")):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.add(self.project.id, "a.csv", CSV)
        self.assertEqual(self.store.list_datasets(self.project.id), [])
        self.assertEqual(self.stored_files(), [])

    def test_demo_samples_upload_as_regression_ready_tables(self):
        for name in ("demo_apartments.csv", "demo_apartments.xlsx"):
            with self.subTest(name=name):
                content = (ROOT / "samples" / name).read_bytes()
                dataset = self.store.add(self.project.id, name, content)
                self.assertEqual((dataset.row_count, dataset.column_count), (150, 7))
                kinds = {c["name"]: c["kind"] for c in dataset.profile["columns"]}
                self.assertEqual(kinds["ціна_тис_грн"], "number")
                self.assertEqual(kinds["район"], "text")


if __name__ == "__main__":
    unittest.main()
