"""Contract and HTTP checks share the same real SQLite service as the UI."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from data_story.contracts import Failure, ProjectCreate, ProjectView, Success
from data_story.projects import ProjectStore
from data_story.service import ProjectService
from data_story.web import install_error_handlers, router

ROOT = Path(__file__).resolve().parents[1]
PROJECT_RESULT = TypeAdapter(Success[ProjectView] | Failure)


class ContractAndApiTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / "tmp" / "tests"
        directory.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temporary.cleanup)
        self.store = ProjectStore(Path(self.temporary.name) / "projects.sqlite3")
        self.service = ProjectService(self.store)
        application = FastAPI()
        application.include_router(router(self.service))
        install_error_handlers(application)
        self.client = TestClient(application)
        self.addCleanup(self.client.close)

    def test_schema_is_strict_and_exposes_limits(self):
        for raw in ({"name": 5}, {"name": " "}, {"name": "Дані", "extra": True}):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                ProjectCreate.model_validate(raw)
        schema = ProjectCreate.model_json_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["name"]["maxLength"], 120)

    def test_http_and_ui_service_return_same_validated_project(self):
        response = self.client.post("/api/projects", json={"name": "  Дані України  "})
        self.assertEqual(response.status_code, 200)
        result = PROJECT_RESULT.validate_python(response.json())
        self.assertIsInstance(result, Success)
        project_id = response.json()["data"]["id"]
        self.assertEqual(
            self.client.get("/api/projects/" + project_id).json(),
            self.service.get(project_id).model_dump(mode="json"),
        )
        self.assertEqual(response.json()["data"]["name"], "Дані України")

    def test_bad_json_unknown_fields_and_empty_name_have_same_error_envelope(self):
        responses = [
            self.client.post("/api/projects", json={"name": ""}),
            self.client.post("/api/projects", json={"name": "Дані", "unknown": 1}),
            self.client.post(
                "/api/projects", content="{", headers={"Content-Type": "application/json"}
            ),
        ]
        for response in responses:
            with self.subTest(body=response.text):
                self.assertEqual(response.status_code, 422)
                failure = Failure.model_validate(response.json())
                self.assertEqual(failure.error.code, "invalid_input")
        self.assertEqual(self.store.list_projects(), [])

    def test_invalid_and_unknown_ids_are_different_failures(self):
        invalid = self.client.get("/api/projects/not-a-uuid")
        missing = self.client.get("/api/projects/" + str(uuid4()))
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "not_found")

    def test_storage_failure_is_not_success_and_does_not_leak_details(self):
        with patch.object(
            self.store, "create", side_effect=sqlite3.OperationalError("private disk path")
        ):
            response = self.client.post("/api/projects", json={"name": "Дані"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "storage_error")
        self.assertNotIn("private disk path", response.text)
        self.assertEqual(self.store.list_projects(), [])

    def test_invalid_output_is_internal_error_not_user_input_error(self):
        with patch.object(self.store, "list_projects", return_value=[{"id": "bad"}]):
            response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "internal_error")

    def test_http_open_and_event_scoping(self):
        first = self.store.create("Перший")
        second = self.store.create("Другий")
        self.client.post(f"/api/projects/{first.id}/open")
        first_events = self.client.get(f"/api/projects/{first.id}/events").json()["data"]
        second_events = self.client.get(f"/api/projects/{second.id}/events").json()["data"]
        self.assertEqual(len(first_events), 2)
        self.assertEqual(len(second_events), 1)
        self.assertTrue(all(event["project_id"] == first.id for event in first_events))

    def test_project_type_is_returned_and_disabled_type_is_rejected(self):
        created = self.client.post("/api/projects", json={"name": "Ціни"}).json()["data"]
        self.assertEqual(created["project_type"], "regression")
        refused = self.client.post(
            "/api/projects", json={"name": "Групи", "project_type": "clustering"}
        )
        self.assertEqual(refused.status_code, 422)
        self.assertIn("ще недоступний", refused.text)
        types = self.client.get("/api/project-types").json()["data"]
        self.assertEqual([(t["key"], t["enabled"]) for t in types][0], ("regression", True))

    def test_instruction_http_round_trip(self):
        url = "/api/project-types/regression/instruction"
        self.assertTrue(self.client.get(url).json()["data"]["is_default"])
        saved = self.client.put(url, json={"text": "Новий промпт"}).json()["data"]
        self.assertEqual((saved["text"], saved["is_default"]), ("Новий промпт", False))
        self.assertEqual(self.client.put(url, json={"text": " "}).status_code, 422)
        self.assertTrue(self.client.delete(url).json()["data"]["is_default"])
        missing = self.client.get("/api/project-types/unknown/instruction")
        self.assertEqual(missing.status_code, 404)

    def test_dataset_upload_list_view_and_preview_over_http(self):
        project = self.store.create("Дані")
        content = "x;y\n1;2\n3;\n".encode()
        uploaded = self.client.post(
            f"/api/projects/{project.id}/datasets", files={"file": ("дані.csv", content)}
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        data = uploaded.json()["data"]
        self.assertEqual((data["row_count"], data["column_count"]), (2, 2))
        self.assertEqual(data["source"]["delimiter"], ";")
        self.assertEqual([c["missing"] for c in data["columns"]], [0, 1])
        listed = self.client.get(f"/api/projects/{project.id}/datasets").json()["data"]
        self.assertEqual([d["id"] for d in listed], [data["id"]])
        preview = self.client.get(f"/api/datasets/{data['id']}/preview").json()["data"]
        self.assertEqual(preview["rows"], [["1", "2"], ["3", None]])
        events = self.client.get(f"/api/projects/{project.id}/events").json()["data"]
        self.assertEqual(events[-1]["operation"], "dataset.uploaded")

    def test_bad_dataset_upload_is_invalid_input_and_unknown_ids_are_not_found(self):
        project = self.store.create("Дані")
        refused = self.client.post(
            f"/api/projects/{project.id}/datasets", files={"file": ("notes.txt", b"a\n1\n")}
        )
        self.assertEqual(refused.status_code, 422)
        self.assertIn("CSV і XLSX", refused.json()["error"]["message"])
        missing_project = self.client.post(
            f"/api/projects/{uuid4()}/datasets", files={"file": ("a.csv", b"a\n1\n")}
        )
        self.assertEqual(missing_project.status_code, 404)
        self.assertEqual(self.client.get(f"/api/datasets/{uuid4()}").status_code, 404)

    def test_metadata_round_trip_over_http(self):
        project = self.store.create("Дані")
        content = "x;колір\n1;червоний\n2;синій\n3;червоний\n".encode()
        dataset = self.client.post(
            f"/api/projects/{project.id}/datasets", files={"file": ("d.csv", content)}
        ).json()["data"]
        url = f"/api/datasets/{dataset['id']}/metadata"
        draft = self.client.get(url).json()["data"]
        self.assertFalse(draft["saved"])
        self.assertEqual([c["kind"] for c in draft["document"]["columns"]], ["number", "category"])
        document = draft["document"]
        document["columns"][0].update(label="Ікс", role="target", range_max=2)
        saved = self.client.put(url, json={"document": document, "confirm": True})
        self.assertEqual(saved.status_code, 200, saved.text)
        body = saved.json()["data"]
        self.assertTrue(body["saved"])
        self.assertIsNotNone(body["confirmed_at"])
        self.assertTrue(any("3 > 2" in i["message"] for i in body["issues"]))
        document["columns"] = document["columns"][:1]
        self.assertEqual(self.client.put(url, json={"document": document}).status_code, 422)
        text = self.client.post(url + "/sources/text", json={"text": "x — номер"})
        self.assertEqual(text.status_code, 200, text.text)
        upload = self.client.post(
            url + "/sources/file", files={"file": ("опис.txt", "колір — колір".encode())}
        )
        self.assertEqual(upload.status_code, 200, upload.text)
        refused = self.client.post(url + "/sources/file", files={"file": ("a.pdf", b"%PDF")})
        self.assertEqual(refused.status_code, 422)
        sources = self.client.get(url + "/sources").json()["data"]
        self.assertEqual([s["kind"] for s in sources], ["text", "file"])

    def test_openapi_uses_shared_request_and_response_schemas(self):
        specification = self.client.get("/openapi.json").json()
        schemas = specification["components"]["schemas"]
        self.assertIn("ProjectCreate", schemas)
        self.assertIn("ProjectView", schemas)
        self.assertIn("Failure", schemas)


if __name__ == "__main__":
    unittest.main()
