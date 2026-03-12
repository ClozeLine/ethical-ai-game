import json
import os
from dataclasses import dataclass


@dataclass
class RoundDef:
    round_number: int
    timer_seconds: float
    description: str
    people_names: list[str]
    suspect_name: str
    reveals: dict[str, str]


def load_rounds(path: str | None = None) -> list[RoundDef]:
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rounds.json")
    with open(path) as f:
        data = json.load(f)
    rounds = []
    for r in data["rounds"]:
        rounds.append(RoundDef(
            round_number=r["round_number"],
            timer_seconds=r["timer_seconds"],
            description=r["description"],
            people_names=r["people"],
            suspect_name=r["suspect_name"],
            reveals=r.get("reveals", {}),
        ))
    return rounds
