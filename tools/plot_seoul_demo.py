import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tmp" / "plot-dependencies"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib-cache"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

font_manager.fontManager.addfont(ROOT / "src/data_story/assets/fonts/OpenSans.ttf")
plt.rcParams.update(
    {
        "font.family": "Open Sans",
        "font.size": 15,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": "#C3C6CA",
        "axes.labelcolor": "#202124",
        "xtick.color": "#7A7F86",
        "ytick.color": "#7A7F86",
        "svg.fonttype": "path",
    }
)
folder = ROOT / "deliverables" / "seoul-demo"


def rows(name):
    with (folder / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


hourly = rows("hourly.csv")
fig, ax = plt.subplots(figsize=(12.8, 6.4))
fig.subplots_adjust(left=0.09, right=0.97, top=0.77, bottom=0.19)
x = [int(r["hour"]) for r in hourly]
y = [float(r["mean"]) for r in hourly]
ax.bar(x, y, color=["#1B4F8A" if hour == 18 else "#C3C6CA" for hour in x], width=0.74)
ax.set_ylim(0, 1850)
ax.set_xticks(range(0, 24, 2))
ax.set_xlabel("Година доби")
ax.set_ylabel("Середня кількість прокатів за годину")
ax.grid(axis="y", color="#E6E5E0")
ax.set_axisbelow(True)
ax.tick_params(length=0)
ax.text(
    18,
    y[18] + 50,
    f"{y[18]:,.0f}".replace(",", " "),
    ha="center",
    color="#1B4F8A",
    fontsize=20,
    fontweight="bold",
)
fig.text(
    0.09, 0.91, "Найвищий середній попит — о 18:00", fontsize=24, fontweight="bold", color="#202124"
)
fig.text(
    0.09,
    0.845,
    "Відкритий прокат · 8 465 годин спостереження · грудень 2017 — листопад 2018",
    fontsize=14,
    color="#7A7F86",
)
fig.text(
    0.09,
    0.055,
    "UCI Seoul Bike Sharing Demand · CC BY 4.0. 295 годин закритої системи виключено.",
    fontsize=12,
    color="#7A7F86",
)
for extension in ["svg", "png"]:
    fig.savefig(folder / f"hourly.{extension}", dpi=150, facecolor="white")
plt.close(fig)
seasonal = rows("seasonal.csv")
labels = {"Summer": "Літо", "Autumn": "Осінь", "Spring": "Весна", "Winter": "Зима"}
fig, ax = plt.subplots(figsize=(12.8, 6.4))
fig.subplots_adjust(left=0.12, right=0.9, top=0.76, bottom=0.2)
means = [float(r["mean"]) for r in seasonal]
ax.barh(range(4), means, color=["#1B4F8A"] + ["#C3C6CA"] * 3, height=0.55)
ax.set_yticks(range(4), [labels[r["season"]] for r in seasonal])
ax.invert_yaxis()
ax.set_xlim(0, max(means) * 1.2)
ax.set_xlabel("Середня кількість прокатів за годину")
ax.tick_params(length=0)
ax.spines["bottom"].set_visible(False)
for i, (value, r) in enumerate(zip(means, seasonal)):
    ax.text(
        value + 18,
        i,
        f"{value:,.0f}".replace(",", " ") + f"  ·  n={r['n']}",
        va="center",
        fontsize=16,
    )
fig.text(
    0.12, 0.91, "Влітку середній попит найвищий", fontsize=24, fontweight="bold", color="#202124"
)
fig.text(
    0.12, 0.845, "Порівняння сезонів за годинами відкритої системи", fontsize=15, color="#7A7F86"
)
fig.text(
    0.12,
    0.055,
    "UCI Seoul Bike Sharing Demand · CC BY 4.0. Різниця середніх не доводить причину.",
    fontsize=12,
    color="#7A7F86",
)
for extension in ["svg", "png"]:
    fig.savefig(folder / f"seasonal.{extension}", dpi=150, facecolor="white")
plt.close(fig)
print("Saved hourly/seasonal plots; Matplotlib", matplotlib.__version__)
