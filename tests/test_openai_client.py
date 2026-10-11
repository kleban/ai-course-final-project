"""Stage 08 adapter: Responses API calls, usage, errors and the AI log — with a fake transport.

No real network: httpx.MockTransport stands in for api.openai.com.
"""

import json
import unittest

import httpx
import test_preparation_store as fixtures
from fastapi import FastAPI
from fastapi.testclient import TestClient

from data_story.contracts import Failure, Success
from data_story.openai_client import AiError, OpenAIClient, output_text, usage_of
from data_story.storage import connect
from data_story.web import install_error_handlers, router

KEY = "sk-unit-" + "z" * 30 + "WXYZ"
RESPONSE = {
    "id": "resp_1",
    "status": "completed",
    "output": [
        {"type": "reasoning", "summary": []},
        {"type": "message", "content": [{"type": "output_text", "text": "З'єднання працює."}]},
    ],
    "usage": {
        "input_tokens": 30,
        "output_tokens": 12,
        "total_tokens": 42,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens_details": {"reasoning_tokens": 4},
    },
}


class OpenAIClientTests(unittest.TestCase):
    setUp = fixtures.PreparationStoreTests.setUp

    def client(self, handler, key=KEY):
        self.seen = []

        def record(request):
            self.seen.append(request)
            return handler(request)

        client = OpenAIClient(
            self.database,
            self.service.ai_settings,
            key=lambda: key,
            transport=httpx.MockTransport(record),
        )
        self.service.openai = client
        return client

    def test_respond_uses_task_model_and_records_usage(self):
        client = self.client(lambda r: httpx.Response(200, json=RESPONSE))
        result = client.respond("model_advice", "Інструкція", "Питання", project_id="p1")
        self.assertEqual(result["text"], "З'єднання працює.")
        self.assertEqual(result["model"], "gpt-6.1-sol")
        self.assertEqual(result["usage"]["total_tokens"], 42)
        self.assertEqual(result["usage"]["reasoning_tokens"], 4)
        request = self.seen[0]
        self.assertEqual(request.url.path, "/v1/responses")
        self.assertEqual(request.headers["authorization"], f"Bearer {KEY}")
        body = json.loads(request.content)
        self.assertEqual((body["model"], body["max_output_tokens"], body["store"]),
                         ("gpt-6.1-sol", 2000, False))  # fmt: skip
        call = client.calls()[0]
        self.assertEqual((call["status"], call["task"], call["project_id"]),
                         ("success", "model_advice", "p1"))  # fmt: skip
        self.assertEqual(client.totals()["total_tokens"], 42)

    def test_key_never_stored_or_logged(self):
        client = self.client(lambda r: httpx.Response(200, json=RESPONSE))
        client.respond("eda_advice", "i", "q")
        self.client(lambda r: httpx.Response(401, json={"error": {}}))
        with self.assertRaises(AiError):
            self.service.openai.respond("eda_advice", "i", "q")
        with connect(self.database) as connection:
            dump = json.dumps([list(r) for r in connection.execute("SELECT * FROM ai_calls")])
            events = json.dumps(
                [list(r) for r in connection.execute("SELECT * FROM config_events")]
            )
        self.assertNotIn(KEY, dump + events)
        self.assertNotIn("WXYZ", dump)

    def test_errors_are_explained_and_logged_without_fallback(self):
        cases = {
            401: "не прийняв ключ",
            404: "Модель не знайдена",
            429: "ліміт",
            500: "помилку 500",
        }
        for status, text in cases.items():
            client = self.client(lambda r, s=status: httpx.Response(s, json={}))
            with self.assertRaises(AiError) as caught:
                client.respond("model_explain", "i", "q")
            self.assertIn(text, str(caught.exception))
            self.assertEqual(len(self.seen), 1)  # no retry, no other model
        client = self.client(lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow")))
        with self.assertRaises(AiError):
            client.respond("model_explain", "i", "q")
        client = self.client(lambda r: httpx.Response(200, json=RESPONSE), key=None)
        with self.assertRaises(AiError) as caught:
            client.respond("model_explain", "i", "q")
        self.assertIn(".env", str(caught.exception))
        self.assertEqual(self.seen, [])
        self.assertEqual(client.totals()["errors"], 6)

    def test_local_task_refused(self):
        client = self.client(lambda r: httpx.Response(200, json=RESPONSE))
        with self.assertRaises(AiError):
            client.respond("knowledge_search", "i", "q")
        with self.assertRaises(AiError):
            client.respond("unknown", "i", "q")
        self.assertEqual(self.seen, [])

    def test_access_check_is_free_and_per_model(self):
        def handler(request):
            if request.url.path.endswith("gpt-6.1-sol"):
                return httpx.Response(404, json={})
            return httpx.Response(200, json={"id": "gpt-6-luna"})

        client = self.client(handler)
        result = {r["model"]: r["available"] for r in client.check_models()}
        self.assertEqual(result, {"gpt-6-luna": True, "gpt-6.1-sol": False})
        self.assertTrue(all(r.method == "GET" for r in self.seen))

    def test_usage_unknown_stays_none(self):
        self.assertEqual(usage_of({})["total_tokens"], None)
        self.assertEqual(output_text({"output_text": "x"}), "x")
        client = self.client(lambda r: httpx.Response(200, json={"output": []}))
        client.respond("eda_advice", "i", "q")
        self.assertEqual(client.totals()["unknown_usage"], 1)

    def test_service_and_http(self):
        self.client(lambda r: httpx.Response(200, json=RESPONSE))
        self.assertIsInstance(self.service.ai_test_request(), Success)
        app = FastAPI()
        app.include_router(router(self.service))
        install_error_handlers(app)
        with TestClient(app) as http:
            self.assertEqual(http.post("/api/configuration/ai/check").status_code, 200)
            calls = http.get("/api/configuration/ai/calls").json()["data"]
            self.assertGreaterEqual(calls["totals"]["calls"], 2)
        self.client(lambda r: httpx.Response(401, json={}))
        self.assertIsInstance(self.service.ai_test_request(), Failure)
