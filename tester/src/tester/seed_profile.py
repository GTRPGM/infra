from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tester.client import GMClient
from tester.scenarios import get_profile


async def _seed(profile_name: str) -> int:
    profile = get_profile(profile_name)
    if not profile:
        print(f"[ERROR] unknown profile: {profile_name}")
        return 2

    payload_file = (
        Path(__file__).resolve().parent
        / "scenario_payloads"
        / f"{profile.name}.inject.json"
    )
    scenario_service_id: str | None = None
    state_scenario_id: str | None = None

    if payload_file.exists():
        print(f"[INFO] debug inject/save from payload file: {payload_file}")
        inject_payload = json.loads(payload_file.read_text(encoding="utf-8"))
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(
                "http://localhost:18040/api/v1/manage/scenarios/debug/inject-save",
                json={
                    "payload": inject_payload,
                    "concept": f"debug_profile:{profile.name}",
                    "inject_to_state": True,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            state_scenario_id = body.get("state_manager_scenario_id") or (
                body.get("state_injection_result", {}) or {}
            ).get("scenario_id")
            scenario_service_id = body.get("scenario_service_id")
        if not state_scenario_id:
            print("[ERROR] direct inject did not return state scenario_id")
            return 4
        if not scenario_service_id:
            print("[ERROR] debug inject/save did not return scenario_service_id")
            return 5
    else:
        client = GMClient()
        print(f"[INFO] generating scenario for profile={profile.name}")
        scenario_data = await client.create_scenario(profile.concept)
        payload = scenario_data.get("data", scenario_data)
        scenario_service_id = scenario_data.get("scenario_id") or (
            payload.get("scenario_id") if isinstance(payload, dict) else None
        )
        if not scenario_service_id:
            print("[ERROR] scenario generation did not return scenario_id")
            return 3

        print(f"[INFO] injecting scenario_id={scenario_service_id}")
        inject_result = await client.inject_scenario(str(scenario_service_id))
        state_scenario_id = inject_result.get("scenario_id") or (
            (inject_result.get("data") or {}).get("scenario_id")
        )
        if not state_scenario_id:
            print("[ERROR] scenario inject did not return state scenario_id")
            return 4

    lock_path = (
        Path(__file__).resolve().parent
        / "scenario_profiles"
        / f"{profile.name}.lock.json"
    )
    lock_payload = {
        "profile": profile.name,
        "state_scenario_id": str(state_scenario_id),
        "scenario_service_id": str(scenario_service_id),
        "seeded_at": datetime.now(timezone.utc).isoformat(),
    }
    lock_path.write_text(
        json.dumps(lock_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] lock written: {lock_path}")
    print(f"[OK] pinned state_scenario_id={state_scenario_id}")
    return 0


def main() -> int:
    import sys

    profile_name = sys.argv[1] if len(sys.argv) > 1 else "three_sequence_combat"
    return asyncio.run(_seed(profile_name))


if __name__ == "__main__":
    raise SystemExit(main())
