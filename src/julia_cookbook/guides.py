from __future__ import annotations

import re
from pathlib import Path

from .models import Annotation, Guide
from .parser import _frontmatter, _render_inline, slugify


TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
LIST_RE = re.compile(r"^\s*(?:(\d+)\.|([-+*]))\s+(.+)$")


def _cells(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip() for cell in value.split("|")]


def _guide_html(lines: list[tuple[int, str]], path: str) -> tuple[str, list[Annotation]]:
    output: list[str] = []
    annotations: list[Annotation] = []
    index = 0
    while index < len(lines):
        number, raw = lines[index]
        if not raw.strip():
            index += 1
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", raw.strip())
        if heading:
            level = len(heading.group(1))
            output.append(f"<h{level}>{_render_inline(heading.group(2), annotations, path, number)}</h{level}>")
            index += 1
            continue
        if index + 1 < len(lines) and "|" in raw and TABLE_DIVIDER_RE.fullmatch(lines[index + 1][1]):
            headers = _cells(raw)
            index += 2
            rows: list[list[tuple[int, str]]] = []
            while index < len(lines) and lines[index][1].strip() and "|" in lines[index][1]:
                rows.append([(lines[index][0], cell) for cell in _cells(lines[index][1])])
                index += 1
            head = "".join(f"<th>{_render_inline(cell, annotations, path, number)}</th>" for cell in headers)
            body = "".join(
                "<tr>" + "".join(f"<td>{_render_inline(cell, annotations, path, row_number)}</td>" for row_number, cell in row) + "</tr>"
                for row in rows
            )
            output.append(f'<div class="guide-table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        marker = LIST_RE.match(raw)
        if marker:
            ordered = bool(marker.group(1))
            items = []
            while index < len(lines):
                item_number, item_raw = lines[index]
                item = LIST_RE.match(item_raw)
                if not item or bool(item.group(1)) != ordered:
                    break
                items.append(_render_inline(item.group(3), annotations, path, item_number))
                index += 1
            tag = "ol" if ordered else "ul"
            output.append(f"<{tag}>{''.join(f'<li>{item}</li>' for item in items)}</{tag}>")
            continue
        paragraph = [(number, raw.strip())]
        index += 1
        while index < len(lines) and lines[index][1].strip():
            next_raw = lines[index][1]
            if re.match(r"^(#{2,4})\s+", next_raw.strip()) or LIST_RE.match(next_raw):
                break
            if index + 1 < len(lines) and "|" in next_raw and TABLE_DIVIDER_RE.fullmatch(lines[index + 1][1]):
                break
            paragraph.append((lines[index][0], next_raw.strip()))
            index += 1
        output.append("<p>" + " ".join(_render_inline(text, annotations, path, line) for line, text in paragraph) + "</p>")
    return "\n".join(output), [item for item in annotations if item.kind == "parameter"]


def parse_guide(path: str | Path) -> Guide:
    source = Path(path)
    lines = source.read_text(encoding="utf-8").splitlines()
    metadata, body_start = _frontmatter(lines, str(source))
    body = [(index + 1, lines[index]) for index in range(body_start, len(lines))]
    html, parameters = _guide_html(body, str(source))
    return Guide(slugify(source.stem), metadata, html, str(source), parameters)
