from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YieldSpec:
    count: float
    item: str
    each: float | None = None
    unit: str = ""
    approximate: bool = False
    tolerance: float | None = None

    @property
    def compound(self) -> bool:
        return self.each is not None

    @property
    def total(self) -> float | None:
        return self.count * self.each if self.each is not None else None


YIELD_RE = re.compile(
    r"^\s*(?P<count>\d+(?:\.\d+)?)\s+(?P<item>.+?)"
    r"(?:\s+\[each=(?P<approx>~)?(?P<each>\d+(?:\.\d+)?)\s*(?P<unit>[^\s\]]+)"
    r"(?:\s*(?:\+/-|±)\s*(?P<tolerance>\d+(?:\.\d+)?)\s*(?P<tolerance_unit>[^\s\]]+))?\])?\s*$"
)


def parse_yield(value: str) -> YieldSpec | None:
    match = YIELD_RE.fullmatch(value)
    if not match:
        return None
    each = float(match["each"]) if match["each"] else None
    tolerance = float(match["tolerance"]) if match["tolerance"] else None
    if match["approx"] and tolerance is not None:
        raise ValueError("yield each value cannot be both approximate and toleranced")
    if tolerance is not None and match["tolerance_unit"] != match["unit"]:
        raise ValueError("yield tolerance unit must match the each unit")
    return YieldSpec(
        count=float(match["count"]),
        item=match["item"].strip(),
        each=each,
        unit=match["unit"] or "",
        approximate=bool(match["approx"]),
        tolerance=tolerance,
    )
