import asyncio
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from src.tester.agent import TesterAgent

# Configure logging to buffer less and capture everything
logger = logging.getLogger("gtrpgm.tester")
logger.setLevel(logging.INFO)

def setup_logging(session_id: str):
    """Sets up dual-channel logging: Console and File."""
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # 1. Stream Handler (Console)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # 2. File Handler
    log_filename = f"test_output_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(log_filename, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    logger.info(f"Logging initialized. Output file: {log_filename}")
    return log_filename


class IntegrationTestRunner:
    def __init__(self, session_id: str, max_turns: int = 20):
        self.session_id = session_id
        self.max_turns = max_turns
        self.agent = TesterAgent(session_id)
        self.results: List[Dict[str, Any]] = []
        # Setup logging immediately
        self.log_file = setup_logging(session_id)

    async def _log_state_snapshot(self, label: str = "현재 상태"):
        state = await self.agent.client.get_session_state(self.session_id)
        player = state.get("player") or {}
        session = state.get("session") or {}
        npcs = state.get("npcs") or []
        enemies = state.get("enemies") or []

        lines = []
        lines.append(f"\n--- {label} ---")
        lines.append(
            f"세션: 액트({session.get('current_act_id')}), 시퀀스({session.get('current_sequence_id')}), 턴({session.get('current_turn')})"
        )
        
        # Sequence Goal & Triggers
        seq_details = state.get("sequence") or {}
        lines.append(f"  [목표]: {seq_details.get('goal', '없음')}")
        lines.append(f"  [트리거]: {seq_details.get('exit_triggers', '없음')}")

        # Player Stats
        if player:
            p_data = player.get("player") or {}
            lines.append(
                f"플레이어: HP({p_data.get('hp')}), MP({p_data.get('mp')}), SAN({p_data.get('san')}), 골드({p_data.get('gold')})"
            )

        # NPC Stats
        if npcs:
            safe_npcs = [n for n in npcs if isinstance(n, dict)]
            npc_str = ", ".join([
                f"{n.get('scenario_entity_id') or n.get('scenario_npc_id')}(HP:{(n.get('state') or {}).get('hp')})"
                for n in safe_npcs
            ])
            lines.append(f"NPC 목록: {npc_str if npc_str else '없음'}")
        else:
            lines.append("NPC 목록: 없음")

        # Enemy Stats
        if enemies:
            safe_enemies = [e for e in enemies if isinstance(e, dict)]
            enemy_str = ", ".join([
                f"{e.get('scenario_entity_id') or e.get('scenario_enemy_id')}(HP:{(e.get('state') or {}).get('hp')})"
                for e in safe_enemies
            ])
            lines.append(f"적 목록: {enemy_str if enemy_str else '없음'}")
        else:
            lines.append("적 목록: 없음")

        # Items in Sequence
        items = seq_details.get("items", [])
        if items:
            safe_items = [i for i in items if isinstance(i, dict)]
            item_str = ", ".join([
                 f"{i.get('scenario_item_id')}({i.get('name')})" for i in safe_items
            ])
            lines.append(f"아이템 목록: {item_str if item_str else '없음'}")
        else:
            lines.append("아이템 목록: 없음")
        lines.append("-" * (len(label) + 8))
        
        logger.info("\n".join(lines))

    async def _log_scenario_manifest(self, scenario: Dict[str, Any]):
        lines = []
        lines.append(f"\n{'=' * 20} 시나리오 명세 {'=' * 20}")
        lines.append(f"제목: {scenario.get('title')}")
        lines.append(
            f"장르: {scenario.get('genre')} | 난이도: {scenario.get('difficulty')}"
        )
        lines.append(f"줄거리: {scenario.get('summary')}")

        lines.append(f"\n[액트 리스트]: {len(scenario.get('acts', []))}")
        for act in scenario.get("acts", []):
            lines.append(f"  - {act.get('id')}: {act.get('name')} ({act.get('region_name')})")

        lines.append(f"\n[NPC 리스트]: {len(scenario.get('npcs', []))}")
        for npc in scenario.get("npcs", []):
            lines.append(
                f"  - {npc.get('scenario_npc_id')}: {npc.get('name')} ({npc.get('description')[:50]}...)"
            )

        lines.append(f"\n[적 리스트]: {len(scenario.get('enemies', []))}")
        for enemy in scenario.get("enemies", []):
            lines.append(
                f"  - {enemy.get('scenario_enemy_id')}: {enemy.get('name')} ({enemy.get('description')[:50]}...)"
            )

        lines.append(f"\n[시퀀스 리스트]: {len(scenario.get('sequences', []))}")
        for seq in scenario.get("sequences", []):
            npcs = seq.get("npcs", [])
            enemies = seq.get("enemies", [])
            items = seq.get("items", [])
            lines.append(
                f"  - {seq.get('id')}: {seq.get('name')} | NPCs:{npcs} | Enemies:{enemies} | Items:{items}"
            )
        lines.append("=" * 59)
        logger.info("\n".join(lines))

    async def run_full_test(self) -> Dict[str, Any]:
        logger.info(f"--- 통합 테스트 시작 ---")
        start_time = datetime.now()

        try:
            # 0. Setup Session
            logger.info(
                "세션 설정 중 (시나리오 생성 -> 주입 -> 세션 시작)..."
            )
            concept = "A haunted tomb with a skeletal guard and a lost explorer NPC"
            self.session_id, scenario_data = await self.agent.setup_session(
                concept=concept
            )
            logger.info(f"세션 생성 완료: {self.session_id}")

            # Print Scenario Manifest
            await self._log_scenario_manifest(scenario_data)

            # Initial State Snapshot
            await self._log_state_snapshot("초기 상태")

            # [수정] 0턴: 오프닝 나레이션 (Briefing) 확보
            logger.info("\n=== 오프닝 나레이션(상황 요약) 생성 중... ===")
            
            # GM의 신규 Summary 엔드포인트를 통해 오프닝을 받아옴
            last_narrative = await self.agent.client.get_summary(self.session_id)
            
            logger.info(f"\n[GM (오프닝)]: {last_narrative}")
            
            # 오프닝을 에이전트 히스토리에 주입
            # act() 호출 시 last_narrative로 전달될 것이므로 여기서는 별도 처리 불필요

            for turn in range(1, self.max_turns + 1):
                logger.info(f"\n{'=' * 20} 제 {turn} 턴 {'=' * 20}")

                # 1. Player Turn
                action = await self.agent.act(last_narrative=last_narrative)
                logger.info(f"\n[플레이어]: {action}")

                player_result = await self.agent.run_step(user_action=action)
                logger.info(f"\n[GM (나레이션)]: {player_result.narrative}")

                # 2. NPC Turn (Automatic in GM Core)
                npc_result = player_result.npc_turn
                combined_narrative = player_result.narrative
                
                if npc_result and npc_result.narrative:
                    logger.info(f"\n[GM (NPC 턴)]: {npc_result.narrative}")
                    combined_narrative += f"\n(NPC 행동): {npc_result.narrative}"
                else:
                    logger.info("\n[GM (NPC 턴)]: NPC 행동 없음.")

                # 다음 턴을 위해 나레이션 업데이트
                last_narrative = combined_narrative

                # End of Turn State Snapshot
                await self._log_state_snapshot(f"제 {turn} 턴 종료 후 상태")

                self.results.append({
                    "turn": turn,
                    "player_action": action,
                    "gm_narrative": player_result.narrative,
                    "npc_narrative": npc_result.narrative if npc_result else None,
                    "status": "success",
                })

                logger.info(f"제 {turn} 턴 완료.")

        except Exception as e:
            logger.exception("통합 테스트 실행 중 예외 발생")
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text

            logger.error(f"제 {len(self.results) + 1} 턴에서 테스트 실패: {error_detail}")
            return {
                "session_id": self.session_id,
                "status": "failed",
                "error": error_detail,
                "completed_turns": len(self.results),
                "details": self.results,
            }

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"--- 통합 테스트 완료 (소요 시간: {duration:.2f}초) ---")
        return {
            "session_id": self.session_id,
            "status": "success",
            "duration_seconds": duration,
            "total_turns": len(self.results),
            "details": self.results,
        }



async def main():
    # Simple CLI for standalone runs
    import sys

    # Default session ID generation
    default_sid = f"auto-test-{int(datetime.now().timestamp())}"
    
    session_id = default_sid
    max_turns = 20

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    if len(sys.argv) > 2:
        max_turns = int(sys.argv[2])

    runner = IntegrationTestRunner(session_id, max_turns=max_turns)
    report = await runner.run_full_test()
    # Print final JSON to console only, for piping if needed.
    # The detailed logs are already in the file.
    # print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
