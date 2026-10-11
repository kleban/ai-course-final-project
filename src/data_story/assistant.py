"""AI assistant (stage 09, first piece): «Порадь», «Виконай», «Поясни результат» in a project.

The assistant is called only by the user. It gathers a compact context (project, saved
results of the current block, matching knowledge rules with sources), sends one task to
OpenAI through the retrying client and, in «Виконай», lets the model call only the
registered tools for the current project, up to the configured step limit.
"""

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Literal
from uuid import uuid4

from .ai_settings import TASKS
from .assistant_tools import TOOLS, run_tool
from .contracts import Failure
from .openai_client import AiError, function_calls, output_text
from .projects import ProjectStore
from .storage import connect

Mode = Literal["advise", "execute", "explain"]
MODES = {"advise": "Порадь", "execute": "Виконай", "explain": "Поясни результат"}
BLOCKS = {
    "data": "Дані",
    "eda": "Оглядовий аналіз",
    "preparation": "Підготовка даних",
    "model": "Модель",
    "validation": "Перевірка моделі",
}
# Which configured task (and so which model chain) serves a block and mode.
TASK_FOR = {
    ("data", "advise"): "next_steps",
    ("data", "execute"): "metadata_draft",
    ("data", "explain"): "eda_explain",
    ("eda", "advise"): "eda_advice",
    ("eda", "execute"): "chart_command",
    ("eda", "explain"): "eda_explain",
    ("preparation", "advise"): "preparation_advice",
    ("preparation", "execute"): "preparation_advice",
    ("preparation", "explain"): "preparation_advice",
    ("model", "advise"): "model_advice",
    ("model", "execute"): "model_advice",
    ("model", "explain"): "model_explain",
    ("validation", "advise"): "next_steps",
    ("validation", "execute"): "validation_explain",
    ("validation", "explain"): "validation_explain",
}
# Quick prompts shown as one-click chips; the user can still type anything.
SUGGESTIONS = {
    "data": ["Що перевірити в даних перед аналізом?", "Які поля можуть бути ціллю?"],
    "eda": ["Який графік подивитися далі?", "Що видно в пропусках?"],
    "preparation": ["Як обробити пропуски?", "Чи потрібне кодування категорій?"],
    "model": ["Поясни результат моделі", "Які ознаки статистично значущі?"],
    "validation": ["Що показує графік похибок?", "Чи можна довіряти моделі?"],
}
RULES = """Ти — AI-помічник аналітика в сервісі Data Story. Відповідай українською, коротко:
до 6 речень або короткий список. Використовуй лише факти з контексту нижче й результати
інструментів; не вигадуй чисел. Посилайся на правила бази знань у форматі
[Джерело: назва розділу]. Розрахунки виконує сервіс, не ти.

Враховуй сторінку, на якій зараз користувач (розділ «Поточна сторінка» в контексті), і
будуй відповідь від неї. Ти ведеш діалог, а не лише виконуєш накази: якщо завдання
неоднозначне, бракує даних (наприклад, не зрозуміло, який набір, ціль чи модель), або дія
змінить результати проєкту і користувач ще не підтвердив її — спершу виклич ask_user з одним
коротким питанням і 2–4 варіантами відповіді. Не став питань, якщо все зрозуміло; не
повторюй питання, на яке вже є відповідь в історії розмови."""
MAX_QUESTION = 2000
MAX_HISTORY = 10
ASK_USER = {
    "type": "function",
    "name": "ask_user",
    "description": "Поставити користувачу одне коротке уточнювальне питання перед відповіддю "
    "чи дією. Розмова зупиняється, доки користувач не відповість.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Питання українською, одне речення."},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2–4 короткі варіанти відповіді.",
            },
        },
        "required": ["question"],
    },
    "strict": False,
}


class AssistantError(AiError):
    """The assistant request is not valid."""


@dataclass
class Answer:
    text: str
    sources: list[dict]
    tools: list[dict]
    model: str
    level: int
    steps: int
    attempts: list[dict]
    usage_total: int | None
    question: dict | None = None


def _compact(value, limit: int = 3000) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " …[скорочено]"


class Assistant:
    def __init__(self, service):
        self.service = service

    def page_context(self, project_id: str, block: str, page: dict) -> dict:
        """What the user sees now: block, selected dataset with its fields, chart, model."""
        current: dict = {"блок": BLOCKS[block]}
        dataset_id = page.get("dataset_id")
        if dataset_id:
            found = self.service.dataset(dataset_id)
            if not isinstance(found, Failure) and str(found.data.project_id) == project_id:
                dataset = found.data
                current["набір"] = {
                    "name": dataset.name, "rows": dataset.row_count, "columns": dataset.column_count,
                }  # fmt: skip
                metadata = self.service.metadata(dataset_id)
                if not isinstance(metadata, Failure):
                    current["поля"] = [
                        {"name": c.name, "kind": c.kind, "role": c.role, "label": c.label}
                        for c in metadata.data.document.columns[:40]
                    ]
                    current["метадані підтверджено"] = bool(metadata.data.confirmed_at)
        if page.get("tool"):
            current["інструмент"] = page["tool"]
        run_id = page.get("run_id")
        if run_id and block == "validation":
            found_model = self.service.model_run(project_id, run_id)
            if not isinstance(found_model, Failure):
                current["обрана модель"] = run_id
        elif run_id and block == "model":
            current["обрані вибірки"] = run_id
        return current

    def context(self, project_id: str, block: str, page: dict | None = None) -> dict:
        """Compact facts for the model: no table rows, only saved summaries."""
        project = self.service.store.get(project_id)
        context: dict = {
            "project": {
                "name": project.name,
                "type": project.project_type,
                "description": project.description[:1500],
            },  # fmt: skip
            "Поточна сторінка": self.page_context(project_id, block, page or {}),
        }
        datasets = self.service.list_datasets(project_id)
        if not isinstance(datasets, Failure):
            context["datasets"] = [
                {"id": str(d.id), "name": d.name, "rows": d.row_count, "columns": d.column_count}
                for d in datasets.data[:10]
            ]
        if block in ("model", "validation", "preparation"):
            runs = run_tool(self.service, project_id, "list_training_runs", {})
            if not isinstance(runs, Failure):
                context["training_runs"] = runs.data[:5]
        if block in ("model", "validation"):
            models = self.service.model_runs(project_id)
            if not isinstance(models, Failure) and models.data:
                chosen = (page or {}).get("run_id") if block == "validation" else None
                model_id = (
                    chosen if chosen in [m["id"] for m in models.data] else models.data[0]["id"]
                )
                explained = run_tool(
                    self.service, project_id, "explain_model_result", {"model_id": model_id}
                )
                if not isinstance(explained, Failure):
                    context["latest_model"] = explained.data
        return context

    def ask(
        self,
        project_id: str,
        block: str,
        mode: str,
        question: str,
        page: dict | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        if block not in BLOCKS:
            raise AssistantError("Невідомий блок для помічника.")
        if mode not in MODES:
            raise AssistantError("Оберіть дію: «Порадь», «Виконай» або «Поясни результат».")
        question = " ".join(str(question).split())
        if not question:
            raise AssistantError("Напишіть завдання або оберіть підказку.")
        if len(question) > MAX_QUESTION:
            raise AssistantError(f"Завдання задовге: до {MAX_QUESTION} символів.")
        ProjectStore(self.service.store.database).get(project_id)
        task = TASK_FOR[(block, mode)]
        started = perf_counter()
        audit: dict = {"block": block, "mode": mode, "task": task, "question": question[:300],
                       "page": page or {}, "history_turns": len(history or [])}  # fmt: skip
        try:
            answer = self._solve(project_id, block, mode, task, question, page or {},
                                 (history or [])[-MAX_HISTORY:])  # fmt: skip
        except (AiError, AssistantError) as error:
            audit.update(status="error", error=str(error),
                         duration_ms=(perf_counter() - started) * 1000)  # fmt: skip
            with connect(self.service.store.database) as connection:
                ProjectStore._event(connection, project_id, "assistant.asked", audit)
            raise
        audit.update(
            status="clarifying" if answer.question else "success",
            model=answer.model,
            level=answer.level,
            steps=answer.steps,
            tools=[t["name"] for t in answer.tools],
            sources=[s["id"] for s in answer.sources],
            usage_total=answer.usage_total,
            answer=answer.text[:500],
            duration_ms=(perf_counter() - started) * 1000,
        )
        with connect(self.service.store.database) as connection:
            ProjectStore._event(connection, project_id, "assistant.asked", audit)
        return {**vars(answer), "task": task, "mode": mode, "block": block}

    def _solve(self, project_id: str, block: str, mode: str, task: str, question: str,
               page: dict, history: list[dict]) -> Answer:  # fmt: skip
        found = self.service.knowledge.search(question, 3)
        sources = found["hits"]
        rules = "\n".join(f"- [{h['section']}] {h['text']}" for h in sources) or "немає"
        instruction = self.service.instructions.get(self.service.store.get(project_id).project_type)
        instructions = (
            f"{RULES}\n\nДія: {MODES[mode]}. Блок: {BLOCKS[block]}.\n\n"
            f"Інструкція типу проєкту:\n{instruction.text[:3000]}\n\n"
            f"Правила бази знань:\n{rules}\n\n"
            f"Контекст проєкту (JSON):\n{_compact(self.context(project_id, block, page), 5000)}"
        )
        client = self.service.openai
        config = self.service.ai_settings.get()
        tools = [ASK_USER]
        if mode == "execute":
            tools += [t.schema() | {"strict": False} for t in TOOLS.values()]
        items: list = [
            {"role": "assistant" if turn.get("role") == "assistant" else "user",
             "content": str(turn.get("text", ""))[:2000]}
            for turn in history
        ]  # fmt: skip
        items.append({"role": "user", "content": question})
        run_id, models = str(uuid4()), None
        attempts: list[dict] = []
        used: list[dict] = []
        totals: list[int] = []
        for step in range(1, config.max_agent_steps + 1):
            extra: dict = {
                "instructions": instructions,
                "input": items,
                "tools": tools,
                "include": ["reasoning.encrypted_content"],
            }

            def check(payload: dict) -> str | None:
                if not output_text(payload).strip() and not function_calls(payload):
                    return "Модель повернула порожню відповідь."
                return None

            result = client.run(task, extra, check, project_id=project_id, models=models,
                                run_id=run_id)  # fmt: skip
            models = result["remaining"]  # keep the working level for the next steps
            attempts += result["attempts"]
            if result["usage_total"] is not None:
                totals.append(result["usage_total"])
            payload = result["payload"]
            calls = function_calls(payload)
            usage = sum(totals) if totals else None
            clarify = next((c for c in calls if c.get("name") == "ask_user"), None)
            if clarify is not None:
                asked = _arguments(clarify) or {}
                text = str(asked.get("question") or "Уточніть, будь ласка, завдання.")
                options = [str(o) for o in (asked.get("options") or [])][:4]
                return Answer(text, sources, used, result["model"], result["level"], step,
                              attempts, usage, {"text": text, "options": options})  # fmt: skip
            if not calls:
                return Answer(output_text(payload), sources, used, result["model"],
                              result["level"], step, attempts, usage)  # fmt: skip
            items += payload.get("output") or []
            for call in calls:
                outcome = self._tool(project_id, call)
                used.append({"name": call.get("name"), "ok": outcome["ok"]})
                items.append({"type": "function_call_output", "call_id": call.get("call_id"),
                              "output": _compact(outcome, 6000)})  # fmt: skip
        raise AiError(
            f"Помічник зупинився на ліміті кроків ({config.max_agent_steps}). "
            "Збільште ліміт у «Моделі AI» або уточніть завдання.",
            attempts,
        )

    def _tool(self, project_id: str, call: dict) -> dict:
        """Run one registered tool in the current project; unknown names are refused."""
        name = call.get("name")
        if name not in TOOLS:
            return {"ok": False, "error": f"Інструмент {name} недоступний."}
        args = _arguments(call)
        if args is None:
            return {"ok": False, "error": "Аргументи інструмента мають бути JSON-об'єктом."}
        result = run_tool(self.service, project_id, name, args)
        if isinstance(result, Failure):
            return {"ok": False, "error": result.error.message}
        return {"ok": True, "data": result.data}


def _arguments(call: dict) -> dict | None:
    try:
        args = json.loads(call.get("arguments") or "{}")
    except ValueError:
        return None
    return args if isinstance(args, dict) else None


def tasks_used() -> set[str]:
    return set(TASK_FOR.values()) & set(TASKS)
