import httpx
from typing import List, Dict, Any
from tester.models import UserInput, GameTurnResponse
from tester.adapter import settings

class GMClient:
    def __init__(self, base_url: str = settings.GM_URL):
        self.base_url = base_url.rstrip("/")
        self.scenario_url = settings.SCENARIO_SERVICE_URL.rstrip("/")
        self.state_url = settings.STATE_MANAGER_URL.rstrip("/")

    async def create_scenario(self, concept: str) -> Dict[str, Any]:
        url = f"{self.scenario_url}/api/v1/generation/pure"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json={"concept": concept})
            response.raise_for_status()
            return response.json()

    async def inject_scenario(self, scenario_id: str) -> Dict[str, Any]:
        url = f"{self.scenario_url}/api/v1/manage/scenarios/{scenario_id}/inject"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url)
            response.raise_for_status()
            return response.json()

    async def start_session(self, state_manager_scenario_id: str) -> str:
        url = f"{self.state_url}/state/session/start"
        payload = {
            "scenario_id": state_manager_scenario_id,
            "user_id": 1,
            "current_act": 1,
            "current_sequence": 1,
            "location": "기본 시작 지점"
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            # Extract session_id from wrapped response
            session_data = data.get("data", {})
            return session_data.get("session_id", "")

    async def process_turn(self, session_id: str, content: str) -> GameTurnResponse:
        url = f"{self.base_url}/api/v1/game/turn"
        payload = UserInput(session_id=session_id, content=content)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload.model_dump())
            response.raise_for_status()
            data = response.json()
            npc_data = data.get("npc_turn")
            npc_turn_obj = None
            if npc_data:
                npc_turn_obj = GameTurnResponse(
                    turn_id=npc_data.get("turn_id", ""),
                    narrative=npc_data.get("narrative", ""),
                    session_id=session_id,
                    commit_id=npc_data.get("commit_id"),
                    active_entity_id=npc_data.get("active_entity_id"),
                    is_npc_turn=True,
                    raw_response=npc_data
                )
            
            return GameTurnResponse(
                turn_id=data.get("turn_id", ""),
                narrative=data.get("narrative", ""),
                session_id=session_id,
                commit_id=data.get("commit_id"),
                active_entity_id=data.get("active_entity_id"),
                is_npc_turn=False,
                npc_turn=npc_turn_obj,
                raw_response=data
            )

    async def process_npc_turn(self, session_id: str) -> GameTurnResponse:
        url = f"{self.base_url}/api/v1/game/npc-turn"
        payload = {"session_id": session_id}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return GameTurnResponse(
                turn_id=data.get("turn_id", ""),
                narrative=data.get("narrative", ""),
                session_id=session_id,
                raw_response=data
            )

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/game/history/{session_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def get_summary(self, session_id: str) -> str:
        url = f"{self.base_url}/api/v1/game/summary"
        payload = {"session_id": session_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("summary", "")

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Fetch full session state and GM-equivalent context from State Manager."""
        def _unwrap(payload: Dict[str, Any]) -> Any:
            if not isinstance(payload, dict):
                return payload
            if isinstance(payload.get("data"), (dict, list)):
                return payload.get("data")
            return payload

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1) Session baseline (GM fetch_state -> get_state)
            session_url = f"{self.state_url}/state/session/{session_id}"
            session_resp = await client.get(session_url)
            session_info = (
                (_unwrap(session_resp.json()) or {})
                if session_resp.status_code == 200
                else {}
            )

            # 2) Sequence details (GM fetch_state -> get_sequence_details)
            seq_url = f"{self.state_url}/state/session/{session_id}/sequence/details"
            seq_resp = await client.get(seq_url)
            seq_details = (
                (_unwrap(seq_resp.json()) or {})
                if seq_resp.status_code == 200
                else {}
            )

            # 3) Act details (GM fetch_state -> get_act_details)
            act_url = f"{self.state_url}/state/session/{session_id}/act/details"
            act_resp = await client.get(act_url)
            act_details = (
                (_unwrap(act_resp.json()) or {})
                if act_resp.status_code == 200
                else {}
            )

            gm_snapshot = dict(session_info)
            if isinstance(seq_details, dict):
                gm_snapshot.update(seq_details)
            gm_snapshot["act"] = act_details if isinstance(act_details, dict) else {}
            gm_snapshot.setdefault("npcs", [])
            gm_snapshot.setdefault("enemies", [])
            gm_snapshot.setdefault("entity_relations", [])
            gm_snapshot.setdefault("player_npc_relations", [])
            gm_snapshot["entities"] = [
                e_id
                for e_id in (
                    [n.get("scenario_entity_id") for n in gm_snapshot.get("npcs", [])]
                    + [e.get("scenario_entity_id") for e in gm_snapshot.get("enemies", [])]
                )
                if e_id
            ]

            # ---- Additional probes for tester-side quality assertions ----
            player_id = session_info.get("player_id")
            player_state = {}
            if player_id:
                # Player 상태
                player_url = f"{self.state_url}/state/player/{player_id}"
                player_resp = await client.get(player_url)
                player_state = (
                    (_unwrap(player_resp.json()) or {})
                    if player_resp.status_code == 200
                    else {}
                )

            # Session NPC/Enemy/Inventory
            npc_url = f"{self.state_url}/state/session/{session_id}/npcs"
            npc_resp = await client.get(npc_url)
            npcs = (
                (_unwrap(npc_resp.json()) or [])
                if npc_resp.status_code == 200
                else []
            )

            enemy_url = f"{self.state_url}/state/session/{session_id}/enemies"
            enemy_resp = await client.get(enemy_url)
            enemies = (
                (_unwrap(enemy_resp.json()) or [])
                if enemy_resp.status_code == 200
                else []
            )

            inv_url = f"{self.state_url}/state/session/{session_id}/inventory"
            inv_resp = await client.get(inv_url)
            inventory = (
                (_unwrap(inv_resp.json()) or {})
                if inv_resp.status_code == 200
                else {}
            )

            items_url = f"{self.state_url}/state/session/{session_id}/items"
            items_resp = await client.get(items_url)
            items = (
                (_unwrap(items_resp.json()) or [])
                if items_resp.status_code == 200
                else []
            )

            return {
                "session": session_info,
                "player": player_state,
                "npcs": npcs,
                "enemies": enemies,
                "sequence": seq_details,
                "act": act_details,
                "inventory": inventory,
                "items": items,
                "gm_snapshot": gm_snapshot,
            }
