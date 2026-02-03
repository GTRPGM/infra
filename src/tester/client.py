import httpx
from typing import List, Dict, Any
from src.tester.models import UserInput, GameTurnResponse
from src.tester.adapter import settings

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
            return GameTurnResponse(
                turn_id=data.get("turn_id", ""),
                narrative=data.get("narrative", ""),
                session_id=session_id,
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
