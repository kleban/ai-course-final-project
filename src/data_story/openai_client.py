"""OpenAI adapter (stage 08): Responses API over httpx, usage and every call in a local log.

No SDK dependency: the service already ships httpx. The key comes only from ``.env`` (D-76),
is sent only in the Authorization header to api.openai.com and never stored or logged.
There is no silent fallback to another model and no automatic retry.
"""

import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
from dotenv import dotenv_values

from .ai_settings import ENV_FILE, KEY_NAME, MODELS, TASKS, AiSettingsStore
from .storage import connect, ensure_schema

API = "https://api.openai.com/v1"
TIMEOUT = httpx.Timeout(60.0, connect=10.0)
TEXT_LIMIT = 4000  # stored request/response text is cut and marked


class AiError(RuntimeError):
    """An OpenAI call could not be made or did not succeed; the message is for the user."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cut(text: str) -> str:
    return text if len(text) <= TEXT_LIMIT else text[:TEXT_LIMIT] + " …[скорочено]"


def _body(body: dict | None) -> dict | None:
    if body is None:
        return None
    text = json.dumps(body, ensure_ascii=False)
    return body if len(text) <= TEXT_LIMIT else {"скорочено": _cut(text)}


def env_key(env_file: Path = ENV_FILE) -> str | None:
    value = (dotenv_values(env_file).get(KEY_NAME) or "").strip() if env_file.is_file() else ""
    return value or None


def usage_of(payload: dict) -> dict:
    """Actual usage as reported; missing fields stay None (unknown), never 0."""
    usage = payload.get("usage") or {}
    return {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens"),
        "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
    }


def output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts = []
    for item in payload.get("output") or []:
        if item.get("type") == "message":
            for content in item.get("content") or []:
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
    return "".join(parts)


ERRORS = {
    401: "OpenAI не прийняв ключ (401). Перевірте OPENAI_API_KEY у файлі .env.",
    403: "Немає доступу до цієї моделі або дії (403).",
    404: "Модель не знайдена або недоступна для вашого облікового запису (404).",
    429: "Перевищено ліміт запитів або квоту OpenAI (429). Спробуйте пізніше.",
}


class OpenAIClient:
    def __init__(
        self,
        database: Path,
        settings: AiSettingsStore,
        key: Callable[[], str | None] | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self.database = ensure_schema(database)
        self.settings = settings
        self._key = key or (lambda: env_key(settings.env_file))
        self.transport = transport

    def _client(self, key: str) -> httpx.Client:
        return httpx.Client(
            base_url=API,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=TIMEOUT,
            transport=self.transport,
        )

    def _log(self, entry: dict) -> None:
        with connect(self.database) as connection:
            connection.execute(
                "INSERT INTO ai_calls VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["id"],
                    entry["started_at"],
                    entry["task"],
                    entry["model"],
                    entry.get("project_id"),
                    entry["status"],
                    entry["duration_ms"],
                    json.dumps(entry, ensure_ascii=False),
                ),
            )

    def _call(self, method: str, path: str, task: str, model: str, body: dict | None,
              project_id: str | None) -> tuple[dict, dict]:  # fmt: skip
        key = self._key()
        entry: dict = {
            "id": str(uuid4()),
            "started_at": _now(),
            "task": task,
            "model": model,
            "project_id": project_id,
            "request": {
                "method": method,
                "path": path,
                "body": _body(body),
            },
        }
        started = perf_counter()
        try:
            if not key:
                raise AiError("Ключ OpenAI не знайдено у файлі .env (OPENAI_API_KEY).")
            try:
                with self._client(key) as client:
                    response = client.request(method, path, json=body)
            except httpx.TimeoutException as error:
                raise AiError(
                    "OpenAI не відповів вчасно. Перевірте мережу й спробуйте ще раз."
                ) from error
            except httpx.HTTPError as error:
                raise AiError("Немає з'єднання з OpenAI. Перевірте мережу.") from error
            entry["http_status"] = response.status_code
            if response.status_code >= 400:
                raise AiError(
                    ERRORS.get(
                        response.status_code, f"OpenAI повернув помилку {response.status_code}."
                    )
                )
            try:
                payload = response.json()
            except ValueError as error:
                raise AiError("OpenAI повернув відповідь, яку не вдалося прочитати.") from error
        except AiError as error:
            entry.update(
                status="error", error=str(error), duration_ms=(perf_counter() - started) * 1000
            )
            self._log(entry)
            raise
        entry.update(status="success", duration_ms=(perf_counter() - started) * 1000)
        return entry, payload

    def respond(
        self,
        task: str,
        instructions: str,
        text: str,
        project_id: str | None = None,
        max_output_tokens: int | None = None,
    ) -> dict:
        """One explicit Responses API call with the model configured for the task."""
        if task not in TASKS:
            raise AiError("Невідома задача AI.")
        config = self.settings.get()
        model = config.models[task]
        if model == "local" or MODELS[model].kind != "text":
            raise AiError("Для цієї задачі в налаштуваннях не обрано текстову модель OpenAI.")
        body = {
            "model": model,
            "instructions": instructions,
            "input": text,
            "max_output_tokens": max_output_tokens or config.max_output_tokens,
            "store": False,
        }
        entry, payload = self._call("POST", "/responses", task, model, body, project_id)
        answer = output_text(payload)
        entry.update(
            usage=usage_of(payload),
            response_id=payload.get("id"),
            response_status=payload.get("status"),
            incomplete=(payload.get("incomplete_details") or {}).get("reason"),
            response={"text": _cut(answer)},
        )
        self._log(entry)
        return {
            "call_id": entry["id"],
            "model": model,
            "text": answer,
            "usage": entry["usage"],
            "status": payload.get("status"),
            "incomplete": entry["incomplete"],
        }

    def check_models(self) -> list[dict]:
        """Free access check: GET /models/{id} for each configured text model, no generation."""
        models = sorted(
            {m for m in self.settings.get().models.values() if MODELS[m].kind == "text"}
        )
        result = []
        for model in models:
            try:
                entry, payload = self._call(
                    "GET", f"/models/{model}", "access_check", model, None, None
                )
                entry.update(response={"id": payload.get("id")}, usage=None)
                self._log(entry)
                result.append({"model": model, "available": True, "message": "Доступна"})
            except AiError as error:
                result.append({"model": model, "available": False, "message": str(error)})
        return result

    def calls(self, limit: int = 20) -> list[dict]:
        with connect(self.database) as connection:
            rows = connection.execute(
                "SELECT document FROM ai_calls ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(r["document"]) for r in rows]

    def totals(self) -> dict:
        """Known tokens and the number of calls with unknown usage (no money)."""
        calls = self.calls(limit=100000)
        known = [
            c["usage"]
            for c in calls
            if c.get("usage") and c["usage"].get("total_tokens") is not None
        ]
        return {
            "calls": len(calls),
            "errors": sum(c["status"] == "error" for c in calls),
            "total_tokens": sum(u["total_tokens"] for u in known),
            "input_tokens": sum(u.get("input_tokens") or 0 for u in known),
            "output_tokens": sum(u.get("output_tokens") or 0 for u in known),
            "unknown_usage": sum(
                1
                for c in calls
                if c["task"] != "access_check"
                and c["status"] == "success"
                and not (c.get("usage") and c["usage"].get("total_tokens") is not None)
            ),
        }
