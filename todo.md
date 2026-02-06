# GTRPGM Integration TODO (State-first)

## 0. 제약/원칙

- Source of Truth(SST): `state-manager`의 현재 주입/조회 스키마와 동작.
- 금지: `state-manager`, `rule-engine` 코드 변경 금지.
- 허용: `scenario-service`, `gm`, `tester/src/tester`, 실행 스크립트/문서/테스트 보강.
- 목표: `bin/project` 기반으로 서비스 기동 후, 실제 턴 루프(플레이어 턴 + NPC 턴)가 안정 동작.

## 1. 현재 파악된 핵심 갭 (수정 우선순위)

1. `scenario-service` 주입 모델이 `state-manager` 주입 모델과 불일치.

- `scenario-service`: `item_id/master_id`, 확장 필드(`summary`, `difficulty`, `genre`, `total_acts`, `sequence_type` 등) 중심.
- `state-manager`: `scenario_item_id/rule_id` 중심, `ScenarioInjectRequest` 기준 필드 강제.
- 결과: 생성→주입 경로에서 422/의미 손실 가능성 높음.

2. 그래프/관계/엣지 주입 ID 규약 불일치 가능성.

- `scenario-service` 내부 full-graph 결과는 `scenario_item_id/master_id` 성향,
- 주입 변환은 다른 키(`item_id/master_id`)를 기대.
- 관계(`relations`)의 from/to가 카탈로그 ID와 정확히 매핑되는지 검증 필요.

3. GM이 소비하는 스냅샷 필드와 state 응답 필드 정렬 필요.

- `scenario_entity_id`, `current_act_id`, `current_sequence_id`, `entity_relations` 처리 경로 점검 필요.
- 턴 진행 중 시나리오 전이(`next_act_id`, `next_seq_id`) 반영/로그 검증 강화 필요.

## 2. 실행 계획

### Phase A. 실행 기반 고정 (`bin/project`)

1. 루트에서 기본 서비스 부팅.

- `./bin/project up`
- `./bin/project ps`
- `./bin/project logs [service]`로 health 확인.

2. 헬스체크 스냅샷 확보.

- GM: `GET /health`
- Scenario: `GET /health`
- State: `GET /health`
- Rule: `GET /health`
- LLM Gateway: `GET /health`

3. 실패 서비스 원인 분리.

- 환경변수/포트/DB 마이그레이션/의존성 순서 확인.

완료 기준

- 핵심 5개 서비스(services/gm/state/scenario/rule/llm) 모두 `healthy` 또는 200 응답.

### Phase B. 시나리오 생성→주입 스키마 정렬 (최우선)

1. `state-manager` 주입 규격을 정식 계약으로 고정.

- 기준: `services/state-manager/src/state_db/schemas/scenario.py`
- 기준: `services/state-manager/src/state_db/repositories/scenario.py` 실제 저장 로직.

2. `scenario-service` 주입 DTO/변환기 정렬.

- 대상: `services/scenario-service/src/scenario/core/models/generation.py`
- 대상: `services/scenario-service/src/scenario/core/engine/scenario_engine.py`
- 대상: `services/scenario-service/src/scenario/plugins/db/adapter.py`
- 조치:
  - 카탈로그 ID를 state 기준 키로 변환.
  - `master_id -> rule_id` 변환 규칙 명시(정수화 실패시 정책 포함).
  - 아이템 키를 `scenario_item_id/rule_id` 체계로 정렬.
  - 액트/시퀀스/관계 참조 ID를 state 주입 시점 기준으로 1:1 보장.

3. 그래프 관계/엣지 주입 일치 보장.

- Sequence의 `npcs/enemies/items` 참조 무결성 검사.
- `relations.from_id/to_id`가 실제 주입 카탈로그 ID와 일치하는지 사전 검증.

4. 스키마 계약 테스트 보강.

- `services/scenario-service/tests/test_injection_reference_match.py`를 state 기준으로 업데이트.
- 생성 결과를 state 모델로 직접 validate하는 계약 테스트 추가.

완료 기준

- `POST /api/v1/generation/pure` → `POST /api/v1/manage/scenarios/{id}/inject` 전 구간 200.
- state 주입 후 `scenario`, `scenario_act`, `scenario_sequence`, 엔티티/NPC/Enemy/Item 참조가 일관.
- UUID/인스턴스 ID를 제외한 논리 스키마가 state 기준과 동일.

### Phase C. GM ↔ 기타 서비스 정렬 (state 기준)

1. GM의 state 소비 계약 점검/수정.

- 대상: `services/gm/src/gm/plugins/external/http_client.py`
- 대상: `services/gm/src/gm/core/engine/game_engine.py`
- 조치:
  - snapshot 필드명 정합성 보정(`scenario_entity_id`, relation 필드).
  - 시나리오 전이 시 `update_act/update_sequence` 호출/에러 처리 강화.

2. Scenario 제안값과 GM 반영 경로 정렬.

- `next_act_id`, `next_seq_id`가 유효 ID일 때만 state 업데이트.
- 무효 ID 시 fail-fast + 명확한 로그.

3. GM 스키마/테스트 동기화.

- `services/gm/src/gm/schemas/*`와 실제 외부 응답 파싱 정렬.
- 회귀 테스트 보강(`services/gm/tests/test_rule_integration.py` 중심).

완료 기준

- GM 턴 처리 중 schema mismatch/KeyError/404 없이 진행.
- 전이 발생 턴에서 state의 current_act/current_sequence가 기대대로 변경.

### Phase D. Tester 기반 전체 턴 검증

1. 엔드투엔드 시나리오 실행.

- `PYTHONPATH=tester/src uv run python -m tester.runner [session_id] [max_turns]`
- 기본 10턴 + 확장 20턴 검증.

2. 검증 포인트 체크리스트.

- 생성/주입/세션시작 성공.
- 플레이어 턴 커밋 성공.
- NPC 턴 자동 처리 안정성.
- sequence goal/exit trigger 기반 전이 정상 반영.
- 로그 파일(`test_output_*.log`)에 턴별 상태 스냅샷 누락 없음.

3. 장애 재현성 확보.

- 실패 케이스별 입력/응답/로그를 `logs/`에 저장.
- 재현 커맨드와 원인/조치 문서화.

완료 기준

- 10턴 연속 성공 + 치명 오류(500, commit 실패, state 불일치) 0건.
- 20턴 장기 실행에서 중단 없이 종료(품질 개선 전 기능 기준).

## 3. 작업 순서 요약

1. Phase A: 기동/헬스 정상화
2. Phase B: 시나리오 주입 스키마/그래프 정렬
3. Phase C: GM 소비/전이 경로 정렬
4. Phase D: Tester 10~20턴 검증

## 4. 산출물

- 코드 수정: `scenario-service`, `gm`, `tester/src/tester` 한정
- 계약 테스트 추가/수정: 주입 스키마, ID 참조, 턴 전이
- 실행 로그: `test_output_*.log`
- 최종 보고: 실패 재현 절차 + 해결 내역 + 잔여 리스크

## 5. 확인 필요 사항 (질문)

1. `uuiod`는 `UUID(인스턴스 ID)`를 의미하는 것으로 이해했습니다. 즉 “UUID/인스턴스 키를 제외한 필드/구조 동일성”이 맞습니까?
2. `master_id -> rule_id` 변환 시, 숫자 변환 불가한 값은

- (A) 주입 실패 처리
- (B) 0으로 강등
  중 어느 정책으로 고정할까요? (현재 state는 `rule_id` 정수 전제)

3. 생성 결과의 확장 필드(`summary`, `difficulty`, `genre`, `tags`, `total_acts`)는

- (A) state 주입 payload에서는 제거/무시
- (B) state 쪽 저장 안 되더라도 scenario-service 내부 보존
  중 어떤 방향이 맞습니까?

4. 전체 턴 검증 합격 기준은 우선 10턴 성공으로 둘지, 바로 20턴 성공을 필수로 둘지 확정 부탁드립니다.
