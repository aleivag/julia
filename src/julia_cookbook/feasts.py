from __future__ import annotations

import json
import tomllib
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from .models import Recipe


@dataclass(slots=True)
class FeastDish:
    course: str
    name: str = ""
    recipe: str = ""
    description: str = ""
    headnote: str = ""
    note: str = ""
    servings: float | None = None


@dataclass(slots=True)
class Feast:
    id: str
    title: str
    dishes: list[FeastDish]
    date: str = ""
    time: str = ""
    location: str = ""
    serves: float | None = None
    headnote: str = ""
    invitation: str = ""
    guests: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)


def load_feast(path: Path) -> Feast:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    dishes = [FeastDish(**dish) for dish in data.get("dishes", [])]
    if not data.get("title"):
        raise ValueError(f"{path}: feast requires a title")
    if not dishes:
        raise ValueError(f"{path}: feast requires at least one [[dishes]] entry")
    return Feast(
        id=path.stem.replace("_", "-").lower(),
        title=str(data["title"]),
        dishes=dishes,
        date=str(data.get("date", "")),
        time=str(data.get("time", "")),
        location=str(data.get("location", "")),
        serves=float(data["serves"]) if data.get("serves") is not None else None,
        headnote=str(data.get("headnote", "")),
        invitation=str(data.get("invitation", "")),
        guests=[str(item) for item in data.get("guests", [])],
        restrictions=[str(item) for item in data.get("restrictions", [])],
    )


def _dish_name(dish: FeastDish, recipes: dict[str, Recipe]) -> str:
    return dish.name or (recipes[dish.recipe].title if dish.recipe in recipes else dish.recipe.replace("-", " ").title())


def _dish_description(dish: FeastDish, recipes: dict[str, Recipe]) -> str:
    override = dish.headnote or dish.description
    recipe = recipes.get(dish.recipe)
    base = override or (str(recipe.metadata.get("headnote", "")) if recipe else "")
    return " ".join(part for part in (base, dish.note) if part)


def _grouped_dishes(feast: Feast) -> list[tuple[str, list[FeastDish]]]:
    groups: list[tuple[str, list[FeastDish]]] = []
    for dish in feast.dishes:
        if not groups or groups[-1][0] != dish.course:
            groups.append((dish.course, []))
        groups[-1][1].append(dish)
    return groups


def _amount(value: str) -> float | None:
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


def _display_amount(value: float) -> str:
    common = ((0.25, "1/4"), (1 / 3, "1/3"), (0.5, "1/2"), (2 / 3, "2/3"), (0.75, "3/4"))
    whole = int(value)
    remainder = value - whole
    for number, label in common:
        if abs(remainder - number) < 0.02:
            return f"{whole} {label}" if whole else label
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _recipe_scale(feast: Feast, dish: FeastDish, recipe: Recipe) -> float:
    desired = dish.servings or feast.serves
    if not desired:
        return 1.0
    match = re.match(r"\s*(\d+(?:\.\d+)?(?:\s+\d+/\d+|/\d+)?)", str(recipe.metadata.get("yield", "")))
    base = _amount(match.group(1)) if match else None
    return desired / base if base else 1.0


def _scaled_quantity(quantity: str, scale: float) -> str:
    amount = _amount(quantity)
    return _display_amount(amount * scale) if amount is not None else quantity


def _scaled_step_html(step_html: str, scale: float) -> str:
    pattern = re.compile(r'(<span class="inline-measure" data-quantity="([^"]*)"[^>]*>)(.*?)(</span>)')
    return pattern.sub(lambda match: f'{match.group(1)}{escape(_scaled_quantity(match.group(2), scale))}{match.group(4)}', step_html)


def _yield_amount(recipe: Recipe) -> float | None:
    match = re.match(r"\s*(\d+(?:\.\d+)?(?:\s+\d+/\d+|/\d+)?)", str(recipe.metadata.get("yield", "")))
    return _amount(match.group(1)) if match else None


def _dependency_scale(reference: Any, parent_scale: float, dependency: Recipe) -> float:
    requested = _amount(reference.quantity)
    produced = _yield_amount(dependency)
    if requested is not None and produced:
        return requested * parent_scale / produced
    return parent_scale


def _walk_recipe(recipe: Recipe, scale: float, recipes: dict[str, Recipe], trail: tuple[str, ...] = ()) -> list[tuple[Recipe, float]]:
    if recipe.id in trail:
        chain = " -> ".join((*trail, recipe.id))
        raise ValueError(f"circular recipe dependency: {chain}")
    result: list[tuple[Recipe, float]] = []
    for step in recipe.steps:
        for reference in step.subrecipes:
            dependency = recipes.get(reference.name)
            if not dependency:
                raise ValueError(f"{recipe.path}: unknown subrecipe '{reference.name}'")
            result.extend(_walk_recipe(dependency, _dependency_scale(reference, scale, dependency), recipes, (*trail, recipe.id)))
    result.append((recipe, scale))
    return result


def render_menu(feast: Feast, recipes: dict[str, Recipe], stylesheet: str = "../../assets/styles.css") -> str:
    courses = []
    for course, dishes in _grouped_dishes(feast):
        items = "".join(
            f'<li><h3>{escape(_dish_name(dish, recipes))}</h3>{f"<p>{escape(_dish_description(dish, recipes))}</p>" if _dish_description(dish, recipes) else ""}</li>'
            for dish in dishes
        )
        courses.append(f'<section class="menu-course"><h2>{escape(course)}</h2><ul>{items}</ul></section>')
    details = " · ".join(item for item in (feast.date, feast.time) if item)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(feast.title)} · Menu</title><link rel="stylesheet" href="{stylesheet}"></head><body class="feast-page"><main class="print-menu"><header><p class="eyebrow">Menu</p><h1>{escape(feast.title)}</h1>{f'<p class="feast-details">{escape(details)}</p>' if details else ''}{f'<p class="feast-headnote">{escape(feast.headnote)}</p>' if feast.headnote else ''}</header>{''.join(courses)}</main></body></html>'''


def render_feast(feast: Feast, recipes: dict[str, Recipe]) -> str:
    courses = []
    for course, dishes in _grouped_dishes(feast):
        items = "".join(
            f'''<li>{f'<a href="../../recipes/{escape(dish.recipe)}.html">' if dish.recipe in recipes else ''}<h3>{escape(_dish_name(dish, recipes))}</h3>{f'<p>{escape(_dish_description(dish, recipes))}</p>' if _dish_description(dish, recipes) else ''}{'</a>' if dish.recipe in recipes else ''}</li>'''
            for dish in dishes
        )
        courses.append(f'<section class="feast-course"><h2>{escape(course)}</h2><ol>{items}</ol></section>')
    details = " · ".join(item for item in (feast.date, feast.time, feast.location) if item)
    payload = json.dumps({"feast": feast.id})
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(feast.title)}</title><link rel="stylesheet" href="../../assets/styles.css"></head><body class="feast-page"><header class="site-header"><a class="brand" href="../../index.html">Cookbook</a><nav><a href="menu.html">Print menu</a><a href="shopping.html">Shopping list</a><a href="booklet.html">Kitchen booklet</a></nav></header><main class="feast-main"><header class="feast-hero"><p class="eyebrow">Feast</p><h1>{escape(feast.title)}</h1>{f'<p class="feast-details">{escape(details)}</p>' if details else ''}{f'<p class="feast-headnote">{escape(feast.headnote)}</p>' if feast.headnote else ''}</header>{''.join(courses)}</main><script type="application/json" id="julia-data">{payload}</script></body></html>'''


def render_shopping(feast: Feast, recipes: dict[str, Recipe]) -> str:
    rows = []
    for dish in feast.dishes:
        recipe = recipes.get(dish.recipe)
        if not recipe:
            continue
        for expanded, scale in _walk_recipe(recipe, _recipe_scale(feast, dish, recipe), recipes):
            for step in expanded.steps:
                for ingredient in step.ingredients:
                    rows.append((ingredient.name, _scaled_quantity(ingredient.quantity, scale), ingredient.unit, expanded.title))
    merged: dict[tuple[str, str], tuple[str, str, float, set[str]]] = {}
    loose: list[tuple[str, str, str, str]] = []
    for name, quantity, unit, recipe in rows:
        amount = _amount(quantity)
        if amount is None:
            loose.append((name, quantity or "as needed", unit, recipe))
            continue
        key = (name.lower(), unit.lower())
        if key in merged:
            display_name, display_unit, total, sources = merged[key]
            sources.add(recipe)
            merged[key] = (display_name, display_unit, total + amount, sources)
        else:
            merged[key] = (name, unit, amount, {recipe})
    merged_rows = [(name, _display_amount(total), unit, ", ".join(sorted(sources))) for name, unit, total, sources in merged.values()]
    items = "".join(f'<li><span>{escape(quantity)} {escape(unit)} {escape(name)}</span><small>{escape(recipe)}</small></li>' for name, quantity, unit, recipe in merged_rows + loose)
    missing = [dish for dish in feast.dishes if dish.recipe and dish.recipe not in recipes or not dish.recipe]
    missing_html = "" if not missing else '<section class="shopping-missing"><h2>Recipes still needed</h2><ul>' + "".join(f'<li>{escape(_dish_name(dish, recipes))}</li>' for dish in missing) + "</ul></section>"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(feast.title)} · Shopping</title><link rel="stylesheet" href="../../assets/styles.css"></head><body class="feast-page"><main class="feast-document"><a href="index.html">Back to feast</a><h1>{escape(feast.title)}</h1><h2>Shopping list</h2><ul class="feast-shopping">{items}</ul>{missing_html}</main></body></html>'''


def render_booklet(feast: Feast, recipes: dict[str, Recipe]) -> str:
    sections = []
    included: set[str] = set()
    for dish in feast.dishes:
        recipe = recipes.get(dish.recipe)
        if not recipe:
            continue
        for expanded, scale in _walk_recipe(recipe, _recipe_scale(feast, dish, recipe), recipes):
            if expanded.id in included:
                continue
            included.add(expanded.id)
            steps = "".join(f'<section class="booklet-step"><aside>{"".join(f"<div>{escape(_scaled_quantity(i.quantity, scale))} {escape(i.unit)} {escape(i.name)}</div>" for i in step.ingredients)}{"".join(f"<div class=\"booklet-dependency\">{escape(_scaled_quantity(r.quantity, scale))} {escape(r.unit)} {escape(r.name.replace("-", " ").title())}</div>" for r in step.subrecipes)}</aside><div><h3>{escape(step.title)}</h3>{_scaled_step_html(step.html, scale).replace("../recipes/", "../../recipes/")}</div></section>' for step in expanded.steps)
            sections.append(f'<article class="booklet-recipe"><h2>{escape(expanded.title)}</h2>{steps}</article>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(feast.title)} · Kitchen Booklet</title><link rel="stylesheet" href="../../assets/styles.css"></head><body class="feast-page"><main class="feast-document"><a href="index.html">Back to feast</a><h1>{escape(feast.title)}</h1><p>Kitchen booklet</p>{''.join(sections)}</main></body></html>'''


def build_feasts(root: Path, output: Path, recipes: list[Recipe]) -> list[Feast]:
    feast_dir = root / "feasts"
    if not feast_dir.is_dir():
        return []
    recipe_map = {recipe.id: recipe for recipe in recipes}
    feasts = [load_feast(path) for path in sorted(feast_dir.glob("*.toml"))]
    for feast in feasts:
        target = output / "feasts" / feast.id
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(render_feast(feast, recipe_map), encoding="utf-8")
        (target / "menu.html").write_text(render_menu(feast, recipe_map), encoding="utf-8")
        (target / "shopping.html").write_text(render_shopping(feast, recipe_map), encoding="utf-8")
        (target / "booklet.html").write_text(render_booklet(feast, recipe_map), encoding="utf-8")
    return feasts
