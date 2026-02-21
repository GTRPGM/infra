# tester_six_sequence_analysis_20260208

## 범위
- 요청 기준:
  - 3 act / 6 sequence 시나리오
  - 플레이어 시작 장비(포션+무기)
  - 필수 아이템 5종 이상
  - NPC 5명(각 2개 이상 아이템), 적 5명(각 2개 이상 아이템)
  - 시나리오 주입 외 테스트는 BE-router 경유
  - 테스터 완주 및 단계별 상태 업데이트 검증

## 시나리오 구성 점검 (정적)
- 대상 페이로드: `tester/src/tester/scenario_payloads/six_sequence_three_act_eval.inject.json`
- 점검 결과:
  - acts: 3
  - sequences: 6
  - npcs: 5
  - enemies: 5
  - items: 8 (starter 2 + essential 6)
  - NPC owns 최소치: 2
  - Enemy owns 최소치: 2

## 실행 이력
1. 1차 실행 실패 (사전 결함 발견)
- 로그: `log/test_output_sixacteval30_20260208_191725.log`
- 실패 원인:
  - `PUT /state/inventory/update`가 BE-router에 없어 404
  - 오류: `httpx.HTTPStatusError: 404 Not Found`

2. 보완 후 재실행
- BE-router에 `PUT /state/inventory/update` 프록시 추가
  - `services/BE-router/src/state/dtos/state_dtos.py`
  - `services/BE-router/src/state/state_router.py`
- 시나리오 주입:
  - `PYTHONPATH=tester/src uv run python -m tester.seed_profile six_sequence_three_act_eval`
  - scenario id: `13feeeb2-00c4-48c6-8f5a-830f75348118`
- 테스터 실행:
  - `PYTHONPATH=tester/src uv run python -m tester.runner sixacteval30 30 six_sequence_three_act_eval`
  - 로그: `log/test_output_sixacteval30_20260208_192019.log`
  - 결과: 30턴 완주(오류 중단 없음), 총 496.45초

## 평가 결과
### 1) 시퀀스별 등장/퇴장 및 전이
- 관측된 고유 경로:
  - `act-1/seq-1 -> act-1/seq-2 -> act-2/seq-3 -> act-2/seq-4`
- 관측 전이:
  - `seq-1 -> seq-2`
  - `seq-2 -> seq-3`
  - `seq-3 -> seq-4`
- 미충족:
  - `seq-5`, `seq-6` 진입 없음
  - 30턴 동안 `seq-4` 고착

### 2) 시퀀스 타입별 정상 진행
- 내러티브는 탐색/잠입 문장 반복으로 생성되나, 상태 전이와 동기화되지 않음.
- `seq-4`의 exit trigger 문구를 행동에 지속 포함했음에도 전이 미발생.
- 결론: 타입별 "서술"은 있으나 "상태 전이 기반 진행"은 실패.

### 3) 아이템/엔티티 상태 업데이트
- 엔티티:
  - `npcs`/`enemies` 조회는 가능하며 `current_hp`는 고정값 유지(100/30).
  - defeated/퇴장 상태 변화 미관측.
- 아이템:
  - `GET /state/session/{session_id}/items`는 8개 아이템 반환.
  - `GET /state/session/{session_id}/inventory`는 빈 배열 지속.

## 인벤토리/아이템 미반영 원인 분석
### A. 테스터 표시 로직의 스키마 불일치(관측 결함)
- `inventory` 응답은 배열(`list[dict]`)인데, 러너 로깅은 dict의 `items` 키를 기대함.
- 위치: `tester/src/tester/runner.py` (`_log_state_snapshot`, `_inventory_item_ids`)
- 영향:
  - 실제 데이터가 있어도 로그에 `인벤토리: 없음`으로 표시될 수 있음.

### B. 실제 상태 반영 자체도 실패(기능 결함)
- `PUT /state/inventory/update`는 성공 응답을 반환:
  - 예: `{\"player_id\":\"...\",\"item_id\":7901,\"quantity\":1}`
- 그러나 직후 조회 결과:
  - `GET /state/session/{session_id}/inventory` => `[]`
  - `GET /state/player/{player_id}` => `player.items: []`
- 해석:
  - 업데이트 응답과 조회계(SOT read model) 간 정합성 결함 가능성 높음.

### C. item ownership relation과 player inventory의 분리
- 시나리오 `relations (owns)`는 엔티티 관계 그래프이며 플레이어 인벤토리와 동일하지 않음.
- 따라서 NPC/적의 소지 아이템 정의만으로 플레이어 인벤토리가 채워지지 않음.

### D. 관계 데이터 중복 누적(구조 결함)
- `seq-4`의 `entity_relations`:
  - total 32, unique 3
  - 동일 `owns` 관계가 다중 중복
- 영향:
  - 상태/컨텍스트 오염 가능성
  - 전이 판정/추론 품질 저하 가능성

## 현재 구조가 목적 달성에 일으키는 문제
1. 쓰기 성공 응답과 읽기 조회값 불일치
- 인벤토리처럼 핵심 상태가 write/read 분리로 일관되지 않으면 테스터 기준 "정상 진행" 판정 불가.

2. 내러티브 중심 진행과 상태 전이 조건의 결합 약함
- trigger 문구를 반복해도 상태 전이가 없어서 장기 고착이 발생.

3. 동일 엔티티 다중 스폰/중복 관계 축적
- 시퀀스별 재배치 과정에서 중복 개체/관계가 늘어나 상태 해석이 어려워짐.

4. 테스터 관측 모델과 API 계약 불일치
- 배열/객체 스키마 차이로 로그/어설션이 실제 상태를 왜곡할 수 있음.

## 개선 우선순위 (제안)
1. State-manager 인벤토리 write/read 정합성 우선 복구
- `inventory/update` 직후 `session inventory`, `player.items`가 동일 소스에서 보이도록 정렬.

2. 테스터 inventory 파싱 보정
- `inventory`가 list/dict 모두 처리하도록 수정하고, rule_id/item_id 기준 집계 지원.

3. 시퀀스 전이 관문 계측 추가
- `exit_trigger matched 여부`, `sequence transition rejection reason`를 상태 API/로그로 노출.

4. 관계 중복 방지
- 동일 `(from_id, to_id, relation_type)` upsert 또는 dedupe 적용.
