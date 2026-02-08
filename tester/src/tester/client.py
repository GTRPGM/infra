from typing import Any, Dict, List, Optional

import httpx

from tester.adapter import settings
from tester.models import GameTurnResponse, UserInput


class GMClient:
    def __init__(self, base_url: str = settings.BE_ROUTER_URL):
        self.base_url = base_url.rstrip("/")
        self._access_token: Optional[str] = None
        self._username = settings.TESTER_USERNAME
        self._password = settings.TESTER_PASSWORD
        self._email = settings.TESTER_EMAIL

    @staticmethod
    def _unwrap(payload: Dict[str, Any]) -> Any:
        if not isinstance(payload, dict):
            return payload
        if "data" in payload:
            return payload.get("data")
        return payload

    def _headers(self) -> Dict[str, str]:
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def ensure_authenticated(self) -> None:
        if self._access_token:
            return

        login_url = f"{self.base_url}/auth/login"
        create_user_url = f"{self.base_url}/user/create"
        login_payload = {"username": self._username, "password": self._password}

        async with httpx.AsyncClient(timeout=15.0) as client:
            login_resp = await client.post(login_url, json=login_payload)
            if login_resp.status_code != 200:
                # Ensure tester user exists, then retry login.
                create_payload = {
                    "username": self._username,
                    "password": self._password,
                    "email": self._email,
                }
                _ = await client.post(create_user_url, json=create_payload)
                login_resp = await client.post(login_url, json=login_payload)

            login_resp.raise_for_status()
            login_body = self._unwrap(login_resp.json()) or {}
            token = login_body.get("access_token")
            if not token:
                raise ValueError("Failed to acquire access token from BE-router login")
            self._access_token = token

    async def create_scenario(self, concept: str) -> Dict[str, Any]:
        await self.ensure_authenticated()
        url = f"{self.base_url}/scenario/generation/pure"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                json={"concept": concept},
            )
            response.raise_for_status()
            return response.json()

    async def get_scenarios(self) -> List[Dict[str, Any]]:
        await self.ensure_authenticated()
        url = f"{self.base_url}/state/scenarios"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            data = self._unwrap(response.json()) or []
            return data if isinstance(data, list) else []

    async def get_scenario(self, scenario_id: str) -> Dict[str, Any]:
        await self.ensure_authenticated()
        url = f"{self.base_url}/state/scenario/{scenario_id}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            data = self._unwrap(response.json()) or {}
            return data if isinstance(data, dict) else {}

    async def inject_scenario(self, scenario_id: str) -> Dict[str, Any]:
        await self.ensure_authenticated()
        url = f"{self.base_url}/scenario/manage/scenarios/{scenario_id}/inject"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def start_session(self, state_manager_scenario_id: str) -> str:
        await self.ensure_authenticated()
        url = f"{self.base_url}/state/session/start"
        payload = {
            "scenario_id": state_manager_scenario_id,
            "current_act": 1,
            "current_sequence": 1,
            "location": "기본 시작 지점",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            session_data = self._unwrap(response.json()) or {}
            return session_data.get("session_id", "")

    async def grant_starter_items(
        self, session_id: str, rule_ids: list[int] | tuple[int, ...]
    ) -> list[Dict[str, Any]]:
        await self.ensure_authenticated()
        if not rule_ids:
            return []

        async with httpx.AsyncClient(timeout=15.0) as client:
            session_url = f"{self.base_url}/state/session/{session_id}"
            session_resp = await client.get(session_url, headers=self._headers())
            session_resp.raise_for_status()
            session_data = self._unwrap(session_resp.json()) or {}
            player_id = session_data.get("player_id")
            if not player_id:
                raise ValueError(f"player_id not found for session_id={session_id}")

            items_url = f"{self.base_url}/state/session/{session_id}/items"
            items_resp = await client.get(items_url, headers=self._headers())
            items_resp.raise_for_status()
            items_data = self._unwrap(items_resp.json()) or []
            if not isinstance(items_data, list):
                items_data = []

            rule_to_item_id: dict[int, str] = {}
            for item in items_data:
                if not isinstance(item, dict):
                    continue
                rid = item.get("rule_id")
                item_id = item.get("item_id")
                if rid is None or not item_id:
                    continue
                try:
                    rid_int = int(rid)
                except (TypeError, ValueError):
                    continue
                rule_to_item_id.setdefault(rid_int, str(item_id))

            earn_url = f"{self.base_url}/state/player/item/earn"
            results: list[Dict[str, Any]] = []
            for rid in rule_ids:
                item_id = rule_to_item_id.get(int(rid))
                if not item_id:
                    results.append(
                        {
                            "rule_id": int(rid),
                            "skipped": True,
                            "reason": "item_id not found in session items",
                        }
                    )
                    continue
                payload = {
                    "session_id": str(session_id),
                    "player_id": str(player_id),
                    "item_id": str(item_id),
                    "rule_id": int(rid),
                    "quantity": 1,
                }
                resp = await client.post(
                    earn_url,
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                results.append(self._unwrap(resp.json()) or {})

            return results

    async def process_turn(self, session_id: str, content: str) -> GameTurnResponse:
        await self.ensure_authenticated()
        url = f"{self.base_url}/gm/turn"
        payload = UserInput(session_id=session_id, content=content)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url, headers=self._headers(), json=payload.model_dump()
            )
            response.raise_for_status()
            data = self._unwrap(response.json()) or {}
            npc_data = data.get("npc_turn")
            npc_turn_obj = None
            if npc_data:
                npc_turn_obj = GameTurnResponse(
                    turn_id=npc_data.get("turn_id", ""),
                    narrative=npc_data.get("narrative", ""),
                    session_id=session_id,
                    commit_id=npc_data.get("commit_id"),
                    active_entity_id=npc_data.get("active_entity_id"),
                    active_entity_name=npc_data.get("active_entity_name"),
                    output_type=npc_data.get("output_type"),
                    is_npc_turn=True,
                    raw_response=npc_data,
                )

            return GameTurnResponse(
                turn_id=data.get("turn_id", ""),
                narrative=data.get("narrative", ""),
                session_id=session_id,
                commit_id=data.get("commit_id"),
                active_entity_id=data.get("active_entity_id"),
                active_entity_name=data.get("active_entity_name"),
                output_type=data.get("output_type"),
                is_npc_turn=False,
                npc_turn=npc_turn_obj,
                raw_response=data,
            )

    async def process_npc_turn(self, session_id: str) -> GameTurnResponse:
        await self.ensure_authenticated()
        url = f"{self.base_url}/gm/npc-turn"
        payload = {"session_id": session_id}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = self._unwrap(response.json()) or {}
            return GameTurnResponse(
                turn_id=data.get("turn_id", ""),
                narrative=data.get("narrative", ""),
                session_id=session_id,
                commit_id=data.get("commit_id"),
                active_entity_id=data.get("active_entity_id"),
                active_entity_name=data.get("active_entity_name"),
                output_type=data.get("output_type"),
                is_npc_turn=True,
                raw_response=data,
            )

    async def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        await self.ensure_authenticated()
        url = f"{self.base_url}/gm/history/{session_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            data = self._unwrap(response.json()) or []
            return data if isinstance(data, list) else []

    async def get_summary(self, session_id: str) -> str:
        await self.ensure_authenticated()
        url = f"{self.base_url}/gm/summary"
        payload = {"session_id": session_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = self._unwrap(response.json()) or {}
            return data.get("summary", "")

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Fetch full session state and GM-equivalent context from State Manager."""
        await self.ensure_authenticated()

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1) Session baseline (GM fetch_state -> get_state)
            session_url = f"{self.base_url}/state/session/{session_id}"
            session_resp = await client.get(session_url, headers=self._headers())
            session_info = (
                (self._unwrap(session_resp.json()) or {})
                if session_resp.status_code == 200
                else {}
            )

            # 2) Sequence details (GM fetch_state -> get_sequence_details)
            seq_url = f"{self.base_url}/state/session/{session_id}/sequence/details"
            seq_resp = await client.get(seq_url, headers=self._headers())
            seq_details = (
                (self._unwrap(seq_resp.json()) or {})
                if seq_resp.status_code == 200
                else {}
            )

            # 3) Act details (GM fetch_state -> get_act_details)
            act_url = f"{self.base_url}/state/session/{session_id}/act/details"
            act_resp = await client.get(act_url, headers=self._headers())
            act_details = (
                (self._unwrap(act_resp.json()) or {})
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
                    + [
                        e.get("scenario_entity_id")
                        for e in gm_snapshot.get("enemies", [])
                    ]
                )
                if e_id
            ]

            # ---- Additional probes for tester-side quality assertions ----
            player_id = session_info.get("player_id")
            player_state = {}
            if player_id:
                # Player 상태
                player_url = f"{self.base_url}/state/player/{player_id}"
                player_resp = await client.get(player_url, headers=self._headers())
                player_state = (
                    (self._unwrap(player_resp.json()) or {})
                    if player_resp.status_code == 200
                    else {}
                )

            # Session NPC/Enemy/Inventory
            npc_url = f"{self.base_url}/state/session/{session_id}/npcs"
            npc_resp = await client.get(npc_url, headers=self._headers())
            npcs = (
                (self._unwrap(npc_resp.json()) or [])
                if npc_resp.status_code == 200
                else []
            )

            enemy_url = f"{self.base_url}/state/session/{session_id}/enemies"
            enemy_resp = await client.get(enemy_url, headers=self._headers())
            enemies = (
                (self._unwrap(enemy_resp.json()) or [])
                if enemy_resp.status_code == 200
                else []
            )

            inv_url = f"{self.base_url}/state/session/{session_id}/inventory"
            inv_resp = await client.get(inv_url, headers=self._headers())
            inventory = (
                (self._unwrap(inv_resp.json()) or {})
                if inv_resp.status_code == 200
                else {}
            )

            items_url = f"{self.base_url}/state/session/{session_id}/items"
            items_resp = await client.get(items_url, headers=self._headers())
            items = (
                (self._unwrap(items_resp.json()) or [])
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
