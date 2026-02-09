import asyncio
import logging
import re
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from tester.agent import TesterAgent
from tester.scenarios import ScenarioProfile, get_profile

# Configure logging to buffer less and capture everything
logger = logging.getLogger("gtrpgm.tester")
logger.setLevel(logging.INFO)


def setup_logging(session_id: str):
    """Sets up dual-channel logging: Console and File."""
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Stream Handler (Console)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # 2. File Handler
    log_dir = Path("log")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_filename = str(
        log_dir / f"test_output_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("[CHANGE] logging initialized output_file=%s", log_filename)
    return log_filename


class IntegrationTestRunner:
    def __init__(
        self,
        session_id: str,
        max_turns: int = 20,
        require_session_end: bool = False,
        scenario_profile: str | None = None,
    ):
        self.session_id = session_id
        self.max_turns = max_turns
        self.require_session_end = require_session_end
        self.scenario_profile_name = scenario_profile
        self.profile: ScenarioProfile | None = get_profile(scenario_profile)
        self.agent = TesterAgent(session_id)
        self.results: List[Dict[str, Any]] = []
        self.prev_state: Dict[str, Any] | None = None
        self.scenario_seq_ids: set[str] = set()
        self.scenario_act_ids: set[str] = set()
        self.sequence_order: list[str] = []
        self.dynamic_sequence_order: list[str] = []
        self.observed_sequence_ids: set[str] = set()
        self.sequence_combat_seen: bool = False
        self.sequence_transition_events: List[Dict[str, Any]] = []
        self.sequence_trace: List[str] = []
        self.session_ended: bool = False
        self.relation_history: List[Dict[str, Any]] = []
        # Setup logging immediately
        self.log_file = setup_logging(session_id)

    @staticmethod
    def _log_test(message: str, *args: Any) -> None:
        logger.info("[TEST] " + message, *args)

    @staticmethod
    def _log_state(message: str, *args: Any) -> None:
        logger.info("[STATE] " + message, *args)

    @staticmethod
    def _log_change(message: str, *args: Any) -> None:
        logger.info("[CHANGE] " + message, *args)

    @staticmethod
    def _hp_of(entity: Dict[str, Any]) -> Any:
        if entity.get("current_hp") is not None:
            return entity.get("current_hp")
        state = entity.get("state") or {}
        if state.get("hp") is not None:
            return state.get("hp")
        numeric = state.get("numeric") or {}
        if numeric.get("HP") is not None:
            return numeric.get("HP")
        return numeric.get("hp")

    @classmethod
    def _count_alive_enemies_in_current_sequence(cls, state: Dict[str, Any]) -> int:
        seq = state.get("sequence") or {}
        enemies = seq.get("enemies", []) if isinstance(seq, dict) else []
        alive = 0
        for enemy in enemies:
            if not isinstance(enemy, dict):
                continue
            if bool(enemy.get("is_defeated")):
                continue
            hp = cls._hp_of(enemy)
            if hp is None:
                alive += 1
                continue
            try:
                if int(hp) > 0:
                    alive += 1
            except (TypeError, ValueError):
                alive += 1
        return alive

    async def _log_state_snapshot(self, label: str = "현재 상태"):
        state = await self.agent.client.get_session_state(self.session_id)
        player = state.get("player") or {}
        session = state.get("session") or {}
        seq_details = state.get("sequence") or {}
        seq_npcs = seq_details.get("npcs", []) if isinstance(seq_details, dict) else []
        seq_enemies = (
            seq_details.get("enemies", []) if isinstance(seq_details, dict) else []
        )
        npcs = seq_npcs if seq_npcs else (state.get("npcs") or [])
        enemies = seq_enemies if seq_enemies else (state.get("enemies") or [])

        lines = []
        lines.append(f"\n--- {label} ---")
        lines.append(
            f"세션: 액트({session.get('current_act_id')}), 시퀀스({session.get('current_sequence_id')}), 턴({session.get('current_turn')})"
        )

        # Sequence Goal & Triggers
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
            npc_str = ", ".join(
                [
                    f"{n.get('scenario_entity_id') or n.get('scenario_npc_id')}(HP:{self._hp_of(n)})"
                    for n in safe_npcs
                ]
            )
            lines.append(f"NPC 목록(현재 시퀀스 기준): {npc_str if npc_str else '없음'}")
        else:
            lines.append("NPC 목록(현재 시퀀스 기준): 없음")

        # Enemy Stats
        if enemies:
            safe_enemies = [e for e in enemies if isinstance(e, dict)]
            enemy_str = ", ".join(
                [
                    f"{e.get('scenario_entity_id') or e.get('scenario_enemy_id')}(HP:{self._hp_of(e)})"
                    for e in safe_enemies
                ]
            )
            lines.append(f"적 목록(현재 시퀀스 기준): {enemy_str if enemy_str else '없음'}")
        else:
            lines.append("적 목록(현재 시퀀스 기준): 없음")

        # Items in Sequence
        items = seq_details.get("items", [])
        if items:
            safe_items = [i for i in items if isinstance(i, dict)]
            item_str = ", ".join(
                [f"{i.get('scenario_item_id')}({i.get('name')})" for i in safe_items]
            )
            lines.append(f"아이템 목록: {item_str if item_str else '없음'}")
        else:
            lines.append("아이템 목록: 없음")

        relations = self._gather_relations(state)
        if relations["entity_relations"] or relations["player_npc_relations"]:
            lines.append("관계 목록:")
            for entry in self._relation_lines(relations):
                lines.append(entry)
        else:
            lines.append("관계 목록: 없음")

        # Inventory / Owned Items
        inventory = state.get("inventory") or {}
        if isinstance(inventory, list):
            inv_items = inventory
        elif isinstance(inventory, dict):
            inv_items = inventory.get("items", []) or []
        else:
            inv_items = []
        if inv_items:
            safe_inv_items = [i for i in inv_items if isinstance(i, dict)]
            inv_item_str = ", ".join(
                [
                    (
                        f"{i.get('scenario_item_id') or i.get('item_id')}"
                        f"({i.get('name') or i.get('item_name') or 'unknown'})"
                    )
                    for i in safe_inv_items
                ]
            )
            lines.append(f"인벤토리: {inv_item_str if inv_item_str else '없음'}")
        else:
            lines.append("인벤토리: 없음")
        lines.append("-" * (len(label) + 8))

        self._log_state("%s", "\n".join(lines))

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

    def _gather_relations(self, state: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        seq = state.get("sequence") or {}
        def safe_list(path: list | None) -> list:
            return [rel for rel in (path or []) if isinstance(rel, dict)]

        return {
            "entity_relations": safe_list(seq.get("entity_relations")),
            "player_npc_relations": safe_list(seq.get("player_npc_relations")),
        }

    def _relation_lines(self, relations: Dict[str, List[Dict[str, Any]]]) -> list[str]:
        lines: list[str] = []
        for rel in relations.get("entity_relations", []):
            lines.append(
                "  - entity: {from_id} -> {to_id} | type={type} affinity={affinity}".format(
                    from_id=rel.get("from_id", "unknown"),
                    to_id=rel.get("to_id", "unknown"),
                    type=rel.get("relation_type", "unspecified"),
                    affinity=rel.get("affinity", "?")
                )
            )
        for rel in relations.get("player_npc_relations", []):
            lines.append(
                "  - player_npc: npc={npc_id} | relation={relation_type} affinity={affinity}".format(
                    npc_id=rel.get("npc_id", "unknown"),
                    relation_type=rel.get("relation_type", "unspecified"),
                    affinity=rel.get("affinity", "?")
                )
            )
        return lines

    def _sequence_entity_ids(self, state: Dict[str, Any]) -> set[str]:
        seq = state.get("sequence") or {}
        ids: set[str] = set()

        for npc in seq.get("npcs", []) or []:
            if isinstance(npc, dict):
                for k in ("scenario_entity_id", "scenario_npc_id", "npc_id"):
                    if npc.get(k):
                        ids.add(str(npc.get(k)))
                        break

        for enemy in seq.get("enemies", []) or []:
            if isinstance(enemy, dict):
                for k in ("scenario_entity_id", "scenario_enemy_id", "enemy_id"):
                    if enemy.get(k):
                        ids.add(str(enemy.get(k)))
                        break

        for item in seq.get("items", []) or []:
            if isinstance(item, dict):
                for k in ("scenario_item_id", "item_id"):
                    if item.get(k):
                        ids.add(str(item.get(k)))
                        break

        return ids

    def _is_closing_narrative(self, narrative: str) -> bool:
        text = (narrative or "").strip()
        if not text:
            return False
        return bool(
            re.search(
                r"(엔딩|결말|막을 내|마무리|끝이 났|끝났다|종결|여정이 끝|모험이 끝|해냈다|승리했다|클리어)",
                text,
                flags=re.IGNORECASE,
            )
        )

    def _validate_profile_manifest(self, scenario: Dict[str, Any]) -> None:
        if not self.profile:
            return
        sequences = scenario.get("sequences", []) if isinstance(scenario, dict) else []
        if not sequences:
            logger.warning(
                "[프로필 %s] 로드 모드에서 시퀀스 명세가 비어 있음. 런타임 관측 기반으로 검증합니다.",
                self.profile.name,
            )
            return
        if len(sequences) < self.profile.min_sequences:
            raise AssertionError(
                f"[프로필 {self.profile.name}] 시퀀스 수 부족: "
                f"expected>={self.profile.min_sequences}, got={len(sequences)}"
            )

        ids = [
            str(seq.get("id"))
            for seq in sequences
            if isinstance(seq, dict) and seq.get("id")
        ]
        if len(ids) >= self.profile.min_sequences:
            self.sequence_order = ids[: self.profile.min_sequences]

    def _remember_sequence(self, seq_id: str) -> None:
        seq = str(seq_id or "").strip()
        if not seq:
            return
        self.observed_sequence_ids.add(seq)
        self.sequence_trace.append(seq)
        if seq not in self.dynamic_sequence_order:
            self.dynamic_sequence_order.append(seq)

    def _assert_no_oscillation_loop(self, turn: int) -> None:
        # Detect short ABAB oscillation loops that usually indicate broken transition rules.
        if len(self.sequence_trace) < 6:
            return
        last = self.sequence_trace[-6:]
        a, b = last[-2], last[-1]
        if not a or not b or a == b:
            return
        if last == [a, b, a, b, a, b]:
            raise AssertionError(
                f"[턴 {turn}] 시퀀스 진동 루프 감지: {a}<->{b} 반복"
            )

    def _select_profile_action(self, state: Dict[str, Any]) -> str:
        if not self.profile:
            raise ValueError("profile action requested without profile")

        session = state.get("session") or {}
        current_seq_id = str(session.get("current_sequence_id") or "")
        seq = state.get("sequence") or {}
        triggers = [str(t).strip() for t in (seq.get("exit_triggers") or []) if str(t).strip()]

        trigger_hint = triggers[0] if triggers else ""

        idx = 0
        # Prefer profile-scripted action by detected sequence order.
        if self.sequence_order and current_seq_id in self.sequence_order:
            idx = self.sequence_order.index(current_seq_id)
        elif current_seq_id in self.dynamic_sequence_order:
            idx = self.dynamic_sequence_order.index(current_seq_id)

        idx = min(idx, len(self.profile.scripted_actions) - 1)
        scripted = self.profile.scripted_actions[idx]
        if trigger_hint:
            return f"{scripted} {trigger_hint}"
        return scripted

        # Fallback to trigger-oriented action for transition robustness.
        if triggers:
            return triggers[0]
        goal = str(seq.get("goal") or "다음 단계로 진행한다")
        return f"저는 목표를 달성하기 위해 행동합니다: {goal}"

    def _inventory_item_ids(self, state: Dict[str, Any]) -> set[str]:
        inventory = state.get("inventory") or {}
        if isinstance(inventory, list):
            items = inventory
        elif isinstance(inventory, dict):
            items = inventory.get("items", []) or []
        else:
            items = []

        ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("scenario_item_id", "item_id", "rule_id"):
                if item.get(key) is not None:
                    ids.add(str(item.get(key)))
                    break
        return ids

    def _narrative_implies_item_acquire(self, narrative: str) -> bool:
        text = (narrative or "").strip()
        if not text:
            return False

        # Avoid false positives on re-mention (e.g. "열쇠를 주워들고 ..."):
        # only treat clearly completed acquisition statements as acquire.
        verb = r"(획득했|주웠|얻었|입수했|손에 넣었|인벤토리에 추가)"
        item_noun = (
            r"(아이템|열쇠|검|무기|방패|물약|포션|보석|유물|주화|금화|장비|문서|지도)"
        )

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
        stopwords = {
            "그리고",
            "또는",
            "으로",
            "에서",
            "한다",
            "했다",
            "하기",
            "the",
            "and",
        }
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
        for npc in state.get("npcs") or []:
            if isinstance(npc, dict):
                for k in ("scenario_entity_id", "scenario_npc_id", "npc_id"):
                    if npc.get(k):
                        known_ids.add(str(npc.get(k)))
        for enemy in state.get("enemies") or []:
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
                if (
                    self.scenario_seq_ids
                    and current_seq_id not in self.scenario_seq_ids
                ):
                    raise AssertionError(
                        f"[턴 {turn}] 시나리오 명세 외 시퀀스 전이: {current_seq_id}"
                    )

                prev_entities = self._sequence_entity_ids(self.prev_state)
                now_entities = self._sequence_entity_ids(state)
                entered = sorted(now_entities - prev_entities)
                departed = sorted(prev_entities - now_entities)
                event = {
                    "turn": turn,
                    "from_sequence_id": prev_seq,
                    "to_sequence_id": current_seq_id,
                    "entered_entities": entered,
                    "departed_entities": departed,
                }
                self.sequence_transition_events.append(event)
                self._log_test(
                    "[전이 검증] %s -> %s | 등장=%s | 퇴장=%s",
                    prev_seq,
                    current_seq_id,
                    entered if entered else "없음",
                    departed if departed else "없음",
                )
            if prev_act != current_act_id:
                if (
                    self.scenario_act_ids
                    and current_act_id not in self.scenario_act_ids
                ):
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
            triggers = [
                str(t).strip()
                for t in (seq.get("exit_triggers") or [])
                if str(t).strip()
            ]
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
            lines.append(
                f"  - {act.get('id')}: {act.get('name')} ({act.get('region_name')})"
            )

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
        self._log_test("%s", "\n".join(lines))
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
        self._log_test("--- 통합 테스트 시작 ---")
        start_time = datetime.now()

        try:
            # 0. Setup Session
            self._log_test("세션 설정 중 (시나리오 로드/생성 -> 세션 시작)...")
            concept = (
                self.profile.concept
                if self.profile
                else "A haunted tomb with a skeletal guard and a lost explorer NPC"
            )
            self.session_id, scenario_data = await self.agent.setup_session(
                concept=concept,
                force_generate=False,
                preferred_scenario_id=(
                    self.profile.pinned_state_scenario_id if self.profile else None
                ),
                preferred_scenario_service_id=(
                    self.profile.pinned_scenario_service_id if self.profile else None
                ),
                preferred_scenario_title_exact=(
                    self.profile.load_title_exact if self.profile else None
                ),
                preferred_scenario_title=self.profile.load_title_hint if self.profile else None,
                strict_load=bool(self.profile)
                or str(os.getenv("TESTER_LOAD_ONLY", "")).strip().lower()
                in {"1", "true", "yes", "y"},
            )
            self._log_state("세션 생성 완료: %s", self.session_id)

            # Optional starter loadout provisioning via BE-router state APIs.
            if self.profile and self.profile.starter_loadout_rule_ids:
                granted = await self.agent.client.grant_starter_items(
                    self.session_id, self.profile.starter_loadout_rule_ids
                )
                self._log_change(
                    "starter_loadout granted session=%s rule_ids=%s results=%s",
                    self.session_id,
                    list(self.profile.starter_loadout_rule_ids),
                    granted,
                )

            # Print Scenario Manifest
            await self._log_scenario_manifest(scenario_data)
            self._validate_profile_manifest(scenario_data)

            # Initial State Snapshot
            await self._log_state_snapshot("초기 상태")
            self.prev_state = await self.agent.client.get_session_state(self.session_id)
            initial_seq = str(
                (self.prev_state.get("session") or {}).get("current_sequence_id") or ""
            )
            self._remember_sequence(initial_seq)

            # [수정] 0턴: 오프닝 나레이션 (Briefing) 확보
            self._log_test("=== 오프닝 나레이션(상황 요약) 생성 중... ===")

            # GM의 신규 Summary 엔드포인트를 통해 오프닝을 받아옴
            last_narrative = await self.agent.client.get_summary(self.session_id)

            self._log_state("[GM (오프닝)]: %s", last_narrative)

            # 오프닝을 에이전트 히스토리에 주입
            # act() 호출 시 last_narrative로 전달될 것이므로 여기서는 별도 처리 불필요

            for turn in range(1, self.max_turns + 1):
                self._log_test("%s 제 %s 턴 %s", "=" * 20, turn, "=" * 20)

                # 1. Player Turn
                if self.profile:
                    state_for_action = await self.agent.client.get_session_state(
                        self.session_id
                    )
                    pre_seq = str(
                        (state_for_action.get("session") or {}).get(
                            "current_sequence_id"
                        )
                        or ""
                    )
                    self._remember_sequence(pre_seq)
                    action = self._select_profile_action(state_for_action)
                else:
                    action = await self.agent.act(last_narrative=last_narrative)
                self._log_test("[플레이어]: %s", action)

                player_result = await self.agent.run_step(user_action=action)
                self._log_state("[GM (나레이션)]: %s", player_result.narrative)

                # 2. NPC Turn (Automatic in GM Core)
                npc_result = player_result.npc_turn
                combined_narrative = player_result.narrative

                if npc_result and npc_result.narrative:
                    if getattr(npc_result, "action", None):
                        self._log_state("[GM (NPC action)]: %s", npc_result.action)
                    self._log_state("[GM (NPC 턴)]: %s", npc_result.narrative)
                    combined_narrative += f"\n(NPC 행동): {npc_result.narrative}"
                    if getattr(npc_result, "dialogue", None):
                        self._log_state("[GM (NPC 대사)]: %s", npc_result.dialogue)
                        combined_narrative += f"\n(NPC 대사): {npc_result.dialogue}"
                else:
                    self._log_state("[GM (NPC 턴)]: NPC 행동 없음.")

                # 다음 턴을 위해 나레이션 업데이트
                last_narrative = combined_narrative

                # End of Turn State Snapshot
                await self._log_state_snapshot(f"제 {turn} 턴 종료 후 상태")
                current_state = await self.agent.client.get_session_state(
                    self.session_id
                )
                relations = self._gather_relations(current_state)
                self.relation_history.append(
                    {
                        "turn": turn,
                        "entity_relations": [dict(r) for r in relations["entity_relations"]],
                        "player_npc_relations": [dict(r) for r in relations["player_npc_relations"]],
                    }
                )
                if relations["entity_relations"] or relations["player_npc_relations"]:
                    self._log_state(
                        "[관계 추적] entity=%s player_npc=%s",
                        len(relations["entity_relations"]),
                        len(relations["player_npc_relations"]),
                    )
                self._assert_state_consistency(
                    turn=turn,
                    state=current_state,
                    combined_narrative=combined_narrative,
                    player_action=action,
                )
                self.prev_state = current_state

                current_session = current_state.get("session") or {}
                current_seq_id = str(current_session.get("current_sequence_id") or "")
                self._remember_sequence(current_seq_id)
                self._assert_no_oscillation_loop(turn)
                seq_stage_idx = -1
                if self.sequence_order and current_seq_id in self.sequence_order:
                    seq_stage_idx = self.sequence_order.index(current_seq_id)
                elif current_seq_id in self.dynamic_sequence_order:
                    seq_stage_idx = self.dynamic_sequence_order.index(current_seq_id)

                if self.profile and seq_stage_idx >= 2:
                    seq_data = current_state.get("sequence") or {}
                    enemies = seq_data.get("enemies", []) if isinstance(seq_data, dict) else []
                    combat_hint = bool(
                        re.search(
                            r"(공격|전투|피해|타격|베기|찌르|적을 쓰러뜨)",
                            combined_narrative,
                            flags=re.IGNORECASE,
                        )
                    )
                    if enemies and combat_hint:
                        self.sequence_combat_seen = True

                session_status = str(
                    (current_state.get("session") or {}).get("status", "")
                ).lower()
                if session_status == "ended":
                    if not self._is_closing_narrative(combined_narrative):
                        raise AssertionError(
                            f"[턴 {turn}] 세션 종료(status=ended) 대비 마무리 나레이션 미검출"
                        )
                    self.session_ended = True
                    self._log_test(
                        "[종료 검증] 세션 종료 및 마무리 나레이션 확인 (턴=%s)",
                        turn,
                    )

                self.results.append(
                    {
                        "turn": turn,
                        "player_action": action,
                        "gm_narrative": player_result.narrative,
                        "npc_narrative": npc_result.narrative if npc_result else None,
                        "session_status": (current_state.get("session") or {}).get(
                            "status"
                        ),
                        "relations": relations,
                        "alive_enemies_in_current_sequence": self._count_alive_enemies_in_current_sequence(
                            current_state
                        ),
                        "status": "success",
                    }
                )

                self._log_test("제 %s 턴 완료.", turn)
                if self.session_ended:
                    break

            if self.require_session_end and not self.session_ended:
                raise AssertionError(
                    f"[최대 턴 {self.max_turns}] 시나리오 종료(status=ended) 미도달"
                )
            if self.profile and self.profile.name == "three_sequence_combat":
                observed = {s for s in self.observed_sequence_ids if s}
                if len(observed) < self.profile.min_sequences:
                    raise AssertionError(
                        f"[프로필 {self.profile.name}] "
                        f"시퀀스 도달 부족: observed={sorted(observed)}"
                    )
                if not self.sequence_combat_seen:
                    raise AssertionError(
                        f"[프로필 {self.profile.name}] 3번째 시퀀스 전투 징후 미검출"
                    )

        except Exception as e:
            logger.exception("통합 테스트 실행 중 예외 발생")
            error_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                except Exception:
                    error_detail = e.response.text

            logger.error(
                f"제 {len(self.results) + 1} 턴에서 테스트 실패: {error_detail}"
            )
            return {
                "session_id": self.session_id,
                "status": "failed",
                "error": error_detail,
                "completed_turns": len(self.results),
                "details": self.results,
            }

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self._log_test("--- 통합 테스트 완료 (소요 시간: %.2f초) ---", duration)
        final_state = (
            self.prev_state if isinstance(self.prev_state, dict) else {}
        )
        return {
            "session_id": self.session_id,
            "status": "success",
            "duration_seconds": duration,
            "total_turns": len(self.results),
            "session_ended": self.session_ended,
            "scenario_profile": self.scenario_profile_name,
            "sequence_order": self.sequence_order,
            "sequence_combat_seen": self.sequence_combat_seen,
            "sequence_transitions": self.sequence_transition_events,
            "alive_enemies_in_current_sequence": self._count_alive_enemies_in_current_sequence(
                final_state
            ),
            "relations": self.relation_history,
            "details": self.results,
        }


async def main():
    # Simple CLI for standalone runs
    import sys
    import os

    # Default session ID generation
    default_sid = f"auto-test-{int(datetime.now().timestamp())}"

    session_id = default_sid
    max_turns = 20
    scenario_profile = None
    require_end = str(os.getenv("REQUIRE_SESSION_END", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    if len(sys.argv) > 2:
        max_turns = int(sys.argv[2])
    if len(sys.argv) > 3:
        scenario_profile = sys.argv[3]
    if len(sys.argv) > 4:
        require_end = str(sys.argv[4]).strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }

    runner = IntegrationTestRunner(
        session_id,
        max_turns=max_turns,
        require_session_end=require_end,
        scenario_profile=scenario_profile,
    )
    await runner.run_full_test()
    # Print final JSON to console only, for piping if needed.
    # The detailed logs are already in the file.
    # print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
