from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .models import Annotation, Recipe, RecipeSyntaxError, SourceLocation, Step

STEP_RE = re.compile(r"^==\s*step(?:\s+(.+?))?\s*==$", re.IGNORECASE)
POSSIBLE_STEP_RE = re.compile(r"^==.*==$")
SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    return SLUG_RE.sub("-", value.lower()).strip("-")


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return [part.strip().strip("\"'") for part in value[1:-1].split(",") if part.strip()]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value.strip("\"'")


def _frontmatter(lines: list[str], path: str) -> tuple[dict[str, Any], int]:
    if not lines or lines[0].strip() != "---":
        raise RecipeSyntaxError(path, 1, "recipe is missing YAML frontmatter", "Start the file with --- and include a title.")
    metadata: dict[str, Any] = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            if "title" not in metadata:
                raise RecipeSyntaxError(path, 1, "frontmatter is missing 'title'")
            return metadata, index + 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise RecipeSyntaxError(path, index + 1, "invalid frontmatter entry", "Use key: value.")
        key, value = line.split(":", 1)
        metadata[key.strip()] = _scalar(value)
    raise RecipeSyntaxError(path, 1, "frontmatter is not closed", "Add --- after the metadata.")


def _balanced(text: str, start: int, opening: str, closing: str, path: str, line: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != opening:
        return "", start
    end = text.find(closing, start + 1)
    if end < 0:
        raise RecipeSyntaxError(path, line, f"unclosed '{opening}' annotation", f"Add a closing {closing}.")
    return text[start + 1 : end], end + 1


def _attributes(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for pair in raw.split(","):
        if not pair.strip():
            continue
        key, separator, value = pair.partition("=")
        result[key.strip()] = value.strip().strip("\"'") if separator else "true"
    return result


def _annotation(text: str, start: int, path: str, line: int) -> tuple[Annotation, int]:
    marker = text[start]
    kind = {"@": "ingredient", "#": "equipment", "~": "timer", "$": "parameter"}[marker]
    cursor = start + 1
    brace = text.find("{", cursor)
    if brace < 0:
        raise RecipeSyntaxError(path, line, f"{kind} marker has no quantity block", "Add {...}, even when it is empty.")
    name = text[cursor:brace].strip()
    body, cursor = _balanced(text, brace, "{", "}", path, line)
    if marker == "@" and name == "recipe":
        slug = body.strip()
        if not slug:
            raise RecipeSyntaxError(path, line, "recipe reference is missing its slug")
        if cursor >= len(text) or text[cursor] != "{":
            raise RecipeSyntaxError(path, line, "recipe reference has no quantity block", "Use @recipe{slug}{qty%unit}.")
        amount, cursor = _balanced(text, cursor, "{", "}", path, line)
        quantity, separator, unit = amount.partition("%")
        note = ""
        attrs: dict[str, str] = {}
        if cursor < len(text) and text[cursor] == "(":
            note, cursor = _balanced(text, cursor, "(", ")", path, line)
        if cursor < len(text) and text[cursor] == "[":
            raw_attrs, cursor = _balanced(text, cursor, "[", "]", path, line)
            attrs = _attributes(raw_attrs)
        return Annotation(
            kind="subrecipe", name=slug, quantity=quantity.strip(),
            unit=unit.strip() if separator else "", note=note.strip(), attributes=attrs,
            source=SourceLocation(path, line, start + 1),
        ), cursor
    if marker == "@" and not name:
        raise RecipeSyntaxError(path, line, "ingredient name is empty")
    if body.count("%") > 1:
        quantity, separator, unit = body.replace("%", " "), "", ""
    else:
        quantity, separator, unit = body.partition("%")
    note = ""
    attrs: dict[str, str] = {}
    if cursor < len(text) and text[cursor] == "(":
        note, cursor = _balanced(text, cursor, "(", ")", path, line)
    if cursor < len(text) and text[cursor] == "[":
        raw_attrs, cursor = _balanced(text, cursor, "[", "]", path, line)
        attrs = _attributes(raw_attrs)
    annotation = Annotation(
        kind=kind,
        name=name or ("timer" if marker == "~" else "temperature" if marker == "$" else "equipment"),
        quantity=quantity.strip(),
        unit=unit.strip() if separator else "",
        note=note.strip(),
        attributes=attrs,
        source=SourceLocation(path, line, start + 1),
    )
    return annotation, cursor


def _render_inline(raw: str, annotations: list[Annotation], path: str, line: int) -> str:
    output: list[str] = []
    cursor = 0
    while cursor < len(raw):
        if raw[cursor] == "[":
            label_end = raw.find("](", cursor + 1)
            target_end = raw.find(")", label_end + 2) if label_end >= 0 else -1
            if label_end >= 0 and target_end >= 0:
                label = raw[cursor + 1 : label_end]
                target = raw[label_end + 2 : target_end].strip()
                if target.startswith("recipe:"):
                    href = f'../recipes/{quote(target.removeprefix("recipe:"), safe="-")}.html'
                elif target.startswith("search:"):
                    href = f'../index.html?q={quote(target.removeprefix("search:"))}'
                else:
                    href = target
                output.append(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')
                cursor = target_end + 1
                continue
        if raw[cursor] in "@#~$":
            annotation, end = _annotation(raw, cursor, path, line)
            ingredient_index = sum(item.kind == "ingredient" for item in annotations)
            annotations.append(annotation)
            label = annotation.name
            ingredient_label = html.escape(annotation.name)
            if annotation.kind == "ingredient" and annotation.quantity:
                measure = " ".join(part for part in (annotation.quantity, annotation.unit) if part)
                fixed = ' data-scale-item="false"' if annotation.attributes.get("scale") == "false" else ""
                ingredient_label = f'<span class="inline-measure" data-quantity="{html.escape(annotation.quantity)}" data-unit="{html.escape(annotation.unit)}"{fixed}>{html.escape(measure)}</span> {html.escape(annotation.name)}'
            if annotation.kind == "timer":
                label = " ".join(part for part in (annotation.quantity, annotation.unit) if part)
            elif annotation.kind == "parameter":
                label = f"{annotation.quantity}\u00b0{annotation.unit}" if annotation.name == "temp" else " ".join((annotation.quantity, annotation.unit))
            elif annotation.kind == "subrecipe":
                title = annotation.name.replace("-", " ").title()
                measure = " ".join(part for part in (annotation.quantity, annotation.unit) if part)
                label = f'{f"<span class=\"inline-measure\" data-quantity=\"{html.escape(annotation.quantity)}\" data-unit=\"{html.escape(annotation.unit)}\">{html.escape(measure)}</span> " if measure else ""}<a href="../recipes/{quote(annotation.name, safe="-")}.html">{html.escape(title)}</a>'
            classes = f"annotation {annotation.kind}"
            attrs = [f'class="{classes}"', f'data-kind="{annotation.kind}"']
            attrs.extend((f'data-name="{html.escape(annotation.name)}"', f'data-quantity="{html.escape(annotation.quantity)}"', f'data-unit="{html.escape(annotation.unit)}"'))
            if annotation.kind == "ingredient":
                attrs.append(f'data-ingredient-index="{ingredient_index}"')
                attrs.extend(('role="checkbox"', 'aria-checked="false"', 'tabindex="0"', 'title="Mark ingredient used"'))
            rendered_label = ingredient_label if annotation.kind == "ingredient" else label if annotation.kind == "subrecipe" else html.escape(label)
            output.append(f"<span {' '.join(attrs)}>{rendered_label}</span>")
            cursor = end
            continue
        char = raw[cursor]
        if char == "*" and cursor + 1 < len(raw):
            end = raw.find("*", cursor + 1)
            if end > cursor + 1:
                output.append(f"<em>{html.escape(raw[cursor + 1:end])}</em>")
                cursor = end + 1
                continue
        output.append(html.escape(char))
        cursor += 1
    return "".join(output)


def _parse_step(raw_lines: list[tuple[int, str]], title: str, step_id: str, path: str) -> Step:
    groups: list[list[tuple[int, str]]] = [[]]
    for item in raw_lines:
        if not item[1].strip():
            if groups[-1]:
                groups.append([])
        else:
            groups[-1].append(item)
    groups = [group for group in groups if group]
    annotations: list[Annotation] = []
    paragraphs = []
    for group in groups:
        rendered = [_render_inline(text, annotations, path, number) for number, text in group]
        paragraphs.append(f"<p>{' '.join(rendered)}</p>")
    return Step(
        id=step_id,
        title=title,
        markdown="\n".join(text for _, text in raw_lines).strip(),
        html="\n".join(paragraphs),
        ingredients=[a for a in annotations if a.kind == "ingredient"],
        equipment=[a for a in annotations if a.kind == "equipment"],
        timers=[a for a in annotations if a.kind == "timer"],
        parameters=[a for a in annotations if a.kind == "parameter"],
        subrecipes=[a for a in annotations if a.kind == "subrecipe"],
        line=raw_lines[0][0] if raw_lines else 1,
    )


def parse_recipe(path: str | Path) -> Recipe:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    metadata, body_start = _frontmatter(lines, str(source))
    steps: list[Step] = []
    current_title = ""
    current_lines: list[tuple[int, str]] = []
    blurb_lines: list[tuple[int, str]] = []
    marker_seen = False

    def finish() -> None:
        nonlocal current_lines
        if current_lines:
            number = len(steps) + 1
            steps.append(_parse_step(current_lines, current_title, f"step-{number}", str(source)))
            current_lines = []

    for index in range(body_start, len(lines)):
        raw = lines[index]
        match = STEP_RE.match(raw.strip())
        if match:
            finish()
            current_title = (match.group(1) or "").strip()
            marker_seen = True
            continue
        if POSSIBLE_STEP_RE.match(raw.strip()):
            raise RecipeSyntaxError(str(source), index + 1, f'unknown step marker "{raw.strip()}"', 'Use "== step ==" or "== step name ==".')
        if not marker_seen:
            blurb_lines.append((index + 1, raw))
            continue
        current_lines.append((index + 1, raw))
    finish()
    if not steps:
        raise RecipeSyntaxError(str(source), body_start + 1, "recipe contains no steps")
    blurb_html = _parse_step(blurb_lines, "", "blurb", str(source)).html if any(text.strip() for _, text in blurb_lines) else ""
    return Recipe(slugify(source.stem), metadata, steps, str(source), blurb_html)
