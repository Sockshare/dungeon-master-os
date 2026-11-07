"""Polyhedral Dice Roller, Probability Distribution & D20 Mechanics Engine."""

from __future__ import annotations

import math
import random
import re
import time
from typing import Literal

SUPPORTED_DICE: tuple[int, ...] = (4, 6, 8, 10, 12, 20, 100)
DiceMode = Literal["normal", "adv", "dis"]

_EXPR_RE = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def parse_dice_expr(expr: str) -> tuple[int, int, int]:
    """Parse an expression like 'd20', '2d6+3', '1d8-1' into (count, sides, modifier)."""
    m = _EXPR_RE.match(expr or "1d20")
    if not m:
        raise ValueError(f"Invalid dice expression: {expr!r}. Expected format like '1d20+4' or '2d6'.")
    count_str, sides_str, mod_str = m.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)
    modifier = int(mod_str.replace(" ", "")) if mod_str else 0
    if count < 1 or count > 20:
        raise ValueError("Dice count must be between 1 and 20.")
    if sides < 2 or sides > 1000:
        raise ValueError("Dice sides must be between 2 and 1000.")
    return count, sides, modifier


def dc_pass_probability(
    sides: int = 20,
    modifier: int = 0,
    dc: int = 12,
    mode: DiceMode = "normal",
) -> float:
    """Compute exact probability (0.0..1.0) of rolling >= dc on 1d(sides) + modifier.

    For d20 checks, Nat 20 always succeeds and Nat 1 always fails.
    """
    successes = 0
    total_outcomes = 0

    if mode == "normal":
        total_outcomes = sides
        for r in range(1, sides + 1):
            if sides == 20 and r == 20:
                successes += 1
            elif sides == 20 and r == 1:
                continue
            elif r + modifier >= dc:
                successes += 1
    else:
        total_outcomes = sides * sides
        for r1 in range(1, sides + 1):
            for r2 in range(1, sides + 1):
                chosen = max(r1, r2) if mode == "adv" else min(r1, r2)
                if sides == 20 and chosen == 20:
                    successes += 1
                elif sides == 20 and chosen == 1:
                    continue
                elif chosen + modifier >= dc:
                    successes += 1

    return round(successes / max(1, total_outcomes), 4)


def distribution_stats(
    sides: int = 20,
    count: int = 1,
    modifier: int = 0,
    mode: DiceMode = "normal",
    dc: int | None = None,
) -> dict:
    """Return theoretical mean, std_dev, min, max, crit_chance, fumble_chance, and histogram."""
    if count == 1 and mode in ("adv", "dis"):
        probs: dict[int, float] = {}
        for r1 in range(1, sides + 1):
            for r2 in range(1, sides + 1):
                val = (max(r1, r2) if mode == "adv" else min(r1, r2)) + modifier
                probs[val] = probs.get(val, 0.0) + 1.0 / (sides * sides)
        mean = sum(k * p for k, p in probs.items())
        variance = sum(((k - mean) ** 2) * p for k, p in probs.items())
        std_dev = math.sqrt(max(0.0, variance))
        crit_chance = (1.0 - ((sides - 1) / sides) ** 2) if mode == "adv" else (1.0 / (sides * sides))
        fumble_chance = (1.0 / (sides * sides)) if mode == "adv" else (1.0 - ((sides - 1) / sides) ** 2)
    else:
        single_mean = (sides + 1) / 2.0
        single_var = (sides * sides - 1) / 12.0
        mean = count * single_mean + modifier
        std_dev = math.sqrt(count * single_var)
        crit_chance = (1.0 / sides) if count == 1 else 0.0
        fumble_chance = (1.0 / sides) if count == 1 else 0.0
        probs = {}
        if count == 1 and sides <= 20:
            for r in range(1, sides + 1):
                probs[r + modifier] = round(1.0 / sides, 4)
        elif count == 2 and sides <= 12:
            for r1 in range(1, sides + 1):
                for r2 in range(1, sides + 1):
                    v = r1 + r2 + modifier
                    probs[v] = round(probs.get(v, 0.0) + 1.0 / (sides * sides), 4)

    # Compact histogram buckets (max 20 buckets)
    histogram = [
        {"value": k, "probability": round(v, 4)}
        for k, v in sorted(probs.items())
    ][:20]

    res = {
        "sides": sides,
        "count": count,
        "modifier": modifier,
        "mode": mode,
        "min_total": count + modifier,
        "max_total": count * sides + modifier,
        "expected_value": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "crit_chance_pct": round(crit_chance * 100, 2) if sides == 20 and count == 1 else 0.0,
        "fumble_chance_pct": round(fumble_chance * 100, 2) if sides == 20 and count == 1 else 0.0,
        "histogram": histogram,
    }
    if dc is not None and count == 1:
        res["dc"] = dc
        res["pass_probability_pct"] = round(dc_pass_probability(sides, modifier, dc, mode) * 100, 1)
    return res


def roll_polyhedral(
    sides: int = 20,
    count: int = 1,
    modifier: int = 0,
    mode: DiceMode = "normal",
    dc: int | None = None,
    label: str = "",
    rng: random.Random | None = None,
    forced_natural: int | None = None,
) -> dict:
    """Roll any polyhedral die (d4, d6, d8, d10, d12, d20, d100) with optional Adv/Dis and DC evaluation."""
    r = rng or random
    count = max(1, min(20, int(count)))
    sides = max(2, min(1000, int(sides)))
    modifier = int(modifier)

    if forced_natural is not None and count == 1:
        nat = max(1, min(sides, int(forced_natural)))
        rolls = [nat]
        discarded: list[int] = []
        natural_total = nat
    elif count == 1 and mode in ("adv", "dis"):
        r1 = r.randint(1, sides)
        r2 = r.randint(1, sides)
        if mode == "adv":
            chosen, dropped = (r1, r2) if r1 >= r2 else (r2, r1)
        else:
            chosen, dropped = (r1, r2) if r1 <= r2 else (r2, r1)
        rolls = [chosen]
        discarded = [dropped]
        natural_total = chosen
    else:
        rolls = [r.randint(1, sides) for _ in range(count)]
        discarded = []
        natural_total = sum(rolls)

    total = natural_total + modifier
    is_nat20 = bool(sides == 20 and count == 1 and natural_total == 20)
    is_nat1 = bool(sides == 20 and count == 1 and natural_total == 1)

    success: bool | None = None
    outcome_tier = "neutral"
    if dc is not None:
        if is_nat20:
            success = True
            outcome_tier = "critical_success"
        elif is_nat1:
            success = False
            outcome_tier = "critical_fumble"
        elif total >= dc:
            success = True
            outcome_tier = "success"
        else:
            success = False
            outcome_tier = "failure"
    else:
        if is_nat20:
            outcome_tier = "critical_success"
        elif is_nat1:
            outcome_tier = "critical_fumble"

    mod_str = f"{modifier:+d}" if modifier != 0 else ""
    mode_tag = " (ADV)" if mode == "adv" else (" (DIS)" if mode == "dis" else "")
    formula = f"{count}d{sides}{mod_str}{mode_tag}"

    return {
        "id": f"roll_{int(time.time() * 1000)}_{r.randint(100, 999)}",
        "timestamp": time.strftime("%H:%M:%S"),
        "label": label or f"Roll {formula}",
        "formula": formula,
        "sides": sides,
        "count": count,
        "modifier": modifier,
        "mode": mode,
        "rolls": rolls,
        "discarded": discarded,
        "natural": natural_total,
        "total": total,
        "dc": dc,
        "success": success,
        "is_nat20": is_nat20,
        "is_nat1": is_nat1,
        "outcome_tier": outcome_tier,
        "stats": distribution_stats(sides=sides, count=count, modifier=modifier, mode=mode, dc=dc),
    }
