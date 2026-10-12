"""Train, persist and audit linear regression results linked to saved train/test matrices."""

import hashlib
import json
from datetime import datetime, timezone
from time import perf_counter
from typing import cast
from uuid import uuid4

import numpy as np
import pandas as pd
import sklearn

from .analytics import Kind
from .model import (
    INFERENCE_VERSION,
    ModelError,
    ModelNotFound,
    check_matrices,
    train_linear_regression,
)
from .model_check import diagnostics
from .preparation import PreparationError
from .projects import ProjectStore
from .storage import connect
from .training_store import TrainingStore


def _row(row) -> dict:
    document = json.loads(row["document"])
    if document["inference"].get("version", 1) < INFERENCE_VERSION:
        reason = (
            "Статистику значущості збережено попереднім методом; її не показуємо. "
            "Для актуальних p-value підготуйте нові вибірки з іншим зерном поділу й навчіть модель."
        )
        for coefficient in [document["intercept_inference"], *document["coefficients"]]:
            coefficient.update(std_error=None, t=None, p_value=None, stars="", reason=reason)
        document["inference"]["reason"] = reason
        document["warnings"] = list(dict.fromkeys([*document["warnings"], reason]))
    return {
        "id": row["id"],
        "training_run_id": row["training_run_id"],
        "created_at": row["created_at"],
        "document": document,
    }


class ModelStore:
    def __init__(self, training: TrainingStore):
        self.training = training
        self.database = training.datasets.database
        self.analytics = training.datasets.analytics

    @staticmethod
    def _source(document: dict) -> str:
        return json.dumps(document, sort_keys=True, ensure_ascii=False, allow_nan=False)

    def _persist(self, project_id: str, model_id: str, document: dict, arrays: dict) -> list[dict]:
        source = self._source(document)
        if self.analytics.result(project_id, "model_metrics", model_id, source) is not None:
            return []
        coefficients = pd.DataFrame(
            [
                {
                    "name": "(intercept)",
                    "value": document["intercept"],
                    **document["intercept_inference"],
                    "term_type": "intercept",
                },
                *[{**c, "term_type": "feature"} for c in document["coefficients"]],
            ]
        )
        metrics = pd.DataFrame(
            [
                {"split": split, "metric": metric, "value": value}
                for split, values in document["metrics"].items()
                for metric, value in (
                    values.items() if isinstance(values, dict) else [(split, values)]
                )
                if metric != "r2_reason"
            ]
        )
        run = self.training.get(project_id, document["training_run_id"])["document"]
        parts = []
        weights = np.array([c["value"] for c in document["coefficients"]])
        for split in ("train", "test"):
            predicted = document["intercept"] + arrays["x_" + split] @ weights
            parts.append(
                pd.DataFrame(
                    {
                        "split": split,
                        "source_row": run[split + "_positions"],
                        "actual": arrays["y_" + split],
                        "predicted": predicted,
                        "residual": arrays["y_" + split] - predicted,
                    }
                )
            )
        predictions = pd.concat(parts, ignore_index=True)
        references = []
        try:
            for kind, frame in (
                ("coefficients", coefficients),
                ("model_metrics", metrics),
                ("predictions", predictions.drop(columns="residual")),
                ("residuals", predictions[["split", "source_row", "predicted", "residual"]]),
            ):
                references.append(
                    self.analytics.put(project_id, cast(Kind, kind), model_id, frame, source=source)
                )
            self.analytics.save_result(project_id, "model_metrics", model_id, source, document, [])
        except BaseException:
            for reference in reversed(references):
                self.analytics.discard(reference)
            raise
        return references

    def train(self, project_id: str, training_run_id: str) -> dict:
        ProjectStore(self.database).get(project_id)
        started = perf_counter()
        audit: dict = {"training_run_id": training_run_id, "estimator": "LinearRegression"}
        references = []
        committed = False
        model_id = None
        document = None
        try:
            with connect(self.database) as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT * FROM model_runs WHERE project_id = ? AND training_run_id = ?",
                    (project_id, training_run_id),
                ).fetchone()
                if existing is not None:
                    return {**_row(existing), "reused": True}
                run = self.training.get(project_id, training_run_id)
                source = run["document"]
                report = source["report"]
                audit.update(
                    dataset_id=run["dataset_id"],
                    dataset_name=source["dataset_name"],
                    sha256=source["sha256"],
                    target=source["choices"]["target"],
                    fields=source["choices"]["features"],
                )
                arrays = self.training.matrices(project_id, training_run_id)
                check_matrices(arrays, report)
                result = train_linear_regression(arrays, report["feature_names"])
                model_id = str(uuid4())
                now = datetime.now(timezone.utc).isoformat()
                document = {
                    "version": 1,
                    **result,
                    "sklearn_version": sklearn.__version__,
                    "training_run_id": training_run_id,
                    "training_created_at": run["created_at"],
                    "matrix_sha256": source["matrix_sha256"],
                    "matrix_sklearn_version": source["sklearn_version"],
                    "dataset_id": run["dataset_id"],
                    "dataset_name": source["dataset_name"],
                    "source_sha256": source["sha256"],
                    "metadata_updated_at": source["metadata_updated_at"],
                    "choices": source["choices"],
                    "transforms": report["transforms"],
                    "preparation_warnings": report["warnings"],
                }
                references = self._persist(project_id, model_id, document, arrays)
                connection.execute(
                    "INSERT INTO model_runs VALUES (?, ?, ?, ?, ?)",
                    (
                        model_id,
                        project_id,
                        training_run_id,
                        now,
                        json.dumps(document, ensure_ascii=False, allow_nan=False),
                    ),
                )
                test = result["metrics"]["test"]
                audit.update(
                    model_id=model_id,
                    train_count=result["train_count"],
                    test_count=result["test_count"],
                    feature_count=result["feature_count"],
                    r2=test["r2"],
                    mae=test["mae"],
                    rmse=test["rmse"],
                    status="success",
                    duration_ms=(perf_counter() - started) * 1000,
                )
                ProjectStore._event(connection, project_id, "model.trained", audit)
            committed = True
            return {
                "id": model_id,
                "training_run_id": training_run_id,
                "created_at": now,
                "document": document,
                "reused": False,
            }
        except (ModelError, PreparationError, LookupError, KeyError, TypeError) as error:
            message = (
                str(error)
                if isinstance(error, (ModelError, PreparationError, LookupError))
                and not isinstance(error, KeyError)
                else "Збережена підготовка має неочікувану структуру. Підготуйте вибірки заново."
            )
            audit.update(
                status="error", error=message, duration_ms=(perf_counter() - started) * 1000
            )
            with connect(self.database) as connection:
                ProjectStore._event(connection, project_id, "model.trained", audit)
            raise ModelError(message) from error
        finally:
            if not committed and references:
                for reference in reversed(references):
                    self.analytics.discard(reference)
                if model_id is not None and document is not None:
                    self.analytics.discard_result(
                        project_id, "model_metrics", model_id, self._source(document)
                    )

    def check(
        self, project_id: str, model_id: str, chart: str, feature: str | None, audit_extra: dict
    ) -> dict:
        """Build one model check view from saved matrices; one audited event per request."""
        model = self.get(project_id, model_id)
        document = model["document"]
        started = perf_counter()
        audit: dict = {
            "model_id": model_id,
            "training_run_id": model["training_run_id"],
            "dataset_name": document["dataset_name"],
            "target": document["choices"]["target"],
            "chart": chart,
            "feature": feature,
            **audit_extra,
        }
        try:
            arrays = self.training.matrices(project_id, model["training_run_id"])
            source = self._source(document) + json.dumps(
                {"diagnostics_version": 1, "chart": chart, "feature": feature}, sort_keys=True
            )
            object_id = model_id + "." + chart + "." + str(feature)
            # Field names may be long; keep catalog identifiers bounded.
            object_id = model_id + "." + hashlib.sha256(object_id.encode()).hexdigest()
            view = self.analytics.result(project_id, "chart_data", object_id, source)
            audit["reused"] = view is not None
            if view is None:
                view = diagnostics(document, arrays, chart, feature)
                self.analytics.save_result(
                    project_id,
                    "chart_data",
                    object_id,
                    source,
                    view,
                    [("points", pd.DataFrame(view["points"], columns=["x", "y"]))],
                )
        except (ModelError, PreparationError, KeyError, TypeError) as error:
            message = (
                str(error)
                if isinstance(error, (ModelError, PreparationError))
                else "Збережена модель має неочікувану структуру. Навчіть модель заново."
            )
            audit.update(
                status="error", error=message, duration_ms=(perf_counter() - started) * 1000
            )
            with connect(self.database) as connection:
                ProjectStore._event(connection, project_id, "model.checked", audit)
            raise ModelError(message) from error
        audit.update(
            feature=view["feature"],
            n=view["n"],
            status="success",
            duration_ms=(perf_counter() - started) * 1000,
        )
        with connect(self.database) as connection:
            ProjectStore._event(connection, project_id, "model.checked", audit)
        return {**view, "model_id": model_id, "document": document}

    def list(self, project_id: str) -> list[dict]:
        with connect(self.database) as connection:
            ProjectStore._get(connection, project_id)
            rows = connection.execute(
                "SELECT * FROM model_runs WHERE project_id = ? ORDER BY created_at DESC, id",
                (project_id,),
            ).fetchall()
        return [_row(r) for r in rows]

    def get(self, project_id: str, model_id: str) -> dict:
        with connect(self.database) as connection:
            ProjectStore._get(connection, project_id)
            row = connection.execute(
                "SELECT * FROM model_runs WHERE project_id = ? AND id = ?", (project_id, model_id)
            ).fetchone()
        if row is None:
            raise ModelNotFound("Модель не знайдено в цьому проєкті.")
        model = _row(row)
        document = model["document"]
        source = self._source(document)
        stored = self.analytics.result(project_id, "model_metrics", model_id, source)
        if stored is None:
            arrays = self.training.matrices(project_id, model["training_run_id"])
            self._persist(project_id, model_id, document, arrays)
        else:
            model["document"] = stored
        return model
