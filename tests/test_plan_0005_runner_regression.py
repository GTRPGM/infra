import asyncio
from types import SimpleNamespace

from tester.runner import IntegrationTestRunner


class _FakeClient:
    async def get_session_state(self, session_id: str):
        return {
            "session": {
                "scenario_id": "scn-1",
                "current_act_id": "act-1",
                "current_sequence_id": "seq-1",
                "current_turn": 1,
            },
            "player": {"player": {"hp": 100, "mp": 50, "san": 10, "gold": 0}},
            "npcs": [],
            "enemies": [],
            "sequence": {"sequence_id": "seq-1", "goal": "goal", "exit_triggers": []},
            "act": {"act_id": "act-1"},
            "inventory": {"items": []},
            "items": [],
            "gm_snapshot": {},
        }

    async def get_summary(self, session_id: str):
        return "opening"


class _FakeAgent:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client = _FakeClient()
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
            "acts": [],
            "npcs": [],
            "enemies": [],
            "sequences": [],
        }
        return self.session_id, scenario

    async def act(self, last_narrative=None):
        return "행동"

    async def run_step(self, user_action=None):
        self._turn += 1
        return SimpleNamespace(
            narrative=f"narr-{self._turn}",
            npc_turn=SimpleNamespace(narrative=f"npc-{self._turn}"),
        )


class _FailingAgent(_FakeAgent):
    async def run_step(self, user_action=None):
        self._turn += 1
        if self._turn == 3:
            raise RuntimeError("forced failure")
        return await super().run_step(user_action)


def test_runner_smoke_10_turns(monkeypatch):
    monkeypatch.setattr("tester.runner.TesterAgent", _FakeAgent)
    runner = IntegrationTestRunner("smoke10", max_turns=10)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "success"
    assert report["total_turns"] == 10
    assert "alive_enemies_in_current_sequence" in report
    assert "alive_enemies_in_current_sequence" in report["details"][0]


def test_runner_endurance_20_turns(monkeypatch):
    monkeypatch.setattr("tester.runner.TesterAgent", _FakeAgent)
    runner = IntegrationTestRunner("endurance20", max_turns=20)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "success"
    assert report["total_turns"] == 20
    assert "alive_enemies_in_current_sequence" in report
    assert "alive_enemies_in_current_sequence" in report["details"][0]


def test_runner_failure_repro(monkeypatch):
    monkeypatch.setattr("tester.runner.TesterAgent", _FailingAgent)
    runner = IntegrationTestRunner("failcase", max_turns=10)
    report = asyncio.run(runner.run_full_test())
    assert report["status"] == "failed"
    assert report["completed_turns"] == 1
