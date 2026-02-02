import httpx
from typing import List, Dict, Any
from src.tester.models import UserInput, GameTurnResponse
from src.tester.adapter import settings

class GMClient:
    def __init__(self, base_url: str = settings.GM_URL):
        self.base_url = base_url.rstrip("/")

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
