from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from tester.adapter import LLMGatewayChatModel
from tester.client import GMClient
from tester.models import GameTurnResponse
import os


class TesterAgent:
    def __init__(self, session_id: str, model_name: Optional[str] = None):
        self.session_id = session_id
        self.llm = (
            LLMGatewayChatModel(model_name=model_name)
            if model_name
            else LLMGatewayChatModel()
        )
        self.client = GMClient()
        self.history: List[BaseMessage] = []
        self._initialize_persona()

    def _initialize_persona(self):
        # services/gm/docs 내의 모든 .md 파일을 읽어서 컨텍스트로 활용
        docs_context = []
        docs_dir = "services/gm/docs"
        if os.path.exists(docs_dir):
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    if file.endswith(".md"):
                        try:
                            with open(
                                os.path.join(root, file), "r", encoding="utf-8"
                            ) as f:
                                docs_context.append(
                                    f"--- Document: {file} ---\n{f.read()}"
                                )
                        except Exception:
                            pass

        all_docs = "\n\n".join(docs_context)

        system_prompt = f"""당신은 전문적인 TRPG 테스터 에이전트입니다.
당신의 임무는 플레이어로서 게임에 참여하여 GM Core 시스템을 테스트하는 것입니다.
시스템이 규칙과 시나리오를 어떻게 처리하는지 확인하기 위해 다양한 창의적이고 논리적인 행동을 시도해야 합니다.

시스템 문서의 핵심 원칙:
- 시나리오 제약 사항은 규칙(Rule)보다 높은 우선순위를 가집니다.
- 모든 상태 변화는 나레이션이 생성되기 전 단일 커밋을 통해 발생합니다.
- 게임은 턴제 구조(플레이어 턴 후 NPC/나레이터 턴)를 따릅니다.

시스템 문서 컨텍스트:
{all_docs}

지침:
1. GM의 나레이션을 주의 깊게 관찰하고 문맥을 파악하세요.
2. 플레이어 캐릭터로서 자연스럽고 창의적인 행동을 결정하세요.
3. **반드시 한국어로만 답변하세요.**
4. 출력은 오직 플레이어의 행동 텍스트(Natural Language Action)만 포함해야 합니다. 다른 설명은 생략하세요.
"""
        self.history.append(SystemMessage(content=system_prompt))

    async def setup_session(
        self,
        concept: str = "A dark fantasy dungeon exploration",
        force_generate: bool = False,
        preferred_scenario_id: str | None = None,
        preferred_scenario_service_id: str | None = None,
        preferred_scenario_title_exact: str | None = None,
        preferred_scenario_title: str | None = None,
        strict_load: bool = False,
    ) -> tuple[str, dict]:
        disable_scenario_service_inject = (
            str(os.getenv("TESTER_DISABLE_SCENARIO_SERVICE_INJECT", ""))
            .strip()
            .lower()
            in {"1", "true", "yes", "y"}
        )

        # 1) Prefer already-injected scenarios via BE-router state API.
        scenarios = [] if force_generate else await self.client.get_scenarios()
        if scenarios:
            selected = scenarios[0]
            if preferred_scenario_id:
                sid = preferred_scenario_id.strip()
                matched = [
                    s
                    for s in scenarios
                    if sid
                    and sid
                    in {
                        str(s.get("scenario_id") or "").strip(),
                        str(s.get("id") or "").strip(),
                    }
                ]
                if matched:
                    selected = matched[0]
                elif strict_load:
                    raise ValueError(
                        "Pinned state scenario id not found in load mode. "
                        f"scenario_id={preferred_scenario_id!r}"
                    )
            if preferred_scenario_title_exact and not preferred_scenario_id:
                exact = preferred_scenario_title_exact.strip().lower()
                matched = [
                    s
                    for s in scenarios
                    if str(s.get("title", "")).strip().lower() == exact
                ]
                if matched:
                    selected = matched[0]
                elif strict_load and not preferred_scenario_id:
                    raise ValueError(
                        "Exact title scenario not found in load mode. "
                        f"title_exact={preferred_scenario_title_exact!r}"
                    )
            # Hint title matching must not override explicit pin/exact selections.
            if (
                preferred_scenario_title
                and not preferred_scenario_id
                and not preferred_scenario_title_exact
            ):
                hint = preferred_scenario_title.strip().lower()
                matched = [
                    s
                    for s in scenarios
                    if hint in str(s.get("title", "")).strip().lower()
                ]
                if matched:
                    selected = matched[0]
            state_manager_scenario_id = str(
                selected.get("scenario_id") or selected.get("id")
            )
            actual_scenario = {
                "title": selected.get("title", "기존 시나리오"),
                "genre": selected.get("genre", "unknown"),
                "difficulty": selected.get("difficulty", "unknown"),
                "summary": selected.get("description", ""),
                "acts": [],
                "npcs": [],
                "enemies": [],
                "sequences": [],
            }
            # 목록 API는 요약 데이터만 포함될 수 있으므로 상세를 재조회한다.
            if state_manager_scenario_id:
                try:
                    detail = await self.client.get_scenario(state_manager_scenario_id)
                    if isinstance(detail, dict):
                        actual_scenario = {
                            "title": detail.get("title", actual_scenario["title"]),
                            "genre": detail.get("genre", actual_scenario["genre"]),
                            "difficulty": detail.get(
                                "difficulty", actual_scenario["difficulty"]
                            ),
                            "summary": detail.get(
                                "description", actual_scenario["summary"]
                            ),
                            "acts": detail.get("acts", []) or [],
                            "npcs": detail.get("npcs", []) or [],
                            "enemies": detail.get("enemies", []) or [],
                            "sequences": detail.get("sequences", []) or [],
                        }
                except Exception:
                    # 상세 조회가 실패해도 기존 요약 정보로 진행.
                    pass
        elif strict_load:
            raise ValueError(
                "No preloaded scenario found for load mode. "
                f"title_hint={preferred_scenario_title!r}"
            )
        else:
            # 2) Fallback: create + inject scenario through BE-router proxies.
            scenario_data = await self.client.create_scenario(concept)
            actual_scenario = scenario_data.get("data", scenario_data)
            scenario_id = scenario_data.get("scenario_id") or (
                actual_scenario.get("scenario_id")
                if isinstance(actual_scenario, dict)
                else None
            )
            if not scenario_id:
                raise ValueError(f"Failed to create scenario: {scenario_data}")

            inject_result = await self.client.inject_scenario(scenario_id)
            state_manager_scenario_id = inject_result.get(
                "scenario_id"
            ) or inject_result.get("data", {}).get("scenario_id")
            if not state_manager_scenario_id:
                state_manager_scenario_id = scenario_id

        # Ensure ScenarioService has context for the state scenario_id by (re)injecting
        # via ScenarioService pinned ID when available.
        if (
            preferred_scenario_service_id
            and not force_generate
            and not disable_scenario_service_inject
        ):
            try:
                inject_result = await self.client.inject_scenario(
                    preferred_scenario_service_id
                )
                pinned_state_id = inject_result.get("scenario_id") or (
                    inject_result.get("data", {}) if isinstance(inject_result, dict) else {}
                ).get("scenario_id")
                if pinned_state_id:
                    state_manager_scenario_id = str(pinned_state_id)
            except Exception:
                # If reinject fails, keep the previously selected state scenario id.
                pass

        # 3. Start Session (State Manager)
        session_id = await self.client.start_session(state_manager_scenario_id)
        if not session_id:
            raise ValueError("Failed to obtain session_id from state-manager")

        self.session_id = session_id
        return session_id, actual_scenario

    async def act(self, last_narrative: Optional[str] = None) -> str:
        if last_narrative:
            # GM의 나레이션을 히스토리에 추가
            self.history.append(
                HumanMessage(
                    content=f"GM 서술: {last_narrative}\n\n다음 행동은 무엇입니까?"
                )
            )
        else:
            # 게임 시작 시 첫 행동 요청
            self.history.append(
                HumanMessage(
                    content="게임이 시작되었습니다. 당신의 첫 번째 행동은 무엇입니까?"
                )
            )

        # 전체 히스토리를 바탕으로 LLM 호출
        response = await self.llm.ainvoke(self.history)
        action_text = str(response.content)

        # 자신의 행동(AI 응답)을 히스토리에 추가
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
