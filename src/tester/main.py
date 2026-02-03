import logging
import uuid
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.tester.adapter import settings
from src.tester.agent import TesterAgent
from src.tester.models import GameTurnResponse
from src.tester.runner import IntegrationTestRunner

# Setup logging to use uvicorn's logger configuration
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="GM Tester Agent API")

# Simple in-memory storage for agents
agents: Dict[str, TesterAgent] = {}

class StartSessionRequest(BaseModel):
    session_id: Optional[str] = None
    model_name: Optional[str] = None

class StepRequest(BaseModel):
    session_id: str
    user_action: Optional[str] = None

class StepResponse(BaseModel):
    player_turn: GameTurnResponse
    npc_turn: Optional[GameTurnResponse] = None

@app.post("/session/start")
async def start_session(request: StartSessionRequest):
    session_id = request.session_id or str(uuid.uuid4())
    if session_id in agents:
        return {"session_id": session_id, "message": "Session already exists"}
    
    agent = TesterAgent(session_id, model_name=request.model_name)
    agents[session_id] = agent
    logger.info(f"Started new session: {session_id}")
    return {"session_id": session_id, "message": "Session started"}

@app.post("/session/step", response_model=StepResponse)
async def run_step(request: StepRequest):
    if request.session_id not in agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = agents[request.session_id]
    
    try:
        logger.info(f"Running step for session: {request.session_id}")
        
        # 1. Player Turn
        if request.user_action:
            logger.info(f"Using provided action: {request.user_action}")
        else:
            logger.info("Agent is thinking of an action...")
            
        player_result = await agent.run_step(user_action=request.user_action)
        logger.info(f"GM Narrative: {player_result.narrative[:100]}...")
        
        # 2. NPC Turn
        npc_result = None
        try:
            logger.info("Requesting NPC turn...")
            npc_result = await agent.run_npc_step()
            logger.info(f"NPC Narrative: {npc_result.narrative[:100]}...")
        except Exception as e:
            logger.warning(f"NPC turn skipped or failed: {str(e)}")
            
        return StepResponse(player_turn=player_result, npc_turn=npc_result)
    except Exception as e:
        logger.error(f"Error during step: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class AutoTestRequest(BaseModel):
    session_id: Optional[str] = None
    max_turns: int = 3

@app.post("/session/auto-test")
async def run_auto_test(request: AutoTestRequest):
    session_id = request.session_id or f"auto-{uuid.uuid4().hex[:8]}"
    runner = IntegrationTestRunner(session_id, max_turns=request.max_turns)
    
    # Run in background or wait for result. For testing, we wait.
    report = await runner.run_full_test()
    return report

@app.get("/sessions")
async def list_sessions():
    return {"sessions": list(agents.keys())}

@app.get("/health")
async def health_check():
    results = {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{settings.LLM_GATEWAY_URL}/health", timeout=2.0)
            results["llm_gateway"] = "ok" if resp.status_code == 200 else "error"
        except Exception:
            results["llm_gateway"] = "unreachable"
        
        try:
            resp = await client.get(f"{settings.GM_URL}/health", timeout=2.0)
            results["gm_service"] = "ok" if resp.status_code == 200 else "error"
        except Exception:
            results["gm_service"] = "unreachable"
            
    return results

@app.get("/session/history/{session_id}")
async def get_session_history(session_id: str):
    if session_id not in agents:
        raise HTTPException(status_code=404, detail="Session not found")
    agent = agents[session_id]
    return await agent.client.get_history(session_id)

