# 404 에러 원인 분석: ScenarioService의 Session 상태 부재

## 1. 현상
- `GM`이 `RuleEngine` 판정 후 `ScenarioService`의 `/api/v1/check/session`을 호출.
- `ScenarioService`는 DB의 `session_states` 테이블에서 해당 `session_id`를 조회하려 시도.
- 결과: `404 Not Found` (DB에 해당 세션 정보가 없음).

## 2. 원인
- **세션 생성의 불일치**:
    - `TesterAgent`는 `StateManager`를 통해 세션을 생성(`start_session`)합니다. 이 정보는 `state_manager` DB 스키마(`session` 테이블)에는 저장됩니다.
    - 그러나 `ScenarioService`는 자체적인 `session_states` 테이블을 가지고 있으며, 이 테이블에 세션 정보가 동기화되지 않고 있습니다.
    - `ScenarioService`는 시나리오 "검증(Validation)"을 위해 자신이 관리하는 세션 상태(`current_act_id` 등)를 참조해야 하는데, 정작 세션이 시작될 때 이 테이블에 데이터를 넣는 로직이 호출되지 않았습니다.

## 3. 해결 방안
- **단기 해결책 (Proxy 활용)**:
    - `ScenarioService`가 자신의 DB(`session_states`)를 조회하는 대신, `StateManager`에게 현재 세션 상태를 물어보도록 수정하거나,
    - `GM`이 `ScenarioService`에 요청할 때 필요한 컨텍스트(`act_id`, `seq_id` 등)를 모두 담아서 `/validate` 엔드포인트를 호출하도록 변경합니다. (`/session` 엔드포인트 대신)

- **장기 해결책 (동기화)**:
    - `StateManager`에서 세션이 생성될 때 이벤트를 발행하여 `ScenarioService`도 알게 하거나,
    - `ScenarioService`가 `StateManager`를 SSOT(Single Source of Truth)로 인정하고 API로 조회하도록 변경.

## 4. 즉시 적용할 수정 (`GM` 측 변경)
- `GM`은 이미 `fetch_state`를 통해 `StateManager`로부터 최신 상태(`act_id`, `sequence_id` 등)를 알고 있습니다.
- 따라서 `GM`의 `ScenarioManagerHTTPClient`가 `/api/v1/check/session` (세션 ID만 보냄) 대신, `/api/v1/validate` (명시적 ID들 보냄)를 호출하도록 변경하면 `ScenarioService`가 DB 조회 없이 검증을 수행할 수 있습니다.

### 변경 대상
- `gm/src/gm/plugins/external/http_client.py`: `ScenarioManagerHTTPClient.get_proposal` 메서드.
- `gm/src/gm/core/models/rule.py`: `ScenarioSuggestion` 생성을 위한 정보가 충분한지 확인. (이미 `act_id` 등을 컨텍스트로 가지고 있는지 확인 필요).

**확인 사항**:
- `GM`의 `ScenarioManagerHTTPClient.get_proposal` 메서드 시그니처는 `(content: str, rule_outcome: RuleOutcome)`입니다.
- 여기서 `rule_outcome`에는 `act_id` 등의 정보가 없을 수 있습니다.
- 하지만 `GameEngine`의 `check_scenario` 노드에서 `state` 컨텍스트를 접근할 수 있으므로, `get_proposal` 호출 시 `state` 전체를 넘기거나 필요한 필드를 추가로 넘겨야 합니다.

현재 `GM` 코드:
```python
    async def check_scenario(self, state: TurnContext) -> TurnContext:
        rule_outcome = state.get("rule_outcome")
        ...
        proposal = await self.scenario_client.get_proposal(
            state["user_input"], rule_outcome
        )
```

수정 계획:
1. `ScenarioManagerPort.get_proposal`의 시그니처를 변경하여 `context: Dict[str, Any]` (또는 `TurnContext`)를 받도록 합니다.
2. 구현체(`ScenarioManagerHTTPClient`)에서 `state["act_id"]`, `state["sequence_id"]` 등을 추출하여 `ScenarioService`의 `/api/v1/validate`를 호출하도록 변경합니다.
