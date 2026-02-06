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

    async def setup_session(self, concept: str):
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
):
    triggers = exit_triggers if exit_triggers is not None else []
    return {
        "session": {
            "scenario_id": "scn-1",
            "current_act_id": "act-1",
            "current_sequence_id": seq_id,
            "current_turn": turn,
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
            "items": [],
        },
        "act": {"act_id": "act-1"},
        "inventory": {
            "items": [
                {"scenario_item_id": f"item-{i+1}", "name": f"i{i+1}"}
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
        _base_snapshot(1, seq_id="seq-1", exit_triggers=["석문을 파괴하고 무덤 안으로 들어간다."]),
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
