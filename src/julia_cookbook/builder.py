from __future__ import annotations

import json
import shutil
import hashlib
import re
import unicodedata
from html import escape
from pathlib import Path
from typing import Any

from .dependencies import default_steps, dependency_scale, scaled_quantity, validate_step_products, walk_recipe
from .models import Annotation, Recipe
from .parser import parse_recipe
from .feasts import build_feasts
from .yields import parse_yield

PACKAGE_DIR = Path(__file__).parent


def _search_key(value: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def load_config(root: Path) -> dict[str, Any]:
    import tomllib

    path = root / ".julia"
    if not path.exists():
        return {"site": {"title": "My Cookbook", "output": "build"}, "sync": {}}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _quantity(item: Annotation) -> str:
    return " ".join(part for part in (item.quantity, item.unit) if part) or "as needed"


def _product_measure(item: Annotation, quantity: str | None = None) -> str:
    value = item.quantity if quantity is None else quantity
    if not value and not item.unit:
        return '<span class="measure"></span>'
    display = " ".join(part for part in (value, item.unit) if part)
    return f'<span class="measure" data-quantity="{escape(value)}" data-unit="{escape(item.unit)}"{_scale_mode_attr(item)}>{escape(display)}</span>'


def _scale_mode_attr(item: Annotation) -> str:
    return ' data-scale-mode="count"' if item.attributes.get("scale") == "count" else ""


def _numeric_quantity(value: str) -> float | None:
    value = value.strip()
    mixed = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", value)
    if mixed:
        return float(mixed[1]) + float(mixed[2]) / float(mixed[3])
    fraction = re.fullmatch(r"(\d+)/(\d+)", value)
    if fraction:
        return float(fraction[1]) / float(fraction[2])
    try:
        return float(value)
    except ValueError:
        return None


def _shell(title: str, content: str, site: dict[str, Any], page: str, data: dict[str, Any] | None = None) -> str:
    site_title = escape(str(site.get("title", "My Cookbook")))
    asset_version = escape(str(site.get("_asset_version", "1")))
    author = site.get("_author", {})
    author_name = str(author.get("name") or site.get("author") or "").strip()
    author_links = []
    if author.get("email"):
        email = str(author["email"]).strip()
        author_links.append(f'<a href="mailto:{escape(email)}">Email</a>')
    if author.get("website"):
        website = str(author["website"]).strip()
        author_links.append(f'<a href="{escape(website)}" rel="me">Website</a>')
    if author.get("instagram"):
        instagram = str(author["instagram"]).strip()
        instagram_url = instagram if instagram.startswith(("http://", "https://")) else f'https://www.instagram.com/{instagram.lstrip("@")}/'
        instagram_icon = '<svg class="social-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17.4" cy="6.6" r="1.1" fill="currentColor"/></svg>'
        author_links.append(f'<a href="{escape(instagram_url)}" rel="me" aria-label="Instagram">{instagram_icon}<span>Instagram</span></a>')
    author_text = f'<span class="cookbook-author">By {escape(author_name)}</span>' if author_name else ""
    author_socials = f'<span class="author-links">{"".join(author_links)}</span>' if author_links else ""
    payload = json.dumps(data or {}, separators=(",", ":"), ensure_ascii=True).replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="en" data-page="{page}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#f7f3e8">
  <meta name="description" content="{escape(str(site.get('description', 'A local-first cookbook.')))}">
  <title>{escape(title)} | {site_title}</title>
  <link rel="manifest" href="{('../' if page == 'recipe' else '')}manifest.webmanifest">
  <link rel="stylesheet" href="{('../' if page == 'recipe' else '')}assets/styles.css?v={asset_version}">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <a class="brand" href="{('../' if page == 'recipe' else '')}index.html">{site_title}</a>
    <nav aria-label="Primary">
      <a href="{('../' if page == 'recipe' else '')}index.html">Recipes</a>
      <button class="icon-button" data-action="open-data" title="Data and sync" aria-label="Data and sync">&#8635;</button>
    </nav>
  </header>
  <main id="main">{content}</main>
  <dialog id="data-dialog" class="data-dialog">
    <form method="dialog" class="dialog-head"><h2>Your cookbook data</h2><button class="icon-button" aria-label="Close">&times;</button></form>
    <p class="muted">Your cooking history stays on this device unless you export it or connect Google Drive.</p>
    <div class="button-row"><button data-action="export-data">Export</button><label class="button secondary">Import<input type="file" accept="application/json" data-action="import-data" hidden></label></div>
    <section class="sync-panel" data-sync-panel><h3>Google Drive</h3><p data-sync-status class="muted">Drive sync is not configured for this site.</p><div class="button-row"><button data-action="google-connect" hidden>Connect</button><button data-action="google-sync" hidden>Sync now</button></div></section>
  </dialog>
  <footer class="site-footer"><div>{author_text}{author_socials}</div><div>Built with <a class="julia-link" href="https://github.com/aleivag/julia">julia</a></div></footer>
  <div id="toast" role="status" aria-live="polite"></div>
  <script id="julia-data" type="application/json">{payload}</script>
  <script src="{('../' if page == 'recipe' else '')}assets/app.js?v={asset_version}" defer></script>
</body>
</html>'''


def _scaled_embedded_html(value: str, scale: float, step_key: str) -> str:
    pattern = re.compile(
        r'(<span class="inline-measure" data-quantity=")([^"]*)(" data-unit=")([^"]*)("[^>]*>)(.*?)(</span>)'
    )

    def replace(match: re.Match[str]) -> str:
        quantity = scaled_quantity(match.group(2), scale)
        display = " ".join(part for part in (quantity, match.group(4)) if part)
        return f"{match.group(1)}{escape(quantity)}{match.group(3)}{match.group(4)}{match.group(5)}{escape(display)}{match.group(7)}"

    rendered = pattern.sub(replace, value)
    rendered = re.sub(
        r'data-ingredient-index="([^"]*)"',
        lambda match: f'data-embedded-toggle="{escape(step_key)}:ingredient:{match.group(1)}"',
        rendered,
    )
    return re.sub(
        r'data-input-index="([^"]*)"',
        lambda match: f'data-embedded-toggle="{escape(step_key)}:input:{match.group(1)}"',
        rendered,
    )


def _render_input_origins(
    value: str,
    inputs: list[Annotation],
    product_sources: dict[str, tuple[int | str, str]],
) -> str:
    for index, item in enumerate(inputs):
        source_number, _ = product_sources[item.name.casefold()]
        placeholder = f'<span class="input-origin" data-input-origin="{index}"></span>'
        value = value.replace(placeholder, f'<span class="input-origin">(from step {source_number})</span>')
    return value


def _step_number(parts: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in parts)


def _embedded_anchor(parts: tuple[int, ...]) -> str:
    return f"embedded-step-{'-'.join(str(part) for part in parts)}"


def _is_dependency_step(step: Any) -> bool:
    return (
        len(step.subrecipes) == 1
        and not step.ingredients
        and not step.inputs
        and not step.equipment
    )


def _embedded_recipe_steps(
    dependency: Recipe,
    recipes: dict[str, Recipe],
    scale: float,
    number_prefix: tuple[int, ...],
    dependency_path: tuple[str, ...],
) -> str:
    rendered_steps = []
    product_sources: dict[str, tuple[str, str]] = {}
    for index, step in enumerate(dependency.steps, start=1):
        number_parts = (*number_prefix, index)
        number = _step_number(number_parts)
        step_key = "/".join((*dependency_path, step.id))
        if _is_dependency_step(step):
            rendered_steps.append(
                _dependency_step(
                    step.subrecipes[0], recipes, scale, number_parts,
                    (*dependency_path, step.id), dependency_path,
                )
            )
        else:
            ingredient_rows = []
            for ingredient_index, ingredient in enumerate(step.ingredients):
                quantity = ingredient.quantity if ingredient.attributes.get("scale") == "false" else scaled_quantity(ingredient.quantity, scale)
                display = " ".join(part for part in (quantity, ingredient.unit) if part) or "as needed"
                fixed = ' data-scale-item="false"' if ingredient.attributes.get("scale") == "false" else ""
                note = f'<small>{escape(ingredient.note)}</small>' if ingredient.note else ""
                check_key = f"{step_key}:ingredient:{ingredient_index}"
                ingredient_rows.append(
                    f'<li><label><input type="checkbox" data-check="dependency-ingredient" data-key="{escape(check_key)}" data-embedded-check="{escape(check_key)}"><span class="measure" data-quantity="{escape(quantity)}" data-unit="{escape(ingredient.unit)}"{fixed}>{escape(display)}</span><span>{escape(ingredient.name)}</span>{note}</label></li>'
                )
            input_rows = []
            for input_index, item in enumerate(step.inputs):
                quantity = scaled_quantity(item.quantity, scale)
                source_number, source_title = product_sources[item.name.casefold()]
                source_label = f"From step {source_number}" + (f", {source_title}" if source_title else "")
                check_key = f"{step_key}:input:{input_index}"
                input_rows.append(
                    f'<li><label><input type="checkbox" data-check="dependency-input" data-key="{escape(check_key)}" data-embedded-check="{escape(check_key)}">{_product_measure(item, quantity)}<span>{escape(item.name)}</span><small><a href="#{_embedded_anchor(tuple(int(part) for part in source_number.split('.')))}">{escape(source_label)}</a></small></label></li>'
                )
            output_rows = [
                f'<li>{_product_measure(item, scaled_quantity(item.quantity, scale))}<span>{escape(item.name)}</span></li>'
                for item in step.outputs
            ]
            instructions = _render_input_origins(
                _scaled_embedded_html(step.html, scale, step_key), step.inputs, product_sources
            )
            heading = f'<p class="component">{escape(step.title)}</p>' if step.title else ""
            inputs = f'<div class="step-products"><p>From earlier steps</p><ul>{"".join(input_rows)}</ul></div>' if input_rows else ""
            outputs = f'<div class="step-products outputs"><p>Produces</p><ul>{"".join(output_rows)}</ul></div>' if output_rows else ""
            nested = "".join(
                _dependency_step(item, recipes, scale, (*number_parts, child_index), (*dependency_path, step.id, f"dependency-{child_index}"), dependency_path)
                for child_index, item in enumerate(step.subrecipes, start=1)
            )
            rendered_steps.append(f'''<article class="recipe-step embedded-tree-step" id="{_embedded_anchor(number_parts)}" data-embedded-step>
              <aside>{heading}<ul class="ingredient-list">{"".join(ingredient_rows)}</ul>{inputs}{outputs}</aside>
              <section class="instructions"><div class="step-heading"><span class="step-number">{number}</span><label><input type="checkbox" data-check="dependency-step" data-key="{escape(step_key)}" data-step-completion><span>Step complete</span></label></div>{instructions}</section>
            </article>{nested}''')
        for item in step.outputs:
            product_sources[item.name.casefold()] = (number, step.title)
    return "".join(rendered_steps)


def _dependency_step(
    reference: Annotation,
    recipes: dict[str, Recipe],
    parent_scale: float,
    number_parts: tuple[int, ...],
    step_path: tuple[str, ...],
    trail: tuple[str, ...],
    root_step_id: str = "",
) -> str:
    dependency = recipes[reference.name]
    if dependency.id in trail:
        chain = " -> ".join((*trail, dependency.id))
        raise ValueError(f"circular recipe dependency: {chain}")
    scale = dependency_scale(reference, parent_scale, dependency)
    requested = scaled_quantity(reference.quantity, parent_scale)
    requested_display = " ".join(part for part in (requested, reference.unit) if part) or "as needed"
    number = _step_number(number_parts)
    step_key = "/".join((*step_path, dependency.id))
    anchor = root_step_id or _embedded_anchor(number_parts)
    check_kind = "step" if root_step_id else "dependency-step"
    data_step = f' data-step="{escape(root_step_id)}"' if root_step_id else ""
    children = _embedded_recipe_steps(
        dependency, recipes, scale, number_parts, (*step_path, dependency.id)
    )
    return f'''<details class="recipe-step dependency-step" id="{escape(anchor)}"{data_step} data-dependency-node>
      <summary class="dependency-step-summary"><aside><p class="component">Included recipe</p><span class="measure" data-quantity="{escape(requested)}" data-unit="{escape(reference.unit)}">{escape(requested_display)}</span></aside><section class="instructions"><div class="step-heading"><span class="step-number">{number}</span><label><input type="checkbox" data-check="{check_kind}" data-key="{escape(root_step_id or step_key)}" data-step-completion><span>Step complete</span></label></div><p>Prepare <span class="inline-measure" data-quantity="{escape(requested)}" data-unit="{escape(reference.unit)}">{escape(requested_display)}</span> <strong>{escape(dependency.title)}</strong>.</p></section></summary>
      <div class="dependency-children"><div class="embedded-recipe-head"><span>Included preparation</span><a href="{escape(dependency.id)}.html">Open full recipe</a></div>{children}</div>
    </details>'''


def _step_groups(recipe: Recipe) -> list[list[Any]]:
    groups = []
    index = 0
    while index < len(recipe.steps):
        step = recipe.steps[index]
        choice = step.attributes.get("choice", "")
        group = [step]
        index += 1
        while choice and index < len(recipe.steps) and recipe.steps[index].attributes.get("choice") == choice:
            group.append(recipe.steps[index])
            index += 1
        groups.append(group)
    return groups


def _choice_step(group: list[Any], display_number: int) -> str:
    choice = group[0].attributes["choice"]
    default = next((step for step in group if step.attributes.get("default") == "true"), group[0])
    controls = []
    panels = []
    for step in group:
        option = step.attributes["option"]
        selected = step is default
        controls.append(
            f'<label><input type="radio" name="choice-{escape(choice)}" value="{escape(option)}" data-choice-select{" checked" if selected else ""}><span>{escape(option.replace("-", " ").title())}</span></label>'
        )
        step_key = f"choice/{choice}/{option}/{step.id}"
        ingredients = []
        for index, item in enumerate(step.ingredients):
            check_key = f"{step_key}:ingredient:{index}"
            ingredients.append(
                f'<li><label><input type="checkbox" data-check="choice-ingredient" data-key="{escape(check_key)}" data-embedded-check="{escape(check_key)}"><span class="measure" data-quantity="{escape(item.quantity)}" data-unit="{escape(item.unit)}">{escape(_quantity(item))}</span><span>{escape(item.name)}</span>{f"<small>{escape(item.note)}</small>" if item.note else ""}</label></li>'
            )
        outputs = "".join(
            f'<li>{_product_measure(item)}<span>{escape(item.name)}</span></li>'
            for item in step.outputs
        )
        instructions = _scaled_embedded_html(step.html, 1.0, step_key)
        panels.append(f'''<section class="choice-option" data-choice-panel="{escape(option)}"{"" if selected else " hidden"}>
          <aside><ul class="ingredient-list">{"".join(ingredients)}</ul>{f'<div class="step-products outputs"><p>Produces</p><ul>{outputs}</ul></div>' if outputs else ''}</aside>
          <div class="instructions">{instructions}</div>
        </section>''')
    title = group[0].title or choice.replace("-", " ")
    return f'''<article class="recipe-step choice-step" id="step-{display_number}" data-step="choice-{escape(choice)}" data-choice-step="{escape(choice)}" data-choice-default="{escape(default.attributes['option'])}">
      <aside><p class="component">Choose one</p><div class="choice-controls">{"".join(controls)}</div></aside>
      <section class="instructions"><div class="step-heading"><span class="step-number">{display_number}</span><label><input type="checkbox" data-check="step" data-key="choice-{escape(choice)}"><span>Step complete</span></label></div><h3>{escape(title)}</h3><div class="choice-panels">{"".join(panels)}</div></section>
    </article>'''


def _recipe_page(recipe: Recipe, recipes: dict[str, Recipe], site: dict[str, Any], sync: dict[str, Any]) -> str:
    meta = recipe.metadata
    blurb_html = f'<section class="recipe-blurb">{recipe.blurb_html}</section>' if recipe.blurb_html else ""
    unit_system = str(meta.get("units", site.get("unit_system", "international"))).lower()
    if unit_system not in {"international", "imperial"}:
        unit_system = "international"
    tags = "".join(f'<a href="../index.html?tag={escape(str(tag))}">{escape(str(tag))}</a>' for tag in meta.get("tags", []))
    source = ""
    if meta.get("source"):
        label = escape(str(meta["source"]))
        source = f'<p class="source">From <a href="{escape(str(meta.get("source_url", "#")))}">{label}</a></p>'
    relationships = []
    if meta.get("variation_of"):
        target = str(meta["variation_of"])
        relationships.append(f'Variation of <a href="{escape(target)}.html">{escape(target.replace("-", " ").title())}</a>')
    related = meta.get("see_also", [])
    if isinstance(related, str):
        related = [related]
    if related:
        links = ", ".join(f'<a href="{escape(str(target))}.html">{escape(str(target).replace("-", " ").title())}</a>' for target in related)
        relationships.append(f"See also {links}")
    relationship_html = f'<p class="relationships">{" &middot; ".join(relationships)}</p>' if relationships else ""
    variations = meta.get("variations", [])
    if isinstance(variations, str):
        variations = [variations]
    variation_html = ""
    if variations:
        variation_links = "".join(
            f'<li><a href="{escape(str(target))}.html">{escape(str(target).replace("-", " ").title())}</a></li>'
            for target in variations
        )
        variation_html = f'<section class="variations"><h2>Variations</h2><ul>{variation_links}</ul></section>'
    steps = []
    yield_spec = parse_yield(str(meta.get("yield", "")))
    all_ingredients = [item for recipe_step in default_steps(recipe) for item in recipe_step.ingredients]
    scale_anchors = [item for item in all_ingredients if item.attributes.get("scale") == "true"]
    if len(scale_anchors) > 1:
        raise ValueError(f"{recipe.path}: recipe has more than one ingredient with scale=true")
    scale_controls = []
    if scale_anchors and not (yield_spec and yield_spec.compound):
        item = scale_anchors[0]
        amount = _numeric_quantity(item.quantity)
        if amount is None or amount <= 0:
            raise ValueError(f"{recipe.path}: scaling ingredient '{item.name}' needs a positive numeric quantity")
        scale_controls.append({"label": item.name.title(), "amount": amount, "unit": item.unit, "step": item.attributes.get("step", "any")})
    yield_match = re.match(r"\s*(\d+(?:\.\d+)?(?:\s+\d+/\d+|/\d+)?)\s*(.*)", str(meta.get("yield", "")))
    yield_amount = _numeric_quantity(yield_match.group(1)) if yield_match else None
    yield_label = yield_match.group(2).strip() if yield_match else ""
    duplicates_ingredient = bool(scale_controls and yield_label.lower() in {scale_controls[0]["label"].lower(), scale_controls[0]["unit"].lower()})
    if yield_amount and yield_amount > 0 and not duplicates_ingredient and not (yield_spec and yield_spec.compound):
        scale_controls.append({"label": (yield_label or "Yield").title(), "amount": yield_amount, "unit": "", "step": str(meta.get("scale_step", "1"))})
    ratio_base = next((item for item in all_ingredients if item.attributes.get("base") == "true"), None)
    if ratio_base is None:
        ratio_base = next((item for item in all_ingredients if item.unit.lower() in {"g", "kg", "oz", "lb"}), None)
    product_sources: dict[str, tuple[int, str]] = {}
    step_groups = _step_groups(recipe)
    for index, group in enumerate(step_groups):
        step = group[0]
        if step.attributes.get("choice"):
            steps.append(_choice_step(group, index + 1))
            for item in step.outputs:
                product_sources[item.name.casefold()] = (index + 1, step.title)
            continue
        ingredient_rows = []
        for i, item in enumerate(step.ingredients):
            is_ratio = item.unit.lower() == "bakers"
            item_ratio_base = next((candidate for candidate in all_ingredients if candidate.name.lower() == item.attributes.get("ratio_of", "").lower()), None) or ratio_base
            display = f"{item.quantity}%" if is_ratio else _quantity(item)
            ratio_attrs = f' data-expected-ratio="{escape(item.quantity)}" data-ratio-base="{escape(item_ratio_base.name if item_ratio_base else "")}"' if is_ratio else ""
            actual_unit = item_ratio_base.unit if is_ratio and item_ratio_base else item.unit
            measure_attrs = f'data-quantity="{escape(item.quantity)}" data-unit="{escape(item.unit)}"'
            if item.attributes.get("scale") == "false":
                measure_attrs += ' data-scale-item="false"'
            if is_ratio and item_ratio_base:
                measure_attrs += f' data-ratio="{escape(item.quantity)}" data-base-quantity="{escape(item_ratio_base.quantity)}" data-base-unit="{escape(item_ratio_base.unit)}"'
            ingredient_rows.append(f'''<li><label><input type="checkbox" data-check="ingredient" data-key="{step.id}:{i}" data-ingredient-index="{i}"><span class="measure" {measure_attrs}>{escape(display)}</span> <span>{escape(item.name)}</span>{f'<small>{escape(item.note)}</small>' if item.note else ''}</label><label class="actual-used">Used <input type="number" min="0" step="any" inputmode="decimal" data-actual="{step.id}:{i}" data-ingredient-name="{escape(item.name)}"{ratio_attrs}> <span>{escape(actual_unit)}</span></label><p class="ratio-warning" data-ratio-warning="{step.id}:{i}"></p></li>''')
        ingredients = "".join(ingredient_rows)
        input_rows = []
        for input_index, item in enumerate(step.inputs):
            source_number, source_title = product_sources[item.name.casefold()]
            source_label = f"step {source_number}"
            if source_title:
                source_label += f", {source_title}"
            input_rows.append(
                f'<li><label><input type="checkbox" data-check="input" data-key="{step.id}:{input_index}" data-input-index="{input_index}">{_product_measure(item)} <span>{escape(item.name)}</span><small><a href="#step-{source_number}">From {escape(source_label)}</a></small></label></li>'
            )
        output_rows = [
            f'<li>{_product_measure(item)} <span>{escape(item.name)}</span></li>'
            for item in step.outputs
        ]
        inputs = f'<div class="step-products"><p>From earlier steps</p><ul>{"".join(input_rows)}</ul></div>' if input_rows else ""
        outputs = f'<div class="step-products outputs"><p>Produces</p><ul>{"".join(output_rows)}</ul></div>' if output_rows else ""
        if _is_dependency_step(step):
            steps.append(
                _dependency_step(
                    step.subrecipes[0], recipes, 1.0, (index + 1,),
                    (recipe.id, step.id), (recipe.id,), root_step_id=step.id,
                )
            )
            for item in step.outputs:
                product_sources[item.name.casefold()] = (index + 1, step.title)
            continue
        nested_dependencies = "".join(
            _dependency_step(
                item, recipes, 1.0, (index + 1, child_index),
                (recipe.id, step.id, f"dependency-{child_index}"), (recipe.id,),
            )
            for child_index, item in enumerate(step.subrecipes, start=1)
        )
        equipment = "".join(f'<span class="equipment-chip">{escape(item.name)}</span>' for item in step.equipment)
        heading = f'<p class="component">{escape(step.title)}</p>' if step.title else ""
        step_html = _render_input_origins(step.html, step.inputs, product_sources)
        steps.append(f'''<article class="recipe-step" id="step-{index + 1}" data-step="{step.id}">
          <aside>{heading}<ul class="ingredient-list">{ingredients}{'<li class="muted">No external ingredients</li>' if not ingredients and not input_rows else ''}</ul>{inputs}{outputs}{equipment}</aside>
          <section class="instructions"><div class="step-heading"><span class="step-number">{index + 1}</span><label><input type="checkbox" data-check="step" data-key="{step.id}"><span>Step complete</span></label></div>{step_html}<textarea data-step-note="{step.id}" placeholder="Note from this cook" aria-label="Notes for step {index + 1}"></textarea></section>
        </article>{nested_dependencies}''')
        for item in step.outputs:
            product_sources[item.name.casefold()] = (index + 1, step.title)
    yield_text = escape(str(meta.get("yield", "Not specified")))
    anchor_controls = []
    for control in scale_controls:
        anchor_value = f'{control["amount"]:g}'
        anchor_controls.append(f'''<label class="anchor-control"><span>{escape(control["label"])}</span><span><input type="number" min="0.01" step="{escape(control["step"])}" value="{anchor_value}" data-scale-anchor data-anchor-original="{anchor_value}" data-anchor-label="{escape(control["label"])}" data-anchor-unit="{escape(control["unit"])}"> {escape(control["unit"])}</span></label>''')
    anchor_control = "".join(anchor_controls)
    compound_control = ""
    if yield_spec and yield_spec.compound:
        count = f"{yield_spec.count:g}"
        each = f"{yield_spec.each:g}"
        precision = "~" if yield_spec.approximate else ""
        tolerance = f' ± {yield_spec.tolerance:g} {escape(yield_spec.unit)}' if yield_spec.tolerance is not None else ""
        compound_control = f'''<div class="compound-yield" data-compound-yield data-original-count="{count}" data-original-each="{each}" data-each-unit="{escape(yield_spec.unit)}"><label><span>Count</span><span class="compound-field"><input type="number" min="1" step="1" value="{count}" data-yield-count><span>{escape(yield_spec.item)}</span></span></label><span class="compound-times">×</span><label><span>Each</span><span class="compound-field"><input type="number" min="0.01" step="any" value="{each}" data-yield-each><span>{escape(yield_spec.unit)}</span></span></label><div class="compound-target"><span>Target</span><strong>= <output data-yield-total>{yield_spec.total:g}</output> {escape(yield_spec.unit)}</strong></div><small>{precision}{each} {escape(yield_spec.unit)} each{tolerance}</small></div>'''
    scale_panel = f'''<details class="scale-panel"><summary><span>Scale &amp; units</span><strong data-scale-summary>Original</strong></summary><div class="scale-panel-body">{compound_control}{anchor_control}<label class="quick-scale"><span>Quick scale</span><select data-scale><option value="0.5">Half</option><option value="1" selected>Original</option><option value="1.5">1.5x</option><option value="2">Double</option><option value="3">Triple</option><option value="custom" hidden>Custom</option></select></label><fieldset class="unit-system"><legend>Temperature</legend><div role="group" aria-label="Temperature units"><button type="button" data-unit-system="international">International</button><button type="button" data-unit-system="imperial">Imperial</button></div></fieldset></div></details>'''
    content = f'''<header class="recipe-hero"><div><p class="eyebrow">Recipe</p><h1>{escape(recipe.title)}</h1><p class="recipe-yield">Makes <strong>{yield_text}</strong></p>{source}<div class="tag-list">{tags}</div></div>
      {relationship_html}<div class="recipe-actions"><button class="primary" data-action="start-cook">Make this recipe</button><a class="source-button" href="../sources/{recipe.id}.html">Show source</a></div></header>
      <div class="progress-wrap" hidden data-progress-wrap><div><span data-progress-text>0 of {len(step_groups)} steps</span><button class="text-button" data-action="finish-cook">Finish cook</button></div><progress max="{len(step_groups)}" value="0" data-progress></progress></div>
      <section class="recipe-body">{blurb_html}{scale_panel}{''.join(steps)}{variation_html}<section class="cook-history"><p class="eyebrow">Cook log</p><h2>Past experiments</h2><div data-cook-history><p class="muted">No completed cooks on this device yet.</p></div></section></section>
      <dialog id="finish-dialog" class="finish-dialog"><form method="dialog" data-finish-form><div class="dialog-head"><h2>Finish this cook</h2><button class="icon-button" value="cancel" aria-label="Close">&times;</button></div><label>Outcome<select name="outcome"><option value="worked">Worked well</option><option value="change">Would change</option><option value="failed">Did not work</option></select></label><label>Summary<textarea name="summary" placeholder="What will you remember next time?"></textarea></label><div class="button-row"><button class="primary" value="default">Save cooking event</button><button type="button" class="secondary danger" data-action="discard-cook">Discard cook</button></div></form></dialog>'''
    data = {"recipe": recipe.to_dict(), "units": unit_system, "sync": {"googleClientId": sync.get("google_client_id", "")}}
    return _shell(recipe.title, content, site, "recipe", data)


def _source_page(recipe: Recipe, site: dict[str, Any], sync: dict[str, Any]) -> str:
    source = Path(recipe.path).read_text(encoding="utf-8")
    content = f'''<header class="source-head"><div><p class="eyebrow">Recipe source</p><h1>{escape(recipe.title)}</h1><p>Read-only Julia recipe markup.</p></div><a class="button secondary" href="../recipes/{recipe.id}.html">Back to recipe</a></header><section class="source-view"><pre><code>{escape(source)}</code></pre></section>'''
    data = {"sync": {"googleClientId": sync.get("google_client_id", "")}}
    return _shell(f"Source: {recipe.title}", content, site, "recipe", data)


def _recipe_payloads(recipes: list[Recipe]) -> list[dict[str, Any]]:
    recipe_map = {recipe.id: recipe for recipe in recipes}
    payloads = []
    for recipe in recipes:
        payload = recipe.to_dict()
        shopping_ingredients = []
        for expanded, scale in walk_recipe(recipe, 1.0, recipe_map):
            for step in expanded.steps:
                for ingredient in step.ingredients:
                    item = ingredient.to_dict()
                    item["quantity"] = scaled_quantity(ingredient.quantity, scale)
                    item["sourceId"] = expanded.id
                    item["sourceTitle"] = expanded.title
                    item["component"] = step.title
                    if step.attributes.get("choice"):
                        item["choice"] = step.attributes["choice"]
                        item["option"] = step.attributes.get("option", "")
                        item["default"] = step.attributes.get("default") == "true"
                    shopping_ingredients.append(item)
        payload["shoppingIngredients"] = shopping_ingredients
        payloads.append(payload)
    return payloads


def _index_page(
    recipes: list[Recipe],
    recipe_payloads: list[dict[str, Any]],
    site: dict[str, Any],
    sync: dict[str, Any],
    feasts: list[Any] | None = None,
) -> str:
    cards = []
    for recipe in recipes:
        tags = " ".join(str(tag) for tag in recipe.metadata.get("tags", []))
        family = str(recipe.metadata.get("family", ""))
        ingredient_count = sum(len(step.ingredients) for step in recipe.steps)
        headnote = str(recipe.metadata.get("headnote") or recipe.metadata.get("description") or recipe.metadata.get("yield", "Flexible yield"))
        cards.append(f'''<article class="recipe-card" data-search="{escape(_search_key(recipe.title + ' ' + tags + ' ' + family))}" data-tags="{escape(_search_key(tags + ' ' + family))}">
          <label class="select-recipe"><input type="checkbox" data-meal-recipe="{recipe.id}" aria-label="Add {escape(recipe.title)} to shopping list"></label>
          <a href="recipes/{recipe.id}.html"><p class="eyebrow">{len(recipe.steps)} steps &middot; {ingredient_count} ingredients</p><h2>{escape(recipe.title)}</h2><p>{escape(headnote)}</p><div class="tag-list">{''.join(f'<span>{escape(str(tag))}</span>' for tag in recipe.metadata.get('tags', []))}</div></a>
        </article>''')
    feast_items = "".join(f'<li><a href="feasts/{escape(feast.id)}/index.html"><span>{escape(feast.title)}</span><small>{len(feast.dishes)} dishes</small></a></li>' for feast in (feasts or []))
    feast_section = f'<section class="feast-index"><p class="eyebrow">Feasts</p><h2>Gatherings and menus</h2><ul>{feast_items}</ul></section>' if feast_items else ""
    content = f'''<section class="library-head"><div><p class="eyebrow">The working collection</p><h1>{escape(str(site.get('title', 'My Cookbook')))}</h1><p>{escape(str(site.get('description', 'Recipes tested, adjusted, and kept.')))}</p></div><div class="library-tools"><label class="search"><span class="sr-only">Search recipes</span><input type="search" data-search placeholder="Search recipes"></label><button data-action="open-shopping">Shopping list <span data-selected-count>0</span></button></div></section>
      {feast_section}<section class="recipe-grid" aria-label="Recipes">{''.join(cards)}</section><p class="empty-state" hidden data-empty>No recipes match your search.</p>
      <dialog id="shopping-dialog" class="shopping-dialog"><form method="dialog" class="dialog-head"><h2>Shopping list</h2><button class="icon-button" aria-label="Close">&times;</button></form><div class="shopping-tabs"><button class="active" data-shopping-view="merged">Merged</button><button data-shopping-view="component">By recipe</button></div><div data-shopping-list></div><div class="button-row"><button data-action="copy-shopping">Copy list</button><button class="secondary" data-action="clear-shopping">Clear</button></div></dialog>'''
    data = {"recipes": recipe_payloads, "sync": {"googleClientId": sync.get("google_client_id", "")}}
    return _shell(str(site.get("title", "My Cookbook")), content, site, "index", data)


def build(root: str | Path = ".") -> tuple[Path, list[Recipe]]:
    root_path = Path(root).resolve()
    config = load_config(root_path)
    site = config.get("site", {})
    sync = config.get("sync", {})
    site["_author"] = config.get("author", {})
    asset_bytes = b"".join((PACKAGE_DIR / "assets" / name).read_bytes() for name in ("styles.css", "app.js", "sw.js"))
    site["_asset_version"] = hashlib.sha256(asset_bytes).hexdigest()[:12]
    recipe_dir = root_path / "recipes"
    if not recipe_dir.is_dir():
        raise FileNotFoundError(f"Recipe directory not found: {recipe_dir}")
    recipes = sorted((parse_recipe(path) for path in recipe_dir.glob("*.md")), key=lambda item: item.title.lower())
    for recipe in recipes:
        validate_step_products(recipe)
    recipe_map = {recipe.id: recipe for recipe in recipes}
    recipe_ids = {recipe.id for recipe in recipes}
    for recipe in recipes:
        for step in recipe.steps:
            for reference in step.subrecipes:
                if reference.name not in recipe_ids:
                    raise ValueError(f"{recipe.path}:{step.line}: unknown subrecipe '{reference.name}'")
    recipe_payloads = _recipe_payloads(recipes)
    output = root_path / str(site.get("output", "build"))
    (output / "recipes").mkdir(parents=True, exist_ok=True)
    (output / "sources").mkdir(parents=True, exist_ok=True)
    (output / "assets").mkdir(parents=True, exist_ok=True)
    for stale in (output / "recipes").glob("*.html"):
        stale.unlink()
    for stale in (output / "sources").glob("*.html"):
        stale.unlink()
    for recipe in recipes:
        (output / "recipes" / f"{recipe.id}.html").write_text(_recipe_page(recipe, recipe_map, site, sync), encoding="utf-8")
        (output / "sources" / f"{recipe.id}.html").write_text(_source_page(recipe, site, sync), encoding="utf-8")
    feasts = build_feasts(root_path, output, recipes)
    (output / "index.html").write_text(_index_page(recipes, recipe_payloads, site, sync, feasts), encoding="utf-8")
    for asset in ("styles.css", "app.js", "icon.svg"):
        shutil.copyfile(PACKAGE_DIR / "assets" / asset, output / "assets" / asset)
    shutil.copyfile(PACKAGE_DIR / "assets" / "sw.js", output / "sw.js")
    manifest = {"name": site.get("title", "My Cookbook"), "short_name": site.get("title", "Cookbook"), "start_url": "./index.html", "display": "standalone", "background_color": "#f7f3e8", "theme_color": "#f7f3e8", "icons": [{"src": "assets/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}]}
    (output / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "recipes.json").write_text(json.dumps(recipe_payloads, indent=2), encoding="utf-8")
    return output, recipes
