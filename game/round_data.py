import json
import os
from dataclasses import dataclass


@dataclass
class RoundDef:
    round_number: int
    timer_seconds: float
    description: str
    people_names: list[str]
    plausible_names: list[str]
    reveals: dict[str, str]


@dataclass
class RoundResult:
    round_number: int
    flagged_name: str | None
    was_plausible: bool | None
    time_remaining: float


def load_rounds(path: str | None = None) -> list[RoundDef]:
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rounds.json")
    with open(path) as f:
        data = json.load(f)
    rounds = []
    for r in data["rounds"]:
        rd = RoundDef(
            round_number=r["round_number"],
            timer_seconds=r["timer_seconds"],
            description=r["description"],
            people_names=r["people"],
            plausible_names=r["plausible_names"],
            reveals=r.get("reveals", {}),
        )
        # Validate: every person in the round must have a reveal entry
        for name in rd.people_names:
            if name not in rd.reveals:
                raise ValueError(
                    f"Round {rd.round_number}: person '{name}' "
                    f"has no reveal entry"
                )
        # Validate: plausible_names must be a non-empty subset of people_names
        if not rd.plausible_names:
            raise ValueError(
                f"Round {rd.round_number}: plausible_names is empty"
            )
        for name in rd.plausible_names:
            if name not in rd.people_names:
                raise ValueError(
                    f"Round {rd.round_number}: plausible name '{name}' "
                    f"is not in the round's people list"
                )
        rounds.append(rd)
    return rounds
