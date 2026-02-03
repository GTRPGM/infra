import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from src.tester.agent import TesterAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gtrpgm.tester")

class IntegrationTestRunner:
    def __init__(self, session_id: str, max_turns: int = 5):
        self.session_id = session_id
        self.max_turns = max_turns
        self.agent = TesterAgent(session_id)
        self.results: List[Dict[str, Any]] = []

    async def run_full_test(self) -> Dict[str, Any]:
        logger.info(f"--- Starting Integration Test ---")
        start_time = datetime.now()
        
        try:
            # 0. Setup Session
            logger.info("Setting up session (Scenario -> Injection -> Session Start)...")
            self.session_id = await self.agent.setup_session()
            logger.info(f"Session established: {self.session_id}")

            for turn in range(1, self.max_turns + 1):
                print(f"\n{'='*20} Turn {turn} {'='*20}")
                
                # 1. Player Turn
                action = await self.agent.act()
                print(f"\n[PLAYER]: {action}")
                
                player_result = await self.agent.run_step(user_action=action)
                print(f"\n[GM (Narrative)]: {player_result.narrative}")
                
                # 2. NPC Turn
                npc_result = None
                try:
                    npc_result = await self.agent.run_npc_step()
                    if npc_result and npc_result.narrative:
                        print(f"\n[GM (NPC Turn)]: {npc_result.narrative}")
                except Exception as e:
                    logger.warning(f"NPC turn failed: {e}")

                self.results.append({
                    "turn": turn,
                    "player_action": action,
                    "gm_narrative": player_result.narrative,
                    "npc_narrative": npc_result.narrative if npc_result else None,
                    "status": "success"
                })
                
                logger.info(f"Turn {turn} completed successfully.")
                
        except Exception as e:
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text

            logger.error(f"Test failed at turn {len(self.results) + 1}: {error_detail}")
            return {
                "session_id": self.session_id,
                "status": "failed",
                "error": error_detail,
                "completed_turns": len(self.results),
                "details": self.results
            }

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"--- Integration Test Completed in {duration}s ---")
        return {
            "session_id": self.session_id,
            "status": "success",
            "duration_seconds": duration,
            "total_turns": len(self.results),
            "details": self.results
        }

async def main():
    # Simple CLI for standalone runs
    import sys
    session_id = sys.argv[1] if len(sys.argv) > 1 else f"auto-test-{int(datetime.now().timestamp())}"
    runner = IntegrationTestRunner(session_id)
    report = await runner.run_full_test()
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
