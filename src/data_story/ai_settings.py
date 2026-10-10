"""AI settings (stage 08): which OpenAI model serves which task of the analysis pipeline.

The key is never stored or accepted here: it is read only from ``.env`` (``OPENAI_API_KEY``,
D-76) and reported masked. Model choices live in SQLite without secrets; every change is
written to ``config_events``. Task keys are the contract for the future assistant (D-75).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import ROOT
from .configuration import InstructionStore, _now
from .storage import connect, ensure_schema

ENV_FILE = ROOT / ".env"
KEY_NAME = "OPENAI_API_KEY"


@dataclass(frozen=True)
class Model:
    id: str
    title: str
    kind: str  # "text" | "embedding" | "local"


# Candidates from planning/ai-settings.md (OpenAI catalogue read 2026-10-10); not verified for
# the author's account. "local" keeps a task without OpenAI.
MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        Model("gpt-6-luna", "gpt-6-luna · економна, для частих коротких задач", "text"),
        Model("gpt-6.1-sol", "gpt-6.1-sol · сильніша, для складних рішень", "text"),
        Model("text-embedding-3-small", "text-embedding-3-small · вектори для пошуку", "embedding"),
        Model("local", "Без OpenAI · локальний розрахунок", "local"),
    )
}


@dataclass(frozen=True)
class Task:
    key: str
    stage: str
    title: str
    purpose: str
    mode: str  # «Порадь» | «Виконай» | «Поясни результат» | «Пошук»
    kind: str  # allowed model kind
    default: str


STAGES = [
    "Проєкт і дані",
    "Оглядовий аналіз",
    "Підготовка даних",
    "Модель і перевірка",
    "Висновки та звіт",
    "База знань",
]

TASKS: dict[str, Task] = {
    t.key: t
    for t in (
        Task(
            "project_description",
            "Проєкт і дані",
            "Опис проєкту",
            "Чернетка мети й опису проєкту",
            "Виконай",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "metadata_draft",
            "Проєкт і дані",
            "Метадані полів",
            "Опис полів, ролі, одиниці з сирого опису",
            "Виконай",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "eda_advice",
            "Оглядовий аналіз",
            "Поради з огляду",
            "Які поля й графіки переглянути далі",
            "Порадь",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "chart_command",
            "Оглядовий аналіз",
            "Графік за командою",
            "Перебудова графіка з тексту чи голосу",
            "Виконай",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "eda_explain",
            "Оглядовий аналіз",
            "Пояснення графіків",
            "Що видно на статистиці й графіках",
            "Поясни результат",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "preparation_advice",
            "Підготовка даних",
            "Поради з підготовки",
            "Пропуски, категорії, поділ",
            "Порадь",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "model_advice",
            "Модель і перевірка",
            "Рекомендації щодо моделі",
            "Ціль, ознаки, ризики перед навчанням",
            "Порадь",
            "text",
            "gpt-6.1-sol",
        ),
        Task(
            "model_explain",
            "Модель і перевірка",
            "Пояснення моделі",
            "Показники, коефіцієнти, p-value, обмеження",
            "Поясни результат",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "validation_explain",
            "Модель і перевірка",
            "Пояснення перевірки",
            "Графіки похибок і прогнозу проти факту",
            "Поясни результат",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "next_steps",
            "Модель і перевірка",
            "Наступні кроки",
            "Що зробити далі в аналізі",
            "Порадь",
            "text",
            "gpt-6.1-sol",
        ),
        Task(
            "conclusions",
            "Висновки та звіт",
            "Висновки",
            "Висновки з доказами та непевністю",
            "Поясни результат",
            "text",
            "gpt-6.1-sol",
        ),
        Task(
            "report_draft",
            "Висновки та звіт",
            "Чернетка звіту",
            "Текст звіту зі збережених результатів",
            "Виконай",
            "text",
            "gpt-6-luna",
        ),
        Task(
            "knowledge_search",
            "База знань",
            "Пошук правил",
            "Пошук фрагментів бази знань (RAG)",
            "Пошук",
            "embedding",
            "local",
        ),
    )
}


class AiConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    models: dict[str, str] = Field(default_factory=lambda: {k: t.default for k, t in TASKS.items()})
    max_output_tokens: Annotated[int, Field(ge=256, le=32000)] = 2000
    max_agent_steps: Annotated[int, Field(ge=1, le=20)] = 6

    @model_validator(mode="after")
    def known(self) -> "AiConfiguration":
        for key, model in self.models.items():
            if key not in TASKS:
                raise ValueError(f"Невідома задача: {key}.")
            if model not in MODELS:
                raise ValueError(f"Невідома модель: {model}.")
            allowed = {TASKS[key].kind, "local"}
            if MODELS[model].kind not in allowed:
                raise ValueError(f"Модель {model} не підходить для задачі «{TASKS[key].title}».")
        for key, task in TASKS.items():  # new tasks get their default
            self.models.setdefault(key, task.default)
        return self


def key_status(env_file: Path = ENV_FILE) -> dict:
    """Presence and masked tail of the key in .env; the key itself never leaves this function."""
    if not env_file.is_file():
        return {"state": "missing_file", "source": ".env", "masked": None,
                "message": "Файл .env не знайдено. Скопіюйте .env.example у .env і впишіть ключ."}  # fmt: skip
    value = (dotenv_values(env_file).get(KEY_NAME) or "").strip()
    if not value:
        return {"state": "empty", "source": ".env", "masked": None,
                "message": f"У .env немає значення {KEY_NAME}."}  # fmt: skip
    if not value.startswith("sk-") or len(value) < 20:
        return {"state": "suspicious", "source": ".env", "masked": "…" + value[-4:],
                "message": "Значення не схоже на ключ OpenAI (очікується sk-…)."}  # fmt: skip
    return {"state": "found", "source": ".env", "masked": "sk-…" + value[-4:],
            "message": "Ключ знайдено у .env. Доступ до OpenAI ще не перевірявся."}  # fmt: skip


class AiSettingsStore:
    def __init__(self, database: Path, env_file: Path = ENV_FILE):
        self.database = ensure_schema(database)
        self.env_file = env_file

    def get(self) -> AiConfiguration:
        with connect(self.database) as connection:
            row = connection.execute("SELECT document FROM ai_configuration WHERE id=1").fetchone()
        return AiConfiguration.model_validate_json(row["document"]) if row else AiConfiguration()

    def save(self, value: AiConfiguration) -> AiConfiguration:
        value = AiConfiguration.model_validate(value.model_dump())
        with connect(self.database) as connection:
            connection.execute(
                "INSERT INTO ai_configuration VALUES (1, ?, ?) ON CONFLICT(id) "
                "DO UPDATE SET document=excluded.document, updated_at=excluded.updated_at",
                (value.model_dump_json(), _now()),
            )
            InstructionStore._event(connection, "ai", "ai.configuration.saved", value.model_dump())
        return value

    def reset(self) -> AiConfiguration:
        with connect(self.database) as connection:
            connection.execute("DELETE FROM ai_configuration WHERE id=1")
            InstructionStore._event(connection, "ai", "ai.configuration.reset", {})
        return self.get()

    def key(self) -> dict:
        return key_status(self.env_file)

    def model_for(self, task: str) -> str:
        """The configured model for a task; the future adapter reads only this."""
        if task not in TASKS:
            raise KeyError(task)
        return self.get().models[task]
