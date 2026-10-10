"""Stage 07 RAG: rule documents, fragments, local search on Ukrainian control questions."""

import json
import unittest

import test_preparation_store as fixtures
from fastapi import FastAPI
from fastapi.testclient import TestClient

from data_story.assistant_tools import run_tool
from data_story.contracts import Failure, Success
from data_story.knowledge import KnowledgeError, KnowledgeStore, parse
from data_story.storage import connect
from data_story.web import install_error_handlers, router

# Control questions written for the default rules: the expected section must be in the top 3.
CONTROL = [
    ("що означає R квадрат", "R² (R-квадрат) — коефіцієнт детермінації"),
    ("чому біля коефіцієнта стоять зірочки", "p-value і зірочки значущості"),
    ("як заповнити пропуски без витоку даних", "Витік даних"),
    ("графік похибок має форму лійки", "Графік похибок"),
    ("чи повинні стовпчики починатися з нуля", "Стовпці починаються з нуля"),
    ("чи можна порівнювати коефіцієнти різних ознак", "Порівняння коефіцієнтів між собою"),
    ("як закодувати категорії", "Категорії і one-hot кодування"),
    ("кореляція близька до нуля, а залежність є", "Розсіювання і кореляція"),
    ("різниця між MAE і RMSE", "RMSE — корінь середнього квадрата помилки"),
    ("R² на навчальній вибірці набагато вищий ніж на тесті", "Навчальна і тестова частини"),
    ("що таке вільний член", "Вільний член a₀"),
    ("скільки інтервалів у гістограмі", "Гістограма і ширина інтервалу"),
    ("прогноз для значень поза діапазоном", "Екстраполяція"),
    ("ознаки сильно корельовані між собою", "Мультиколінеарність"),
    ("чи заповнювати пропуски в цільовій змінній", "Ціль не заповнюємо"),
]


class KnowledgeTests(unittest.TestCase):
    setUp = fixtures.PreparationStoreTests.setUp

    def test_control_questions_find_expected_rules(self):
        misses = []
        for question, section in CONTROL:
            hits = self.service.knowledge.search(question)["hits"]
            if section not in [h["section"] for h in hits]:
                misses.append((question, [h["section"] for h in hits]))
        self.assertEqual(misses, [])

    def test_unrelated_question_returns_nothing(self):
        result = self.service.knowledge.search("рецепт борщу")
        self.assertEqual(result["hits"], [])
        self.assertIn("не знайдено", result["reason"])

    def test_hits_carry_source_section_and_are_logged(self):
        result = self.service.knowledge_search({"query": "що таке вільний член", "limit": 2})
        self.assertIsInstance(result, Success)
        hit = result.data["hits"][0]
        self.assertEqual(hit["document_id"], "04-regression-coefficients")
        self.assertTrue(hit["source"])
        self.assertLessEqual(len(result.data["hits"]), 2)
        event = self.service.knowledge.events()[0]
        self.assertEqual(event["operation"], "knowledge.searched")
        self.assertEqual(event["query"], "що таке вільний член")
        self.assertEqual(event["hits"][0]["id"], hit["id"])

    def test_defaults_seeded_once_and_edits_rebuild_index(self):
        documents = self.service.knowledge.documents()
        self.assertEqual(len(documents), 5)
        self.assertTrue(all(d["is_default"] for d in documents))
        self.assertGreaterEqual(sum(d["fragments"] for d in documents), 30)
        reopened = KnowledgeStore(self.database)
        self.assertEqual(len(reopened.documents()), 5)
        before = reopened.search("правило про кавові зерна")["hits"]
        self.assertNotIn("Кавові зерна", [h["section"] for h in before])
        text = "# Кава\nДжерело: тест\nПріоритет: 1\n\n## Кавові зерна\nПравило про кавові зерна.\n"
        with connect(self.database) as connection:
            connection.execute(
                "INSERT INTO knowledge_documents VALUES ('09-test', 'Кава', 'тест', 1, ?, 0, 'x')",
                (text,),
            )
        after = reopened.search("правило про кавові зерна")["hits"]
        self.assertEqual(after[0]["section"], "Кавові зерна")

    def test_parse_and_input_errors(self):
        meta, fragments = parse("x", "# T\nДжерело: s\nПріоритет: 2\n\n## A\ntext a\n\n## B\nb\n")
        self.assertEqual((meta["priority"], [f.section for f in fragments]), (2, ["A", "B"]))
        for bad in ("без заголовка", "# T\nтекст без розділів"):
            with self.assertRaises(KnowledgeError):
                parse("x", bad)
        with self.assertRaises(KnowledgeError):
            self.service.knowledge.search("   ")
        self.assertIsInstance(self.service.knowledge_search({"query": ""}), Failure)
        self.assertIsInstance(self.service.knowledge_search({"query": "x" * 501}), Failure)

    def test_http_and_assistant_tool(self):
        app = FastAPI()
        app.include_router(router(self.service))
        install_error_handlers(app)
        with TestClient(app) as client:
            docs = client.get("/api/knowledge/documents")
            self.assertEqual(docs.status_code, 200)
            self.assertEqual(len(docs.json()["data"]), 5)
            found = client.post("/api/knowledge/search", json={"query": "форма лійки похибок"})
            self.assertEqual(found.status_code, 200)
            self.assertEqual(found.json()["data"]["hits"][0]["section"], "Графік похибок")
            self.assertEqual(client.post("/api/knowledge/search", json={}).status_code, 422)
        tool = run_tool(self.service, self.project.id, "search_knowledge", {"query": "витік даних"})
        self.assertIsInstance(tool, Success)
        json.dumps(tool.data)
