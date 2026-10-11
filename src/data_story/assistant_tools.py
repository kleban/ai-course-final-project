"""Model operations described for the future AI assistant (stage 08–09).

No OpenAI calls here. Each tool has a JSON schema of its arguments in function-calling form and
calls the same ``ProjectService`` method as the UI and HTTP API, so an assistant can later
advise («Порадь»), execute an explicit task («Виконай») or explain a saved result
(«Поясни результат») without new domain logic. See planning/ai-assistant.md.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .contracts import (
    ErrorInfo,
    Failure,
    KnowledgeQuery,
    MetadataDraftQuery,
    ModelCheckQuery,
    ModelTrainQuery,
    ProjectDraftQuery,
    Success,
)
from .model import explain
from .service import ProjectService, execute, validate_input

Mode = Literal["advise", "execute", "explain"]


class NoArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelResultQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str


@dataclass(frozen=True)
class AssistantTool:
    name: str
    mode: Mode
    description: str
    arguments: type[BaseModel]
    changes_data: bool
    handler: Callable[[ProjectService, str, dict], Success | Failure]

    def schema(self) -> dict:
        parameters = self.arguments.model_json_schema()
        parameters.pop("title", None)
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }


def _training_runs(service: ProjectService, project_id: str, _args: dict) -> Success | Failure:
    runs = service.training_runs(project_id)
    models = service.model_runs(project_id)
    if isinstance(runs, Failure):
        return runs
    trained = (
        {m["training_run_id"]: m["id"] for m in models.data} if isinstance(models, Success) else {}
    )
    return Success(
        data=[
            {
                "training_run_id": r["id"],
                "dataset_name": r["document"]["dataset_name"],
                "target": r["document"]["choices"]["target"],
                "features": r["document"]["choices"]["features"],
                "train_count": r["document"]["report"]["train_count"],
                "test_count": r["document"]["report"]["test_count"],
                "feature_count": r["document"]["report"]["feature_count"],
                "created_at": r["created_at"],
                "model_id": trained.get(r["id"]),
            }
            for r in runs.data
        ]
    )


def _train(service: ProjectService, project_id: str, args: dict) -> Success | Failure:
    return service.model_train(project_id, args)


def _explain(service: ProjectService, project_id: str, args: dict) -> Success | Failure:
    found = service.model_run(project_id, str(args.get("model_id", "")))
    if isinstance(found, Failure):
        return found
    document = found.data["document"]
    return Success(
        data={
            "model_id": found.data["id"],
            "target": document["choices"]["target"],
            "metrics": document["metrics"],
            "coefficients": document["coefficients"],
            "intercept": document["intercept"],
            "explanation": explain(document),
            "warnings": document["warnings"] + document["preparation_warnings"],
            "limitations": document["limitations"],
            "provenance": {
                key: document[key]
                for key in (
                    "dataset_name",
                    "source_sha256",
                    "training_run_id",
                    "matrix_sha256",
                    "sklearn_version",
                )
            },
        }
    )


def _check(service: ProjectService, project_id: str, args: dict) -> Success | Failure:
    result = service.model_check(project_id, args)
    if isinstance(result, Success):
        result.data.pop("svg", None)  # the assistant gets numbers and text, the UI draws
    return result


def _knowledge(service: ProjectService, _project_id: str, args: dict) -> Success | Failure:
    return service.knowledge_search(args)


def _project_draft(service: ProjectService, project_id: str, args: dict) -> Success | Failure:
    from .assistant_drafts import propose_project

    return execute(
        lambda: {
            "proposal": propose_project(
                service, project_id, validate_input(ProjectDraftQuery, args).model_dump(mode="json")
            )
        }
    )


def _metadata_draft(service: ProjectService, project_id: str, args: dict) -> Success | Failure:
    from .assistant_drafts import propose_metadata

    return execute(
        lambda: {
            "proposal": propose_metadata(
                service,
                project_id,
                validate_input(MetadataDraftQuery, args).model_dump(mode="json"),
            )
        }
    )


TOOLS: dict[str, AssistantTool] = {
    tool.name: tool
    for tool in (
        AssistantTool(
            "propose_project_description",
            "execute",
            "Підготувати українську Markdown-чернетку опису проєкту з його мети. "
            "Показує пропозицію для перегляду; нічого не зберігає. Користувач застосує її кнопкою.",
            ProjectDraftQuery,
            False,
            _project_draft,
        ),
        AssistantTool(
            "propose_metadata",
            "execute",
            "Запропонувати опис набору та зміни описів, назв, одиниць, типів і ролей відомих полів "
            "на основі наданих сирих описів. Невідомі одиниці й значення не вигадувати. "
            "Лише чернетка для перегляду; нічого не зберігає і не підтверджує.",
            MetadataDraftQuery,
            False,
            _metadata_draft,
        ),
        AssistantTool(
            "list_training_runs",
            "advise",
            "Показати збережені навчальні/тестові вибірки проєкту й чи навчена на них модель.",
            NoArguments,
            False,
            _training_runs,
        ),
        AssistantTool(
            "train_linear_regression",
            "execute",
            "Навчити LinearRegression (scikit-learn) на навчальній частині обраних збережених "
            "вибірок і оцінити на тестовій. Повторний виклик повертає збережений результат.",
            ModelTrainQuery,
            True,
            _train,
        ),
        AssistantTool(
            "explain_model_result",
            "explain",
            "Повернути збережені показники, коефіцієнти, попередження, обмеження й походження "
            "моделі для пояснення результату без нових обчислень.",
            ModelResultQuery,
            False,
            _explain,
        ),
        AssistantTool(
            "search_knowledge",
            "advise",
            "Знайти в базі знань правила (візуалізація, підготовка даних, показники й "
            "коефіцієнти регресії, перевірка моделі) з джерелом і розділом для поради чи "
            "пояснення. Пошук локальний.",
            KnowledgeQuery,
            False,
            _knowledge,
        ),
        AssistantTool(
            "build_model_chart",
            "execute",
            "Побудувати або замінити графік перевірки моделі на тестовій частині: "
            "regression (ціль від обраної числової ознаки з лінією моделі), residuals "
            "(похибки проти прогнозу) або actual (прогноз проти факту); параметри стилю "
            "необов'язкові. Дані не змінює.",
            ModelCheckQuery,
            False,
            _check,
        ),
    )
}


def run_tool(service: ProjectService, project_id: str, name: str, args: dict) -> Success | Failure:
    tool = TOOLS.get(name)
    if tool is None:
        return Failure(error=ErrorInfo(code="not_found", message="Інструмент не знайдено."))
    return tool.handler(service, project_id, args)
