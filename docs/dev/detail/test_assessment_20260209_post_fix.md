# 테스트/구조 평가 보고서 (2026-02-09, post-fix)

## 1) 실행 범위
- 유닛 테스트 커버리지 (BE-router, rule-engine 제외)
  - `services/gm`: `87%`
  - `services/state-manager`: `84%` (`143 passed`)
  - `services/scenario-service`: `81%`
  - `services/llm-gateway`: `82%`
- 테스터 E2E (BE-router 경유)
  - 프로필: `six_sequence_three_act_eval`
  - 시나리오: 3 Act / 6 Sequence / NPC 5 / Enemy 5 / 아이템 8(필수 6 + 시작 2)
  - 최종 런: `log/test_output_final-sixseq-20260209_20260209_013440.log`
  - sequence_type 재검증 런: `log/test_output_seqtype_eval_short_20260209_20260209_020255.log`

## 2) 정상 동작 확인
- 시나리오 상세 로드
  - `GET /state/scenario/{id}` 500 해소.
  - `acts/sequences/npcs/enemies` 정상 노출.
  - 시퀀스별 `items` 매핑 정상 노출 (`seq-1/2/3/4/6`).
- 테스터 시나리오 명세 표시
  - 시퀀스별 아이템 목록이 빈 값이 아닌 실제 ID로 표시됨.
- 시작 인벤토리
  - 포션/철검 지급 정상 (`starter_loadout rule_ids=[7901,7902]`).
- 시퀀스 전이/등장·퇴장
  - `seq-1 -> seq-2 -> seq-3 -> seq-4 -> seq-5 -> seq-6` 전이 로그 확인.
  - 각 전이마다 등장/퇴장 엔티티 + 시퀀스 아이템 등장/퇴장 로그 확인.
- 종료 판정
  - 최종 런에서 `status=ended`, `current_turn=20`, `current_sequence_id=seq-6` 확인.
  - 종료 시점 현재 시퀀스 적 5체 모두 `HP=0`, `is_defeated=true` 확인.
- sequence_type 기반 판정 컨텍스트
  - `scenario_sequence.metadata.sequence_type`가 state-manager에 저장/조회됨.
  - GM -> RuleEngine로 `sequence_type` 전달 확인.
  - RuleEngine 로그에서 `sequence_type hint applied: EXPLORATION/NEGO/COMBAT` 확인.
  - seq-6 전투 구간에서 적 HP 감소(`30 -> 27`) 확인.
- 종료 게이트 보강 결과
  - 실행 로그: `log/test_output_endgate_eval_20260209_20260209_022741.log`
  - seq-6에서 적 HP `5` 구간(`turn 10`)에는 종료되지 않음(`status=active` 유지).
  - 적 HP가 전원 `0`이 된 직후(`turn 11`) `status=ended`로 정상 종료.
  - 장기 회귀(`require_session_end=true`) 3회 결과:
    - `log/test_output_endgate_reg_1_1770571910_20260209_023151.log` (`ended`, 13턴)
    - `log/test_output_endgate_reg_2_1770572085_20260209_023445.log` (`ended`, 11턴)
    - `log/test_output_endgate_reg_3_1770572247_20260209_023727.log` (`ended`, 11턴)
    - 공통: 종료 시점 `alive_enemies_in_current_sequence=0`

## 3) 부족한 부분
- 장기 러너(20턴)에서 `seq-6` 반복 시나리오가 여전히 재현됨.
  - 내러티브는 “처치/안정화”를 반복하나, 세션 `status=active` 유지 케이스 존재.
- 러너 최종 요약(JSON)에는 “현재 시퀀스 생존 적 수”가 별도 고정 필드로 제공되지 않음.

## 4) 잠재 문제
- `gm/summary` 호출 `ReadTimeout` 간헐 발생 이력 존재(재시도 시 정상).
  - 오프닝 단계 단일 실패가 전체 러너 중단으로 연결될 수 있어 안정성 리스크.
- `should_end`/트리거 문구와 실제 전투 상태(적 생존, HP>0)의 불일치 가능성.
  - 상태 기반 종료 게이트가 약하면, 조기 종료 또는 무한 반복 양쪽 리스크가 남음.

## 5) 구조적 리스크
- 상태판정 소스가 분산됨
  - `narrative`, `rule-engine 판단`, `state-manager DB 상태`가 서로 다른 타이밍으로 갱신되어
    종료/전이 근거가 일시적으로 불일치할 수 있음.
- 아이템 모델 이원화
  - 시나리오 선언(`scenario_item_id`)과 런타임 상태(`item_id`, `rule_id`) 간 변환 단계가 많아
    직렬화/매핑 오류가 재발하기 쉬운 구조.

## 6) 권장 후속 작업
1. `gm/summary`에 재시도(백오프) + 타임아웃 상향 + 실패 시 대체 경로(최근 턴 요약) 추가.
2. 종료 게이트를 상태기반으로 강제: `should_end=true`라도 현재 시퀀스 적 생존 시 종료 차단.
3. 러너 결과 스키마에 `alive_enemies_in_current_sequence` 필드를 추가해 회귀 판정 자동화.

## 7) plan_0028 추가 검증 결과 (2026-02-09)
- 변경 요약
  - GM 서사 가드레일을 강화하여, 생존 적 존재 시 종료/완료 서사를 재시도 후에도 허용하지 않도록 안전 문장 fallback을 도입.
  - LLM 컨텍스트에 적 HP/격파 여부를 포함해 상태 참조성을 강화.
- 단위 테스트
  - `services/gm/tests/test_narrative_guardrails.py`: `3 passed`
  - `tests/test_plan_0003_contract_alignment.py tests/test_pipeline_precision.py tests/test_game_summary.py`: `18 passed` (기존 warning 1건)
- E2E (BE-router 경유)
  - 실패 런(일시 503): `log/test_output_narrative_guard_eval_20260209_c_20260209_025455.log`
  - 최종 성공 런: `log/test_output_narrative_guard_eval_20260209_d_20260209_025824.log`
    - seq-6에서 적 HP>0 동안 종료 문구 미출력, 안전 문장만 출력.
    - 적 HP 전원 0 이후 `"모험은 끝이 났다."` 출력 및 세션 종료 확인.
  - 구조 분리 검증 런(전이 조건 비노출): `log/test_output_no_trigger_prompt_eval_20260209_retry_20260209_031540.log`
    - GM 생성 컨텍스트에서 `exit_triggers`/`narrative_slot` 강제 제거 후에도 시퀀스 전이 정상.
    - 종료 문구는 `session ended + 적 전원 0` 시점에서만 출력됨.
- 잔존 리스크
  - 정합성 우선 fallback으로 인해 전투 중 나레이션 표현 다양성이 낮아짐(품질 영역 개선 필요).
