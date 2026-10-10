"""Heatmap SVG adapted from SRC-004 slides_4_types.js divCol; no browser calculations."""

from html import escape
from typing import Any

from .chart_configuration import ChartOptions


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def color(value: float, options: ChartOptions) -> str:
    # Lecture divCol: diverging interpolation, fixed center zero and endpoints +/-1.
    start = rgb(options.neutral)
    end = rgb(options.positive if value >= 0 else options.negative)
    t = min(1.0, abs(value))
    return "#{:02x}{:02x}{:02x}".format(*(round(a + (b - a) * t) for a, b in zip(start, end)))


def luminance(color_value: str) -> float:
    values = [v / 255 for v in rgb(color_value)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(a: str, b: str) -> float:
    x, y = sorted((luminance(a), luminance(b)))
    return (y + 0.05) / (x + 0.05)


def contrast_warnings(options: ChartOptions) -> list[str]:
    warnings = []
    if contrast(options.text, options.background) < 4.5:
        warnings.append("Низький контраст тексту й фону: оберіть контрастніші кольори.")
    if contrast(options.negative, options.positive) < 1.2:
        warnings.append("Кольори додатних і від’ємних значень схожі; перевірте розрізнення.")
    return warnings


def field_label(column: dict[str, Any]) -> str:
    label = column["label"] or column["name"]
    if label != column["name"]:
        label += " · " + column["name"]
    if column["unit"]:
        label += " (" + column["unit"] + ")"
    return label


def heatmap_svg(result: dict[str, Any], options: ChartOptions, title: str = "") -> str:
    names = result["fields"]
    columns = {c["name"]: c for c in result["columns"]}
    size, left, top = 64, 240, 170
    width, height = left + len(names) * size + 140, top + max(len(names) * size, 252) + 55
    parts = [
        f'<svg class="heatmap" xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" role="group" '
        f'aria-label="Теплова карта кореляцій Pearson" style="font-family:{options.font};'
        f'background:{options.background}">',
        f'<text x="20" y="35" font-size="{options.title_size}" fill="{options.text}">'
        f"{escape(title or 'Зв’язки числових полів · Pearson')}</text>",
    ]

    def label(x: float, y: float, value: str, anchor: str = "start", rotate: bool = False) -> str:
        transform = f' transform="rotate(-35 {x} {y})"' if rotate else ""
        return (
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{options.label_size}" '
            f'fill="{options.text}"{transform}>{escape(value)}</text>'
        )

    for i, name in enumerate(names):
        full = field_label(columns[name])
        short = full if len(full) <= 25 else full[:22] + "…"
        parts.append(label(left - 12, top + i * size + size / 2 + 5, short, "end"))
        parts.append(label(left + i * size + size / 2, top - 15, short, rotate=True))
        for j, other in enumerate(names):
            if options.lower_triangle and j > i:
                continue
            value, n, reason = result["r"][i][j], result["n"][i][j], result["reasons"][i][j]
            value_text = "—" if value is None else f"{value:.{options.decimals}f}"
            detail = f"{full} ↔ {field_label(columns[other])}: r={value_text}; n={n}"
            detail += f"; виключено пар: {result['row_count'] - n}"
            if reason:
                detail += "; " + reason
            fill = "#E5E7EB" if value is None else color(value, options)
            muted = (
                value is not None and options.threshold_enabled and abs(value) < options.threshold
            )
            if muted:
                fill = options.neutral
                detail += f"; нижче порога акценту {options.threshold:g}"
            ink = "#000000" if contrast("#000000", fill) >= contrast("#FFFFFF", fill) else "#FFFFFF"
            x, y = left + j * size, top + i * size
            parts.append(
                f'<g class="heatmap-cell" tabindex="0" role="img" aria-label="{escape(detail, quote=True)}">'
                f'<title>{escape(detail)}</title><rect x="{x}" y="{y}" width="{size - 2}" '
                f'height="{size - 2}" fill="{fill}" />'
            )
            if options.numbers or value is None:
                parts.append(
                    f'<text x="{x + size / 2}" y="{y + size / 2 + 5}" text-anchor="middle" '
                    f'font-size="{options.label_size}" fill="{ink}">{value_text}</text>'
                )
            parts.append("</g>")
    if options.frame:
        parts.append(
            f'<rect x="{left - 1}" y="{top - 1}" width="{len(names) * size}" '
            f'height="{len(names) * size}" fill="none" stroke="{options.text}" />'
        )
    # Discrete legend has all three exact anchors; no configurable truncation.
    legend_x = left + len(names) * size + 22
    for i in range(21):
        value = 1 - i / 10
        parts.append(
            f'<rect x="{legend_x}" y="{top + i * 12}" width="20" height="13" '
            f'fill="{color(value, options)}" />'
        )
    for i, value in ((0, "1"), (10, "0"), (20, "−1")):
        parts.append(label(legend_x + 30, top + i * 12 + 12, value))
    parts.append(label(20, height - 15, "Невизначено: — · Шкала кольору: −1…1"))
    parts.append("</svg>")
    return "".join(parts)
