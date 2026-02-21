# 테스터 상세 분석 리포트 (2026-02-08)

## 실행 요약
- 실행 1: `PYTHONPATH=tester/src uv run python -m tester.runner seqeval20 20 three_sequence_combat`
  - 로그: `log/test_output_seqeval20_20260208_175830.log`
  - 결과: 8턴에서 실패 (`502 Bad Gateway`, Scenario context mismatch)
- 실행 2: `PYTHONPATH=tester/src uv run python -m tester.runner seqeval20_retry 20 three_sequence_combat`
  - 로그: `log/test_output_seqeval20_retry_20260208_180038.log`
  - 결과: 1턴에서 실패 (획득 서술 대비 인벤토리 증가 없음)
- 실행 3: `PYTHONPATH=tester/src uv run python -m tester.runner smoke10_latest 10`
  - 로그: `log/test_output_smoke10_latest_20260208_180056.log`
  - 결과: 10턴 완료

## 주요 평가 요소별 분석

## 1) 시퀀스별 등장/퇴장 검증
- 공통적으로 `seq-1 -> seq-2`, `seq-2 -> seq-3` 전이는 관측됨.
  - 근거:
    - `log/test_output_seqeval20_20260208_175830.log:54`
    - `log/test_output_seqeval20_20260208_175830.log:73`
    - `log/test_output_smoke10_latest_20260208_180056.log:183`
    - `log/test_output_smoke10_latest_20260208_180056.log:207`
- 등장/퇴장 이벤트는 의도와 대체로 일치:
  - `seq-1 -> seq-2`: `npc-elder-1` 등장
  - `seq-2 -> seq-3`: `enemy-goblin-1`, `enemy-goblin-2` 등장 / `npc-elder-1` 퇴장
- 중대 이상:
  - 실행 1에서 `seq-3 -> seq-4` 비계약 전이 발생
  - 전이 시 적 2체가 퇴장 처리되었으나, 직후 시퀀스 상태에 적 HP가 남아 있어 모델/상태 간 불일치 징후
  - 근거:
    - `log/test_output_seqeval20_20260208_175830.log:196` (전이 이벤트)
    - `log/test_output_seqeval20_20260208_175830.log:192` (동일 시점 적 HP 존재)

## 2) 시퀀스 타입별 진행 정상성
- 기대 타입 흐름(three_sequence_combat): 탐색(seq-1) -> 상호작용/협상(seq-2) -> 전투(seq-3)
- 관측:
  - 실행 1: 타입 흐름 자체는 충족되었으나, 전투 후 `seq-4`로 이탈하며 실패
  - 실행 2: seq-1에서 즉시 어설션 실패로 타입 진행 평가 불가
  - 실행 3: 탐색/상호작용/전투 시퀀스 전이는 확인되나, 10턴 내 전투 상태(HP) 변화가 없어 전투 진행 실질성 부족
- 판단:
  - 타입 전이 트리거는 작동하지만, 전이 후 계약 보장(유효 시퀀스 범위)과 전투 상태 반영 일관성이 불안정

## 3) 아이템/엔티티 상태 업데이트
- 아이템/인벤토리:
  - 3개 실행 모두 스냅샷 기준 `아이템 목록: 없음`, `인벤토리: 없음`이 지속됨.
  - 실행 2에서는 내러티브가 "열쇠 획득"을 포함했지만 인벤토리 증가가 없어서 러너 어설션 실패.
  - 근거:
    - 실패: `log/test_output_seqeval20_retry_20260208_180038.log:65`
- 엔티티(적) 상태:
  - 실행 1에서 적 HP는 `30 -> 26 -> 21 -> 19 -> 13 -> 7`로 감소하여 전투 반영 확인됨.
  - 실행 3에서는 시퀀스 3 진입 후에도 적 HP가 `30` 고정으로 유지되어 전투 상태 반영 불충분.
  - 근거:
    - 감소 트레일: `log/test_output_seqeval20_20260208_175830.log`의 `:92, :116, :138, :166, :192`
    - 고정 트레일: `log/test_output_smoke10_latest_20260208_180056.log`의 `:203, :233`

## 실패 원인 정리
- 실패 A (실행 1): 비계약 시퀀스 전이
  - 증상: `seq-4` 전이 후 `check_scenario`에서 `Sequence seq-4 not found in act act-1`
  - 에러: BE-router 502 + PipelineError
  - 근거: `log/test_output_seqeval20_20260208_175830.log:214`
- 실패 B (실행 2): 내러티브-상태 불일치
  - 증상: 획득 서술이 있었으나 인벤토리 증가 없음
  - 에러: 러너 상태 일관성 어설션 실패
  - 근거: `log/test_output_seqeval20_retry_20260208_180038.log:65`

## 종합 판단
- 현재 테스터 기준에서 "항상 안정적"이라고 보기 어려움.
- 시퀀스 전이와 상태 업데이트가 실행마다 다른 양상을 보이며, 특히 아래 2가지가 핵심 리스크:
  - 시퀀스 계약 범위 이탈(`seq-4`)
  - 내러티브 기반 사건(획득/전투)과 상태 DB 반영의 불일치

## 권장 조치
1. GM 시퀀스 전이 결과를 state-manager 시퀀스 목록과 강제 대조하고, 불일치 시 전이 롤백/무시.
2. "아이템 획득" 내러티브 생성 전 상태 커밋 성공 여부를 확인하는 게이트 추가.
3. 테스터 리포트에 `state_diff`/`commit_id`를 함께 기록해 내러티브-상태 불일치의 원인 위치를 즉시 식별하도록 개선.
