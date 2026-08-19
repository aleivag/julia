from __future__ import annotations

import re
from typing import Any

from .models import Recipe


def default_steps(recipe: Recipe) -> list[Any]:
    selected = []
    index = 0
    while index < len(recipe.steps):
        step = recipe.steps[index]
        choice = step.attributes.get("choice", "")
        if not choice:
            selected.append(step)
            index += 1
            continue
        group = []
        while index < len(recipe.steps) and recipe.steps[index].attributes.get("choice") == choice:
            group.append(recipe.steps[index])
            index += 1
        selected.append(next((item for item in group if item.attributes.get("default") == "true"), group[0]))
    return selected


def amount(value: str) -> float | None:
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


def display_amount(value: float) -> str:
    common = ((0.25, "1/4"), (1 / 3, "1/3"), (0.5, "1/2"), (2 / 3, "2/3"), (0.75, "3/4"))
    whole = int(value)
    remainder = value - whole
    for number, label in common:
        if abs(remainder - number) < 0.02:
            return f"{whole} {label}" if whole else label
    return f"{value:.2f}".rstrip("0").rstrip(".")


def scaled_quantity(quantity: str, scale: float) -> str:
    parsed = amount(quantity)
    return display_amount(parsed * scale) if parsed is not None else quantity


def yield_amount(recipe: Recipe) -> float | None:
    match = re.match(r"\s*(\d+(?:\.\d+)?(?:\s+\d+/\d+|/\d+)?)", str(recipe.metadata.get("yield", "")))
    return amount(match.group(1)) if match else None


def dependency_scale(reference: Any, parent_scale: float, dependency: Recipe) -> float:
    requested = amount(reference.quantity)
    produced = yield_amount(dependency)
    if requested is not None and produced:
        return requested * parent_scale / produced
    return parent_scale


def walk_recipe(
    recipe: Recipe,
    scale: float,
    recipes: dict[str, Recipe],
    trail: tuple[str, ...] = (),
) -> list[tuple[Recipe, float]]:
    """Return dependencies depth-first followed by the requested recipe."""
    if recipe.id in trail:
        chain = " -> ".join((*trail, recipe.id))
        raise ValueError(f"circular recipe dependency: {chain}")
    result: list[tuple[Recipe, float]] = []
    for step in default_steps(recipe):
        for reference in step.subrecipes:
            dependency = recipes.get(reference.name)
            if not dependency:
                raise ValueError(f"{recipe.path}: unknown subrecipe '{reference.name}'")
            child_scale = dependency_scale(reference, scale, dependency)
            result.extend(walk_recipe(dependency, child_scale, recipes, (*trail, recipe.id)))
    result.append((recipe, scale))
    return result


def validate_step_products(recipe: Recipe) -> None:
    produced: dict[str, tuple[int, str]] = {}
    index = 0
    display_index = 0
    while index < len(recipe.steps):
        step = recipe.steps[index]
        choice = step.attributes.get("choice", "")
        group = [step]
        if choice:
            cursor = index + 1
            while cursor < len(recipe.steps) and recipe.steps[cursor].attributes.get("choice") == choice:
                group.append(recipe.steps[cursor])
                cursor += 1
            options = [item.attributes.get("option", "") for item in group]
            if any(not option for option in options) or len(set(options)) != len(options):
                raise ValueError(f"{recipe.path}: choice '{choice}' requires unique option names")
            defaults = [item for item in group if item.attributes.get("default") == "true"]
            if len(defaults) > 1:
                raise ValueError(f"{recipe.path}: choice '{choice}' has more than one default option")
            contracts = [{item.name.casefold() for item in branch.outputs} for branch in group]
            if any(contract != contracts[0] for contract in contracts[1:]):
                raise ValueError(f"{recipe.path}: choice '{choice}' options must produce the same outputs")
        display_index += 1
        for branch in group:
            for item in branch.inputs:
                key = item.name.casefold()
                if key not in produced:
                    line = item.source.line if item.source else branch.line
                    path = item.source.path if item.source else recipe.path
                    raise ValueError(
                        f"{path}:{line}: step input '{item.name}' has no output from an earlier step"
                    )
        for item in group[0].outputs:
            key = item.name.casefold()
            if key in produced:
                previous, _ = produced[key]
                line = item.source.line if item.source else step.line
                path = item.source.path if item.source else recipe.path
                raise ValueError(
                    f"{path}:{line}: step output '{item.name}' was already produced by step {previous}"
                )
            produced[key] = (display_index, step.title)
        index += len(group)
