import asyncio
import logging
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from tester.agent import TesterAgent

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
        self.prev_state: Dict[str, Any] | None = None
        self.scenario_seq_ids: set[str] = set()
        self.scenario_act_ids: set[str] = set()
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

        # Inventory / Owned Items
        inventory = state.get("inventory") or {}
        inv_items = inventory.get("items", []) if isinstance(inventory, dict) else []
        if inv_items:
            safe_inv_items = [i for i in inv_items if isinstance(i, dict)]
            inv_item_str = ", ".join(
                [f"{i.get('scenario_item_id')}({i.get('name')})" for i in safe_inv_items]
            )
            lines.append(f"인벤토리: {inv_item_str if inv_item_str else '없음'}")
        else:
            lines.append("인벤토리: 없음")
        lines.append("-" * (len(label) + 8))
        
        logger.info("\n".join(lines))

    def _extract_relation_entity_ids(self, state: Dict[str, Any]) -> set[str]:
        seq = state.get("sequence") or {}
        relation_ids: set[str] = set()
        for rel in seq.get("entity_relations", []) or []:
            if isinstance(rel, dict):
                if rel.get("from_id"):
                    relation_ids.add(str(rel["from_id"]))
                if rel.get("to_id"):
                    relation_ids.add(str(rel["to_id"]))
        for rel in seq.get("player_npc_relations", []) or []:
            if isinstance(rel, dict) and rel.get("npc_id"):
                relation_ids.add(str(rel["npc_id"]))
        return relation_ids

    def _inventory_item_ids(self, state: Dict[str, Any]) -> set[str]:
        inventory = state.get("inventory") or {}
        if not isinstance(inventory, dict):
            return set()
        items = inventory.get("items", []) or []
        return {
            str(i.get("scenario_item_id"))
            for i in items
            if isinstance(i, dict) and i.get("scenario_item_id")
        }

    def _narrative_implies_item_acquire(self, narrative: str) -> bool:
        text = (narrative or "").strip()
        if not text:
            return False

        verb = r"(획득|주웠|얻었|입수|손에 넣|줍는다|주워)"
        item_noun = r"(아이템|열쇠|검|무기|방패|물약|포션|보석|유물|주화|금화|장비|문서|지도)"

        patterns = [
            rf"{item_noun}.{{0,20}}{verb}",
            rf"{verb}.{{0,20}}{item_noun}",
            r"인벤토리.{0,20}(추가|획득|입수)",
        ]
        return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", "", str(text or "")).lower()

    def _keyword_tokens(self, text: str) -> list[str]:
        raw_tokens = re.findall(r"[가-힣a-zA-Z0-9]+", str(text or "").lower())
        stopwords = {"그리고", "또는", "으로", "에서", "한다", "했다", "하기", "the", "and"}
        return [t for t in raw_tokens if len(t) >= 2 and t not in stopwords]

    def _is_trigger_satisfied(
        self,
        action: str,
        triggers: list[str],
    ) -> bool:
        if not triggers:
            return False

        combined = action
        normalized = self._normalize_text(combined)

        # 1) Fast-path: normalized phrase inclusion.
        for trig in triggers:
            trig_norm = self._normalize_text(trig)
            if trig_norm and trig_norm in normalized:
                return True

        # 2) Semantic-ish fallback: keyword overlap ratio.
        combined_tokens = set(self._keyword_tokens(combined))
        if not combined_tokens:
            return False

        for trig in triggers:
            trig_tokens = self._keyword_tokens(trig)
            if len(trig_tokens) < 2:
                continue
            matched = sum(1 for tk in trig_tokens if tk in combined_tokens)
            if matched / max(len(trig_tokens), 1) >= 0.6:
                return True
        return False

    def _assert_state_consistency(
        self,
        turn: int,
        state: Dict[str, Any],
        combined_narrative: str,
        player_action: str = "",
    ) -> None:
        session = state.get("session") or {}
        seq = state.get("sequence") or {}
        act = state.get("act") or {}

        scenario_id = session.get("scenario_id")
        if not scenario_id:
            raise AssertionError(f"[턴 {turn}] session.scenario_id 누락")

        current_act_id = session.get("current_act_id")
        current_seq_id = session.get("current_sequence_id")
        if not current_act_id or not current_seq_id:
            raise AssertionError(f"[턴 {turn}] current_act_id/current_sequence_id 누락")

        # GM context parity: sequence details must align with current session pointer.
        seq_id = seq.get("sequence_id")
        if seq_id and seq_id != current_seq_id:
            raise AssertionError(
                f"[턴 {turn}] 시퀀스 불일치 session={current_seq_id}, sequence.details={seq_id}"
            )

        # If act details are available, must align with session act.
        act_id = act.get("act_id")
        if act_id and act_id != current_act_id:
            raise AssertionError(
                f"[턴 {turn}] 액트 불일치 session={current_act_id}, act.details={act_id}"
            )

        # Canonical id format check
        if not str(current_act_id).startswith("act-"):
            raise AssertionError(f"[턴 {turn}] 비정규 act_id: {current_act_id}")
        if not str(current_seq_id).startswith("seq-"):
            raise AssertionError(f"[턴 {turn}] 비정규 seq_id: {current_seq_id}")

        # Relation integrity: referenced ids must be known in current scope.
        known_ids = {"player"}
        for npc in (state.get("npcs") or []):
            if isinstance(npc, dict):
                for k in ("scenario_entity_id", "scenario_npc_id", "npc_id"):
                    if npc.get(k):
                        known_ids.add(str(npc.get(k)))
        for enemy in (state.get("enemies") or []):
            if isinstance(enemy, dict):
                for k in ("scenario_entity_id", "scenario_enemy_id", "enemy_id"):
                    if enemy.get(k):
                        known_ids.add(str(enemy.get(k)))

        rel_ids = self._extract_relation_entity_ids(state)
        for rel_id in rel_ids:
            if rel_id in known_ids:
                continue
            if rel_id.startswith(("npc-", "enemy-", "item-", "player")):
                continue
            raise AssertionError(f"[턴 {turn}] 관계 참조 ID 무결성 오류: {rel_id}")

        # Sequence / Act transition sanity checks between turns.
        if self.prev_state:
            prev_session = self.prev_state.get("session") or {}
            prev_seq = prev_session.get("current_sequence_id")
            prev_act = prev_session.get("current_act_id")

            if prev_seq != current_seq_id:
                if self.scenario_seq_ids and current_seq_id not in self.scenario_seq_ids:
                    raise AssertionError(
                        f"[턴 {turn}] 시나리오 명세 외 시퀀스 전이: {current_seq_id}"
                    )
            if prev_act != current_act_id:
                if self.scenario_act_ids and current_act_id not in self.scenario_act_ids:
                    raise AssertionError(
                        f"[턴 {turn}] 시나리오 명세 외 액트 전이: {current_act_id}"
                    )

            # Heuristic assertion: acquisition narrative should increase inventory.
            if self._narrative_implies_item_acquire(combined_narrative):
                prev_inv = self._inventory_item_ids(self.prev_state)
                now_inv = self._inventory_item_ids(state)
                if len(now_inv) <= len(prev_inv):
                    raise AssertionError(
                        f"[턴 {turn}] 획득 서술 대비 인벤토리 증가 없음"
                    )

            # Trigger-aware sequence transition assertion:
            # If action clearly includes an exit trigger phrase and narrative implies progress,
            # sequence should not remain unchanged.
            triggers = [str(t).strip() for t in (seq.get("exit_triggers") or []) if str(t).strip()]
            trigger_hit = self._is_trigger_satisfied(
                action=player_action,
                triggers=triggers,
            )
            normalized_narrative = self._normalize_text(combined_narrative)
            if re.search(r"(위해|하려|시도|준비|필요|계획)", normalized_narrative):
                progress_hint = None
            else:
                progress_hint = re.search(
                    r"(안으로들어갔|안으로들어섰|진입했|문이열렸|관문통과했|도달했|넘어갔)",
                    normalized_narrative,
                    flags=re.IGNORECASE,
                )
            if trigger_hit and progress_hint and prev_seq == current_seq_id:
                raise AssertionError(
                    f"[턴 {turn}] exit_trigger 충족 정황 대비 시퀀스 전이 없음 ({current_seq_id})"
                )

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
        self.scenario_seq_ids = {
            str(seq.get("id"))
            for seq in scenario.get("sequences", [])
            if isinstance(seq, dict) and seq.get("id")
        }
        self.scenario_act_ids = {
            str(act.get("id"))
            for act in scenario.get("acts", [])
            if isinstance(act, dict) and act.get("id")
        }

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
            self.prev_state = await self.agent.client.get_session_state(self.session_id)

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
                current_state = await self.agent.client.get_session_state(self.session_id)
                self._assert_state_consistency(
                    turn=turn,
                    state=current_state,
                    combined_narrative=combined_narrative,
                    player_action=action,
                )
                self.prev_state = current_state

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
