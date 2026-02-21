# 테스트/구조 점검 리포트 (2026-02-08)

## 범위
- 유닛 테스트/커버리지: `gm`, `state-manager`, `scenario-service`, `llm-gateway`
- 통합 러너: `smoke10`, `endurance20`
- 제외: `rule-engine`, `BE-router` (요청사항 기준)

## 결과 요약
- 기준 충족
  - `gm` 커버리지 86.73%
  - `state-manager` 커버리지 83.36%
  - `scenario-service` 커버리지 80.35%
  - `llm-gateway` 커버리지 81.78%
  - 통합 러너 2종 모두 오류 중단 없이 완료

## 보완 결과
- `gm` 실패 테스트 수정 완료
  - `tests/test_interfaces.py`의 `MockStateManager`에 `end_session` 추가
- `state-manager` 보강 테스트 추가
  - `tests/test_progress_repository_unit.py`
  - `tests/test_trace_repository_unit.py`
  - `tests/test_state_service_unit.py`
- `scenario-service` 보강 테스트 추가
  - `tests/test_rule_engine_adapter.py`
  - `tests/test_llm_adapter_extended.py`
  - `tests/test_interfaces_coverage.py`

## 잠재적 문제
- 계약 드리프트 위험
  - 인터페이스 확장(`end_session`) 시 테스트 더블/하위 구현 동기화가 누락될 수 있음.
- 장기 턴 관찰성 한계
  - 러너 턴 번호와 상태 턴 증가 방식(플레이어+NPC 반영)이 달라 보이며, 장기 회귀 시 해석 혼동 가능성이 있음.
- 시나리오 명세 가시성 불일치
  - 러너 출력의 시나리오 명세가 `acts/npcs/enemies/sequences = 0`으로 보이는데, 실제 상태에는 엔티티/시퀀스가 존재.
  - 데이터 로드/표시 레이어 간 정합성 검증 포인트가 필요함.
- 외부 의존 플래키 가능성
  - LLM 호출/외부 서비스 응답 지연이 길어질 경우, 통합 테스트 시간이 크게 변동하며 실패 재현성이 낮아질 수 있음.

## 현재 구조가 목적 달성에 주는 문제
- 서비스 간 결합이 계약 중심으로 엄격히 고정되지 않음
  - 다수 경로가 런타임 dict/가공 로직에 의존하여, 계약 변경 시 전파 누락이 발생하기 쉬움.
- 테스트 피라미드 불균형
  - 통합 시나리오는 강화되었지만, 일부 핵심 도메인 로직(상태 저장소/시나리오 어댑터)의 분기 단위 테스트가 얕아 커버리지 목표 미달로 이어짐.
- 종료 조건/전투 상태 결합의 검증 비용 높음
  - 종료/전이/전투 반영이 다중 서비스에 걸쳐 있어, 회귀 시 원인 분리가 느리고 디버깅 비용이 큼.

## 권장 후속 조치
1. `state-manager`의 `repositories/player.py`(42%)와 `session.py`(55%) 중심 추가 단위 테스트로 여유 마진 확보.
2. `scenario-service`의 `scenario_engine.py`/`plugins/db/adapter.py` 경계 케이스 테스트를 보강해 회귀 내성 강화.
3. 러너 리포트에 `러너 턴`, `세션 턴`, `커밋 횟수`를 함께 기록해 장기 추적성을 개선.
