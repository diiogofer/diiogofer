"""SVG rendering for the neofetch-style profile card."""
import datetime as dt
import html


FONT      = "ConsolasFallback,Consolas,'SF Mono',Menlo,'DejaVu Sans Mono',monospace"
FONT_SIZE = 16
CHAR_W    = 9.7   # approximate character width in px at 16px font size
LINE_H    = 20


def uptime(birthday: dt.date, today: dt.date) -> str:
    """Returns elapsed time as '21 years, 2 months, 14 days'."""
    y = today.year - birthday.year
    m = today.month - birthday.month
    d = today.day - birthday.day
    if d < 0:
        m -= 1
        # borrow days from the previous month (handles variable month lengths)
        d += (dt.date(today.year, today.month, 1) - dt.date(today.year, today.month - 1 if today.month > 1 else 12, 1)).days
    if m < 0:
        y -= 1
        m += 12
    fmt = lambda n, w: f"{n} {w}{'s' if n != 1 else ''}"
    return f"{fmt(y, 'year')}, {fmt(m, 'month')}, {fmt(d, 'day')}"


def kv(key: str, value: str, width: int) -> list:
    """Returns a list of (text, css_class) spans for a key·value info line."""
    dots = width - len(key) - 5 - len(value)
    if dots < 1:
        raise SystemExit(f"Line '{key}' is {1 - dots} chars too long.")
    return [
        (". ", "cc"), (key, "key"), (":", "text"),
        (" " + "." * dots + " ", "cc"),
        (value, "value"),
    ]


def kv_loc(key: str, total: str, adds: str, dels: str, width: int) -> list:
    """Like kv(), but renders additions in green (.add) and deletions in red (.rem)."""
    inner  = f"{total} ( "
    suffix = " )"
    dots   = max(1, width - len(key) - 5 - len(inner) - len(adds) - 2 - len(dels) - len(suffix))
    return [
        (". ", "cc"), (key, "key"), (":", "text"),
        (" " + "." * dots + " ", "cc"),
        (inner, "value"), (adds, "add"), (", ", "cc"), (dels, "rem"), (suffix, "value"),
    ]


def section(title: str, width: int) -> list:
    """Returns spans for a divider line: '- Title ————————————'."""
    return [("- ", "cc"), (title, "text"), (" " + "—" * (width - len(title) - 3), "cc")]


def build_info(user: str, host: str, birthday: dt.date, width: int,
               info: list, contact: list, github_stats: list, stats: dict) -> list:
    """Assembles the full list of text spans that make up the info panel."""
    head  = f"{user}@{host}"
    lines = [[(head, "key"), (" " + "—" * (width - len(head) - 1), "cc")]]
    up    = uptime(birthday, dt.date.today())

    for item in info:
        lines.append([] if item is None else kv(item[0], item[1].replace("{uptime}", up), width))

    lines.append([])
    lines.append(section("Contact", width))
    lines += [kv(k, v, width) for k, v in contact]

    lines.append([])
    lines.append(section("GitHub Stats", width))
    for key, tmpl in github_stats:
        if "{lines_of_code}" in tmpl:
            lines.append(kv_loc(key, *stats["loc"], width) if stats["loc"] else kv(key, "run with GITHUB_TOKEN", width))
            continue
        val = (tmpl
               .replace("{total_repos}",   stats["total_repos"])
               .replace("{contributed}",   stats["contributed"])
               .replace("{total_stars}",   stats["total_stars"])
               .replace("{total_commits}", stats["total_commits"])
               .replace("{followers}",     stats["followers"]))
        lines.append(kv(key, val, width))

    return lines


def render(theme: dict, art: list, info: list, line_width: int = 60) -> str:
    """Renders the full SVG as a string given a colour theme, ASCII art, and info spans."""
    art_w    = max((len(l) for l in art), default=0)
    info_x   = 15 + round((art_w + 3) * CHAR_W)
    width    = info_x + round(line_width * CHAR_W) + 20
    rows     = max(len(art), len(info))
    height   = 30 + rows * LINE_H
    art_off  = (rows - len(art))  // 2
    info_off = (rows - len(info)) // 2

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" font-family="{FONT}" '
        f'width="{width}px" height="{height}px" font-size="{FONT_SIZE}px">',
        "<style>",
        "@font-face { src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; "
        "font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }",
        f".key{{fill:{theme['key']};}} .value{{fill:{theme['value']};}} "
        f".cc{{fill:{theme['cc']};}} .text{{fill:{theme['text']};}} "
        f".add{{fill:{theme['add']};}} .rem{{fill:{theme['rem']};}}",
        "text,tspan{white-space:pre;}",
        "</style>",
        f'<rect width="{width}px" height="{height}px" fill="{theme["bg"]}" rx="15"/>',
    ]
    for i, line in enumerate(art):
        y = 30 + (i + art_off) * LINE_H
        out.append(f'<text x="15" y="{y}" fill="{theme["text"]}">{html.escape(line)}</text>')
    for i, segs in enumerate(info):
        if not segs:
            continue
        y     = 30 + (i + info_off) * LINE_H
        spans = "".join(f'<tspan class="{c}">{html.escape(t)}</tspan>' for t, c in segs)
        out.append(f'<text x="{info_x}" y="{y}" fill="{theme["text"]}">{spans}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"
