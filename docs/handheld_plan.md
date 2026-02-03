# Rule Engine 422 에러 수정 및 GM 데이터 바인딩 개선 계획

## 1. 목적
- GM 서비스가 Rule Engine에 요청을 보낼 때 발생하는 422(Validation Error)를 해결.
- Rule Engine의 `EntityUnit` 스키마와 GM의 `RuleRequestEntity` 스키마 불일치 해소.
- State Manager의 세션 스냅샷에서 `player_id`를 동적으로 가져와 룰 엔진에 전달.

## 2. 현황
- GM의 `RuleRequestEntity`가 `state_entity_id`를 `entity_id`라는 별칭으로 보내고 있어, Rule Engine의 `EntityUnit` 구조(두 필드 모두 존재)와 충돌 가능성.
- GM이 플레이어 정보를 하드코딩하거나 불완전하게 생성하여 전달 중.

## 3. 상세 계획
1.  **GM 모델 수정**: `gm/src/gm/core/models/rule.py`의 `RuleRequestEntity`를 Rule Engine의 `EntityUnit`과 호환되도록 수정.
2.  **HTTP 클라이언트 수정**: `gm/src/gm/plugins/external/http_client.py`에서:
    - State Manager로부터 현재 세션의 상태(`player_id` 등)를 조회.
    - 조회된 정보를 바탕으로 `RuleRequestEntity` 목록을 정확히 구성.
    - `state_entity_id`(UUID 문자열)와 `entity_id`(Master 정수 ID)를 명확히 구분하여 전달.
3.  **테스트**: `test-session-success-final` 시나리오를 실행하여 422 에러 해소 및 정상 흐름 확인.

## 4. 진행 로그
- [x] 2026-02-03: 계획 수립
- [x] 2026-02-03: GM `RuleRequestEntity` 모델 수정 및 룰 엔진 호환성 확보.
- [x] 2026-02-03: 룰 엔진 `PlaySceneRequest/Response`에서 `scenario_id` 타입을 `str`로 변경 (UUID 통일 정책 반영).
- [x] 2026-02-03: `GameEngine.fetch_state`에서 `SequenceDetailInfo`를 함께 가져오도록 개선.
- [x] 2026-02-03: `RuleManagerHTTPClient.get_proposal`에서 동적으로 엔티티 목록(Player, NPC, Enemy)을 구성하도록 수정.
- [ ] 2026-02-03: 통합 테스트 실행 및 422 에러 해소 확인.
