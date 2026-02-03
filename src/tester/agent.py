from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from src.tester.adapter import LLMGatewayChatModel
from src.tester.client import GMClient
from src.tester.models import GameTurnResponse
import os

class TesterAgent:
    def __init__(self, session_id: str, model_name: Optional[str] = None):
        self.session_id = session_id
        self.llm = LLMGatewayChatModel(model_name=model_name) if model_name else LLMGatewayChatModel()
        self.client = GMClient()
        self.history: List[BaseMessage] = []
        self._initialize_persona()

    def _initialize_persona(self):
        # gm/docs 내의 모든 .md 파일을 읽어서 컨텍스트로 활용
        docs_context = []
        docs_dir = "gm/docs"
        if os.path.exists(docs_dir):
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    if file.endswith(".md"):
                        try:
                            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                                docs_context.append(f"--- Document: {file} ---\n{f.read()}")
                        except Exception:
                            pass

        all_docs = "\n\n".join(docs_context)
        
        system_prompt = f"""You are an expert TRPG tester agent. 
Your mission is to test the GM Core system by playing the game as a player.
You should try various actions to see how the system handles rules and scenarios.

Key Principles from System Documentation:
- Scenario constraints have higher priority than Rules.
- Every state change happens via a single commit before the narrative is generated.
- The game follows a turn-based structure (Player turn followed by NPC turn).

System Documentation Context:
{all_docs}

Instructions:
1. Observe the GM's narrative carefully.
2. Formulate a creative and logical action as a player.
3. Your output should be ONLY the natural language action text.
"""
        self.history.append(SystemMessage(content=system_prompt))

    async def setup_session(self, concept: str = "A dark fantasy dungeon exploration") -> str:
        # 1. Create Scenario (Scenario Service)
        scenario_data = await self.client.create_scenario(concept)
        scenario_id = scenario_data.get("scenario_id")
        if not scenario_id:
            raise ValueError(f"Failed to create scenario: {scenario_data}")
        
        # 2. Inject Scenario into State Manager via Scenario Service
        # This returns the ID used by State Manager
        inject_result = await self.client.inject_scenario(scenario_id)
        
        # Injection might return sm_id in different paths depending on service version
        state_manager_scenario_id = inject_result.get("scenario_id") or \
                                   inject_result.get("data", {}).get("scenario_id")
        
        if not state_manager_scenario_id:
            # Fallback to scenario_id if inject doesn't return a new one
            state_manager_scenario_id = scenario_id

        # 3. Start Session (State Manager)
        session_id = await self.client.start_session(state_manager_scenario_id)
        if not session_id:
            raise ValueError("Failed to obtain session_id from state-manager")

        self.session_id = session_id
        return session_id

    async def act(self, last_narrative: Optional[str] = None) -> str:
        if last_narrative:
            self.history.append(HumanMessage(content=f"GM Narrative: {last_narrative}\n\nWhat is your next action?"))
        else:
            self.history.append(HumanMessage(content="The game has started. What is your first action?"))

        response = await self.llm.ainvoke(self.history)
        action_text = str(response.content)
        self.history.append(response)
        return action_text

    async def run_step(self, user_action: Optional[str] = None) -> GameTurnResponse:
        action = user_action if user_action else await self.act()
        
        # Player Turn
        result = await self.client.process_turn(self.session_id, action)
        
        # Keep track of history in agent if needed
        # For now, we just return the result
        return result

    async def run_npc_step(self) -> GameTurnResponse:
        return await self.client.process_npc_turn(self.session_id)
