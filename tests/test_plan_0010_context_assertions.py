import asyncio
from types import SimpleNamespace

from tester.runner import IntegrationTestRunner


class _StateClient:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.idx = 0

    async def get_session_state(self, session_id: str):
        if self.idx >= len(self.snapshots):
            return self.snapshots[-1]
        value = self.snapshots[self.idx]
        self.idx += 1
        return value

    async def get_summary(self, session_id: str):
        return "opening"


class _AgentBase:
    def __init__(self, session_id: str, snapshots, narratives):
        self.session_id = session_id
        self.client = _StateClient(snapshots)
        self._narratives = narratives
        self._turn = 0

    async def setup_session(
        self,
        concept: str,
        force_generate: bool = False,
        preferred_scenario_id: str | None = None,
        preferred_scenario_title_exact: str | None = None,
        preferred_scenario_title: str | None = None,
        strict_load: bool = False,
    ):
        scenario = {
            "title": "t",
            "genre": "g",
            "difficulty": "d",
            "summary": "s",
            "acts": [{"id": "act-1"}],
            "npcs": [],
            "enemies": [],
            "sequences": [{"id": "seq-1"}, {"id": "seq-2"}],
        }
        return self.session_id, scenario

    async def act(self, last_narrative=None):
        return "행동"

    async def run_step(self, user_action=None):
        self._turn += 1
        text = self._narratives[self._turn - 1]
        return SimpleNamespace(narrative=text, npc_turn=SimpleNamespace(narrative=None))


def _base_snapshot(
    turn: int,
    seq_id: str = "seq-1",
    inv_count: int = 0,
    exit_triggers=None,
    status: str = "active",
    seq_npcs=None,
    seq_enemies=None,
):
    triggers = exit_triggers if exit_triggers is not None else []
    seq_npcs = seq_npcs if seq_npcs is not None else []
    seq_enemies = seq_enemies if seq_enemies is not None else []
    return {
        "session": {
            "scenario_id": "scn-1",
            "current_act_id": "act-1",
            "current_sequence_id": seq_id,
            "current_turn": turn,
            "status": status,
        },
        "player": {"player": {"hp": 100, "mp": 50, "san": 10, "gold": 0}},
        "npcs": [],
        "enemies": [],
        "sequence": {
            "scenario_id": "scn-1",
            "sequence_id": seq_id,
            "goal": "goal",
            "exit_triggers": triggers,
            "entity_relations": [],
            "player_npc_relations": [],
            "npcs": seq_npcs,
            "enemies": seq_enemies,
            "items": [],
        },
        "act": {"act_id": "act-1"},
        "inventory": {
            "items": [
                {"scenario_item_id": f"item-{i + 1}", "name": f"i{i + 1}"}
                for i in range(inv_count)
            ]
        },
        "items": [],
        "gm_snapshot": {},
    }


def test_context_assertion_success(monkeypatch):
    snapshots = [
        _base_snapshot(0),  # initial
        _base_snapshot(0),  # prev_state load
        _base_snapshot(1),
        _base_snapshot(2, seq_id="seq-2"),  # transition to valid sequence
    ]
    narratives = ["탐색한다", "계속 이동한다"]

    class _Agent(_AgentBase):
        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner("ctx-ok", max_turns=2)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "success"


def test_context_assertion_item_acquire_without_inventory(monkeypatch):
    snapshots = [
        _base_snapshot(0),
        _base_snapshot(0),
        _base_snapshot(1, inv_count=0),
    ]
    narratives = ["아이템을 획득했다"]

    class _Agent(_AgentBase):
        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner("ctx-fail", max_turns=1)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "failed"
    assert "인벤토리 증가 없음" in str(report["error"])


def test_context_assertion_trigger_progress_without_sequence_change(monkeypatch):
    snapshots = [
        _base_snapshot(0, exit_triggers=["석문을 파괴하고 무덤 안으로 들어간다."]),
        _base_snapshot(0, exit_triggers=["석문을 파괴하고 무덤 안으로 들어간다."]),
        _base_snapshot(
            1, seq_id="seq-1", exit_triggers=["석문을 파괴하고 무덤 안으로 들어간다."]
        ),
    ]
    narratives = ["석문을 파괴하고 무덤 안으로 진입했다"]

    class _Agent(_AgentBase):
        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

        async def act(self, last_narrative=None):
            return "석문을 부수고 무덤 안으로 들어간다."

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner("ctx-trigger-fail", max_turns=1)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "failed"
    assert "시퀀스 전이 없음" in str(report["error"])


def test_sequence_transition_tracks_entity_appearance_departure(monkeypatch):
    snapshots = [
        _base_snapshot(
            0,
            seq_id="seq-1",
            seq_enemies=[{"scenario_entity_id": "enemy-1"}],
        ),
        _base_snapshot(
            0,
            seq_id="seq-1",
            seq_enemies=[{"scenario_entity_id": "enemy-1"}],
        ),
        _base_snapshot(
            1,
            seq_id="seq-2",
            seq_npcs=[{"scenario_entity_id": "npc-1"}],
        ),
        _base_snapshot(
            1,
            seq_id="seq-2",
            seq_npcs=[{"scenario_entity_id": "npc-1"}],
        ),
    ]
    narratives = ["시퀀스가 전환되었다"]

    class _Agent(_AgentBase):
        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner("ctx-transition-entities", max_turns=1)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "success"
    assert report["sequence_transitions"]
    tr = report["sequence_transitions"][0]
    assert tr["from_sequence_id"] == "seq-1"
    assert tr["to_sequence_id"] == "seq-2"
    assert "npc-1" in tr["entered_entities"]
    assert "enemy-1" in tr["departed_entities"]


def test_session_end_requires_closing_narrative(monkeypatch):
    snapshots = [
        _base_snapshot(0),
        _base_snapshot(0),
        _base_snapshot(1, status="ended"),
        _base_snapshot(1, status="ended"),
    ]
    narratives = ["문이 닫혔다."]

    class _Agent(_AgentBase):
        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner("ctx-ended-no-closing", max_turns=1)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "failed"
    assert "마무리 나레이션" in str(report["error"])


def test_session_end_with_closing_narrative(monkeypatch):
    snapshots = [
        _base_snapshot(0),
        _base_snapshot(0),
        _base_snapshot(1, status="ended"),
        _base_snapshot(1, status="ended"),
    ]
    narratives = ["모험은 끝이 났고, 당신의 여정은 마무리되었다."]

    class _Agent(_AgentBase):
        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner("ctx-ended-closing", max_turns=1)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "success"
    assert report["session_ended"] is True


def test_three_sequence_profile_requires_three_sequences(monkeypatch):
    snapshots = [_base_snapshot(0), _base_snapshot(0)]
    narratives = ["행동"]

    class _Agent(_AgentBase):
        async def setup_session(
            self,
            concept: str,
            force_generate: bool = False,
            preferred_scenario_id: str | None = None,
            preferred_scenario_title_exact: str | None = None,
            preferred_scenario_title: str | None = None,
            strict_load: bool = False,
        ):
            scenario = {
                "title": "t",
                "genre": "g",
                "difficulty": "d",
                "summary": "s",
                "acts": [{"id": "act-1"}],
                "npcs": [],
                "enemies": [],
                "sequences": [{"id": "seq-1"}, {"id": "seq-2"}],
            }
            return self.session_id, scenario

        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner(
        "ctx-profile-short", max_turns=1, scenario_profile="three_sequence_combat"
    )
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "failed"
    assert "시퀀스 수 부족" in str(report["error"])


def test_three_sequence_profile_combat_seen(monkeypatch):
    snapshots = [
        _base_snapshot(0, seq_id="seq-1"),
        _base_snapshot(0, seq_id="seq-1"),
        _base_snapshot(1, seq_id="seq-2"),
        _base_snapshot(1, seq_id="seq-2"),
        _base_snapshot(
            2,
            seq_id="seq-3",
            seq_enemies=[{"scenario_entity_id": "enemy-9"}],
        ),
        _base_snapshot(
            2,
            seq_id="seq-3",
            seq_enemies=[{"scenario_entity_id": "enemy-9"}],
        ),
    ]
    narratives = ["다음 구역으로 이동했다", "협상에 성공했다", "적을 공격해 전투를 시작했다"]

    class _Agent(_AgentBase):
        async def setup_session(
            self,
            concept: str,
            force_generate: bool = False,
            preferred_scenario_id: str | None = None,
            preferred_scenario_title_exact: str | None = None,
            preferred_scenario_title: str | None = None,
            strict_load: bool = False,
        ):
            scenario = {
                "title": "t",
                "genre": "g",
                "difficulty": "d",
                "summary": "s",
                "acts": [{"id": "act-1"}],
                "npcs": [],
                "enemies": [],
                "sequences": [{"id": "seq-1"}, {"id": "seq-2"}, {"id": "seq-3"}],
            }
            return self.session_id, scenario

        def __init__(self, session_id: str):
            super().__init__(session_id, snapshots, narratives)

    monkeypatch.setattr("tester.runner.TesterAgent", _Agent)
    runner = IntegrationTestRunner(
        "ctx-profile-combat", max_turns=3, scenario_profile="three_sequence_combat"
    )
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "success"
    assert report["sequence_combat_seen"] is True
    assert report["scenario_profile"] == "three_sequence_combat"
