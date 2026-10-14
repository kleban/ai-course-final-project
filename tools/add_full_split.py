"""History 146: add a Seoul split with every usable field to the working database.

The split of history 137 had 5 fields; models now choose their own fields (D-107), so the split
takes all 11. Adds the split and one model on all fields; nothing is deleted (the old model
keeps its conclusions). No OpenAI calls. Run with the server STOPPED.

  .venv\\Scripts\\python.exe tools\\add_full_split.py [--database PATH]
"""

import argparse
import json
import shutil
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from data_story.contracts import Failure  # noqa: E402
from data_story.projects import ProjectStore  # noqa: E402
from data_story.service import ProjectService  # noqa: E402

PROJECT = "Прокат велосипедів у Сеулі"
DATASET = "Відкритий прокат"
TARGET = "Rented Bike Count"
FEATURES = [
    "Hour",
    "Temperature(°C)",
    "Humidity(%)",
    "Wind speed (m/s)",
    "Visibility (10m)",
    "Dew point temperature(°C)",
    "Solar Radiation (MJ/m2)",
    "Rainfall(mm)",
    "Snowfall (cm)",
    "Seasons",
    "Holiday",
]
RUNTIME = ROOT / "runtime" / "data-story.sqlite3"


def data(result):
    if isinstance(result, Failure):
        raise RuntimeError(f"{result.error.code}: {result.error.message}")
    return result.data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=RUNTIME)
    parser.add_argument("--out", type=Path, default=ROOT / "tmp" / "split-146.json")
    args = parser.parse_args()
    database = args.database.resolve()
    if database == RUNTIME.resolve():
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 8765)) == 0:
                print("Сервіс працює на 8765. Спершу Stop.cmd.")
                return 1
        backup = ROOT / "tmp" / "runtime-before-146"
        if not backup.exists():
            shutil.copytree(
                database.parent, backup, ignore=shutil.ignore_patterns("dependencies", "*.lock")
            )
            print(f"Резервна копія: {backup.relative_to(ROOT)}", flush=True)
    service = ProjectService(ProjectStore(database))
    project = next(p for p in service.store.list_projects() if p.name == PROJECT)
    datasets = service.datasets.list_datasets(str(project.id))
    dataset = next(d for d in datasets if Path(d.name).stem == DATASET)
    for run in data(service.training_runs(project.id)):
        same = run["document"]["choices"]["features"] == FEATURES
        if run["dataset_id"] == str(dataset.id) and same:
            print("Вибірки з усіма полями вже є — нічого не змінюю.")
            return 0
    run = data(
        service.training_prepare(
            project.id,
            {
                "dataset_id": str(dataset.id),
                "target": TARGET,
                "features": FEATURES,
                "encoding": "onehot",
                "test_percent": 30,
                "seed": 42,
            },
        )
    )
    report = run["document"]["report"]
    print(
        f"Вибірки: {report['train_count']}/{report['test_count']} рядків, "
        f"{len(FEATURES)} полів, {report['feature_count']} стовпців",
        flush=True,
    )
    model = data(service.model_train(project.id, {"training_run_id": run["id"]}))
    metrics = model["document"]["metrics"]
    test = metrics["test"]
    print(f"Модель на всіх полях: R² тест {test['r2']:.4f}, MAE {test['mae']:.1f}", flush=True)
    steps = {}
    for criterion in ("adj_r2", "aic", "bic"):
        # Preview only on a copy; on the working base the author runs stepwise in the UI.
        if database != RUNTIME.resolve():
            chosen = data(
                service.model_stepwise(
                    project.id, {"training_run_id": run["id"], "criterion": criterion}
                )
            )["selection"]["features"]
            steps[criterion] = chosen
            print(f"Stepwise {criterion}: {', '.join(chosen)}", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "training_run_id": run["id"],
                "model_id": model["id"],
                "metrics": metrics,
                "stepwise_preview": steps,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
