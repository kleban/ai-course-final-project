BLUE = "#0B6BB0"


def mark_body(color=BLUE, waves=True, sw=13):
    s = f'stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    f = f'fill="{color}"'
    parts = [
        f'<rect x="22" y="207" width="55" height="103" rx="4" {f}/>',
        f'<rect x="103" y="150" width="54" height="160" rx="4" {f}/>',
        f'<rect x="182" y="92" width="54" height="218" rx="4" {f}/>',
        f'<path d="M264 32h44a4 4 0 0 1 4 4v258h-52V36a4 4 0 0 1 4-4z" {f}/>',
        # swoosh: thin at the bars, thick under the book, rising to the right
        f'<path d="M238 312C290 292 352 283 418 288c38 3 66 11 82 20 26-12 84-24 200-24l2 10c-104 2-160 14-202 32-26-14-60-22-100-24-62-3-120 2-164 10z" {f}/>',
        # left page
        f'<path d="M336 24c66 0 124 12 164 62v206c-40-30-96-44-164-42z" {s}/>',
        # right page with curled lower edge
        f'<path d="M500 86c36-44 88-62 140-62v112c-58 34-110 92-136 150" {s}/>',
        # back cover edge
        f'<path d="M656 64h32v214c-62-2-128 8-178 30" {s}/>',
    ]
    if waves:
        for y in (110, 150, 192):
            parts.append(f'<path d="M370 {y}c18-16 34-16 50 0s34 16 50 0" {s}/>')
    return "".join(parts)


def mark_svg(color=BLUE, waves=True):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 340">{mark_body(color, waves)}</svg>'


def book_icon_svg(color=BLUE, inner="bars"):
    """Square icon for the browser tab: the open book from the mark, with bars or waves inside."""
    sw = 18
    s = f'stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    f = f'fill="{color}"'
    parts = [
        f'<path d="M336 24c66 0 124 12 164 62v206c-40-30-96-44-164-42z" {s}/>',
        f'<path d="M500 86c36-44 88-62 140-62v112c-58 34-110 92-136 150" {s}/>',
        f'<path d="M656 64h32v214c-62-2-128 8-178 30" {s}/>',
        f'<path d="M330 300c60-14 120-12 170 12 50-22 120-30 202-26l2 18c-80-2-148 6-204 34-50-26-108-28-170-20z" {f}/>',
    ]
    if inner == "bars":
        for x, h in ((362, 50), (398, 82), (434, 118)):
            parts.append(f'<rect x="{x}" y="{226 - h}" width="24" height="{h}" rx="3" {f}/>')
    else:
        for y in (110, 150, 192):
            parts.append(f'<path d="M370 {y}c18-16 34-16 50 0s34 16 50 0" {s}/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="316 4 400 400">{"".join(parts)}</svg>'
