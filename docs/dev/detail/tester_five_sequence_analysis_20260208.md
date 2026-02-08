# 5시퀀스 평가 시나리오 테스트 분석 (2026-02-08)

## 테스트 구성
- 주입 시나리오: `TST_FIVE_SEQUENCE_EVALUATION_V1`
- 구성 요구 충족:
  - 아이템 5개, NPC 5개, 적 5개, 시퀀스 5개
  - payload: `tester/src/tester/scenario_payloads/five_sequence_evaluation.inject.json`
- 주입(예외 경로): `tester.seed_profile` -> scenario-service debug inject-save
- 테스트 경로(주입 외): BE-router 경유
  - 세션 시작: `/state/session/start`
  - 턴 처리: `/gm/turn`
  - 상태 조회: `/state/session/*`
  - 근거 코드: `tester/src/tester/client.py`

## 실행 커맨드
1. 주입
```bash
PYTHONPATH=tester/src uv run python -m tester.seed_profile five_sequence_evaluation
```

2. 테스트 실행
```bash
PYTHONPATH=tester/src uv run python -m tester.runner fiveeval25 25 five_sequence_evaluation
```

3. 로그
- `log/test_output_fiveeval25_20260208_180727.log`

## 결과 요약
- 테스트는 11턴에서 세션 종료(`status=ended`)로 완료.
- 5개 시퀀스 전이 모두 관측됨:
  - `seq-1 -> seq-2` (`log/test_output_fiveeval25_20260208_180727.log:56`)
  - `seq-2 -> seq-3` (`log/test_output_fiveeval25_20260208_180727.log:75`)
  - `seq-3 -> seq-4` (`log/test_output_fiveeval25_20260208_180727.log:94`)
  - `seq-4 -> seq-5` (`log/test_output_fiveeval25_20260208_180727.log:113`)
- 종료 검증 통과:
  - `log/test_output_fiveeval25_20260208_180727.log:256`

## 평가 요소별 분석

## 1) 시퀀스별 등장/퇴장
- 전이 로그가 매 단계 기록되어 시퀀스 이동은 정상 확인.
- 다만 등장/퇴장 엔티티가 payload 설계와 1:1 매칭되지 않고, 중복 엔티티가 관측됨.
  - 예: 초기 상태에서 NPC/적 ID가 중복 반복
  - 근거:
    - NPC: `log/test_output_fiveeval25_20260208_180727.log:26`
    - Enemy: `log/test_output_fiveeval25_20260208_180727.log:27`

## 2) 시퀀스 타입별 진행(탐색/수집/협상/잠입/전투)
- 프로파일 액션과 목표/트리거 기준으로 5개 타입 흐름은 진행됨.
  - seq-1 탐색 -> seq-2 수집 -> seq-3 협상 -> seq-4 잠입 -> seq-5 전투
- seq-5에서 반복 전투/서술 루프 후 종료로 이어짐.

## 3) 아이템/엔티티 상태 업데이트
- 엔티티(적) HP 업데이트는 부분적으로 반영됨:
  - 예: `HP 30 -> 28 -> 18 -> 9 -> 5 -> 2`
  - 근거:
    - `log/test_output_fiveeval25_20260208_180727.log:130`
    - `log/test_output_fiveeval25_20260208_180727.log:148`
    - `log/test_output_fiveeval25_20260208_180727.log:168`
    - `log/test_output_fiveeval25_20260208_180727.log:210`
    - `log/test_output_fiveeval25_20260208_180727.log:232`
- 아이템/인벤토리 업데이트는 미관측:
  - 전 턴에서 `아이템 목록: 없음`, `인벤토리: 없음` 유지
  - 근거:
    - 초기: `log/test_output_fiveeval25_20260208_180727.log:28`
    - 종료 전: `log/test_output_fiveeval25_20260208_180727.log:253`, `log/test_output_fiveeval25_20260208_180727.log:254`

## 발견 이슈
1. 엔티티 중복 노출
- 동일 ID NPC/적이 상태 스냅샷에 중복으로 노출되어 전이/전투 판정 해석을 어렵게 만듦.

2. 아이템 파이프라인 미반영
- payload에 아이템이 정의되어 있으나 상태 조회 경로에서 노출/획득 반영이 되지 않음.

3. 전투 상태 불일치 가능성
- 일부 동일 ID 엔티티가 HP 30과 HP 감소본이 동시에 존재하여 단일 소스 정합성 의심.

## 결론
- 요청한 형태의 5시퀀스 평가 시나리오 생성/주입/BE-router 경유 테스트는 수행 완료.
- 시퀀스 전이는 5단계 모두 확인되었으나, 엔티티/아이템 상태 정합성(중복/미반영) 문제로 평가 신뢰도는 제한적.
