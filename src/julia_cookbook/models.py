from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceLocation:
    path: str
    line: int
    column: int = 1


@dataclass(slots=True)
class Annotation:
    kind: str
    name: str
    quantity: str = ""
    unit: str = ""
    note: str = ""
    attributes: dict[str, str] = field(default_factory=dict)
    source: SourceLocation | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("source", None)
        return value


@dataclass(slots=True)
class Step:
    id: str
    title: str
    markdown: str
    html: str
    attributes: dict[str, str] = field(default_factory=dict)
    ingredients: list[Annotation] = field(default_factory=list)
    inputs: list[Annotation] = field(default_factory=list)
    outputs: list[Annotation] = field(default_factory=list)
    equipment: list[Annotation] = field(default_factory=list)
    timers: list[Annotation] = field(default_factory=list)
    parameters: list[Annotation] = field(default_factory=list)
    subrecipes: list[Annotation] = field(default_factory=list)
    line: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "html": self.html,
            "attributes": self.attributes,
            "ingredients": [item.to_dict() for item in self.ingredients],
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
            "equipment": [item.to_dict() for item in self.equipment],
            "timers": [item.to_dict() for item in self.timers],
            "parameters": [item.to_dict() for item in self.parameters],
            "subrecipes": [item.to_dict() for item in self.subrecipes],
        }


@dataclass(slots=True)
class Recipe:
    id: str
    metadata: dict[str, Any]
    steps: list[Step]
    path: str
    blurb_html: str = ""

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", self.id.replace("-", " ").title()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "id": self.id,
            "metadata": self.metadata,
            "blurbHtml": self.blurb_html,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(slots=True)
class Guide:
    id: str
    metadata: dict[str, Any]
    html: str
    path: str
    parameters: list[Annotation] = field(default_factory=list)

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", self.id.replace("-", " ").title()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "id": self.id,
            "metadata": self.metadata,
            "parameters": [item.to_dict() for item in self.parameters],
        }


class RecipeSyntaxError(ValueError):
    def __init__(self, path: str, line: int, message: str, hint: str = "") -> None:
        self.path = path
        self.line = line
        self.message = message
        self.hint = hint
        text = f"{path}:{line}: {message}"
        if hint:
            text += f"\n  Hint: {hint}"
        super().__init__(text)
