from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScenarioProfile:
    name: str
    concept: str
    min_sequences: int
    scripted_actions: tuple[str, ...]
    load_title_hint: str | None = None
    load_title_exact: str | None = None
    pinned_state_scenario_id: str | None = None
    pinned_scenario_service_id: str | None = None
    starter_loadout_rule_ids: tuple[int, ...] = ()


_PROFILE_DIR = Path(__file__).resolve().parent / "scenario_profiles"


def _load_profile(filename: str) -> ScenarioProfile:
    payload = json.loads((_PROFILE_DIR / filename).read_text(encoding="utf-8"))
    lock_path = _PROFILE_DIR / f"{Path(filename).stem}.lock.json"
    lock_payload: dict[str, object] = {}
    if lock_path.exists():
        lock_payload = json.loads(lock_path.read_text(encoding="utf-8"))
    return ScenarioProfile(
        name=str(payload["name"]),
        concept=str(payload["concept"]),
        min_sequences=int(payload["min_sequences"]),
        scripted_actions=tuple(str(x) for x in payload["scripted_actions"]),
        load_title_hint=payload.get("load_title_hint"),
        load_title_exact=payload.get("load_title_exact"),
        pinned_state_scenario_id=(
            str(lock_payload.get("state_scenario_id"))
            if lock_payload.get("state_scenario_id")
            else payload.get("pinned_state_scenario_id")
        ),
        pinned_scenario_service_id=(
            str(lock_payload.get("scenario_service_id"))
            if lock_payload.get("scenario_service_id")
            else None
        ),
        starter_loadout_rule_ids=tuple(
            int(x) for x in payload.get("starter_loadout_rule_ids", [])
        ),
    )


THREE_SEQUENCE_COMBAT = _load_profile("three_sequence_combat.json")
FIVE_SEQUENCE_EVALUATION = _load_profile("five_sequence_evaluation.json")
SIX_SEQUENCE_THREE_ACT_EVAL = _load_profile("six_sequence_three_act_eval.json")
MINIMAL_RELATION_TEST = _load_profile("minimal_relation_test.json")


def get_profile(name: str | None) -> ScenarioProfile | None:
    if not name:
        return None
    key = str(name).strip().lower()
    if key == THREE_SEQUENCE_COMBAT.name:
        return THREE_SEQUENCE_COMBAT
    if key == FIVE_SEQUENCE_EVALUATION.name:
        return FIVE_SEQUENCE_EVALUATION
    if key == SIX_SEQUENCE_THREE_ACT_EVAL.name:
        return SIX_SEQUENCE_THREE_ACT_EVAL
    if key == MINIMAL_RELATION_TEST.name:
        return MINIMAL_RELATION_TEST
    return None
