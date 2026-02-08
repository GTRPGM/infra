# Handheld

<!-- PROJ_UNDERSTANDING_BEGIN -->
## Project Understanding
### What this project is
- **GTRPGM**: LLM 기반 TRPG 진행을 위한 마이크로서비스 플랫폼.
- **핵심 구조**:
  - `BE-router`: 외부 진입점(API Gateway, 인증/중계)
  - `gm`: 턴 오케스트레이션(룰/시나리오/상태/서술 통합)
  - `rule-engine`: 룰 판정, 상태 diff 제안
  - `scenario-service`: 시나리오 생성/검증/주입
  - `state-manager`: 상태 SOT(SQL + Apache AGE 그래프)
  - `llm-gateway`: Gemini/OpenAI 공통 호출 계층
  - `WEB`: 프론트엔드

### Architecture link
- <!-- PROJ_ARCH_LINK -->docs/dev/architect/architecture_v0.0.0.md

### Repository map (핵심)
- `docker-compose.local.yml`: 로컬 통합 실행 정의
- `bin/project`: 통합 실행 래퍼(`up/down/ps/logs/build`)
- `services/`: 서브모듈 서비스 루트(`BE-router`, `gm`, `state-manager`, `scenario-service`, `rule-engine`, `llm-gateway`, `WEB`)
- `tester/src/tester/`: 시나리오 생성~턴 루프 E2E 러너
- `docs/global-plan.md`, `todo.md`: 상위 설계/정합성 TODO

### Current priorities
- `[P0]` BE-router 경유 전체 게임 진행 플로우 정상 동작 검증
  - 범위: 로그인 -> 시나리오 선택 -> 세션 생성 -> 세계 상태 요약 -> 턴 진행
  - 기준: 엔드포인트 목적 적합성 + 턴/상태 반영 정합성
- `[P9 - 최하순위]` `plan_0008` DB 분리/마이그레이션 재정렬

### Runtime topology (local compose)
- External ports:
  - BE-router `18010 -> 8010`
  - GM `18020 -> 8020`
  - State Manager `18030 -> 8030`
  - Scenario Service `18040 -> 8040`
  - Rule Engine `18050 -> 8050`
  - LLM Gateway `18060 -> 8060`
  - Web `18080 -> 8080`
  - Postgres:
    - 통합 Postgres: `15432 -> 5432` (`postgres`)
    - 참고: Graph/Play/Rule 분리는 `plan_0008`로 이관된 상태이며 현재 로컬 compose에는 반영되지 않음
  - Redis `16379`

### How to run
- 전체 스택:
  ```bash
  ./bin/project up
  ./bin/project ps
  ```
- 로그 확인:
  ```bash
  ./bin/project logs gm
  ./bin/project logs state-manager
  ```
- 종료:
  ```bash
  ./bin/project down
  ```

### Health checks
- `GET /health`:
  - `http://localhost:18010/health` (BE-router)
  - `http://localhost:18020/health` (GM)
  - `http://localhost:18030/health` (State)
  - `http://localhost:18040/health` (Scenario)
  - `http://localhost:18050/health` (Rule)
  - `http://localhost:18060/health` (LLM Gateway)

### Core request flows
- 플레이어 턴:
  1. Client -> `BE-router /gm/turn`
  2. BE-router -> `GM /api/v1/game/turn`
  3. GM -> State snapshot 조회
  4. GM -> Rule Engine `/play/scenario`
  5. GM -> Scenario Service `/api/v1/check/validate`
  6. GM -> State Manager `/state/commit` (+ act/sequence 전이 API)
  7. GM -> LLM Gateway로 narrative 생성
  8. GM PlayLog 저장 후 응답
- NPC 턴:
  - GM이 동일 파이프라인을 자동 재실행하되, actor 선택(`npc`/`narrator`) 및 NPC 입력 생성 노드 포함
- 시나리오 생성/주입:
  1. Scenario Service `/api/v1/generation/pure|grounded|informed`
  2. `/api/v1/manage/scenarios/{scenario_id}/inject`
  3. 내부적으로 State Manager `/state/scenario/inject` 호출

### How to test
- 서비스별 단위 테스트(각 서비스 루트에서):
  ```bash
  uv run pytest tests/
  ```
- 통합 턴 테스트(루트):
  ```bash
  PYTHONPATH=tester/src uv run python -m tester.runner <session_id> <max_turns>
  ```

### Conventions / gotchas
- **DB 구성(현행)**:
  - 현재 `docker-compose.local.yml`은 단일 `postgres` 컨테이너를 사용.
  - DB 분리(Graph/Play/Rule)는 `plan_0008`로 추적 중이며 최하순위 작업.
- **Migration**: `db/migration/run_migration.sh <dump_file>`을 통해 기존 통합 덤프를 자동으로 분할하여 각 DB에 주입 가능.
- **State API prefix**: 대부분 `/state/*` 경로 사용 (`state-manager`가 라우터 등록 시 prefix 부여)
- **Commit 입력 규약**: GM은 `turn_id = "{session_id}:{seq}"` 형식으로 커밋
- **Scenario 주입 규약**: State 기준은 `rule_id` 정수 + `scenario_*_id` 문자열 규약
- **Schema mismatch 리스크**:
  - Scenario Service 내부 모델(`master_id`, `item_id`)과 State 주입 스키마(`rule_id`, `scenario_item_id`) 간 변환이 핵심 리스크
- **Session 0 템플릿**: `00000000-0000-0000-0000-000000000000` 세션 데이터가 복제/주입 기준
- **LLM 키 필요**: `OPENAI_API_KEY`/`GOOGLE_API_KEY` 미설정 시 관련 호출 실패 가능
- **현재 미구현**: Scenario Service `POST /api/v1/manage/sessions/transition`
<!-- PROJ_UNDERSTANDING_END -->

<!-- PROJ_WORKNOTES_BEGIN -->
## Work Notes by Detail
- `2026-02-06`: 루트 `docs/dev` 문서를 코드베이스 실상(다중 서비스/실제 엔드포인트/실행 커맨드) 기준으로 정리.
- `2026-02-07`: 우선순위 재정렬. 정상 동작 검증(`plan_0012`)을 최우선으로 승격, DB 분리(`plan_0008`)는 최하순위로 이관.
- `2026-02-07`: 종료 검증 보강.
  - `scenario-service`: act context 시퀀스 정렬 고정, 역전이 차단, terminal-trigger 시 `should_end=true` 반환.
  - `gm`: `should_end=true` 수신 시 `state/session/{id}/end` 호출, 종료 턴 내 마무리 문구 강제.
  - `tester`: 시퀀스 진동(ABAB) 루프 감지 어설트 추가.
- `2026-02-07`: 실환경 러너 검증에서 외부 의존 불안정 관측.
  - `llm-gateway` 500, rule/scenario timeout, 일시적 `state/commit` 404로 턴 실패 케이스 존재.
- `2026-02-07`: 정상 동작 우선 경로 재검증 완료(3-시퀀스).
  - 수정:
    - `gm`: 플레이어 턴에서 시퀀스 전환이 발생한 경우 같은 턴의 NPC 자동 턴을 스킵(새 시퀀스 조기 종료 방지).
    - `gm`: `should_end` 수신 시 NPC 턴 스킵 로직과 병행하여 세션 종료 분기 안정화.
    - `tester`: `setup_session`에서 시나리오 선택 우선순위를 `pinned_id > exact_title > hint`로 고정.
  - 결과:
    - `seq-1 -> seq-2 -> seq-3` 전이 검증 성공
    - 전이별 등장/퇴장 검증 성공
    - 마지막 시퀀스에서 `status=ended` + 마무리 문구(`모험은 끝이 났다.`) 확인
    - 실행 로그: `test_output_three_seq_final_retry6_20260207_20260207_145524.log`
- `2026-02-07`: 전투 상태 반영 경로 보강 및 재검증.
  - 수정:
    - `rule-engine/combat_node`: 적대 relation 누락 시 요청 enemy 전체를 전투 대상으로 폴백.
    - `rule-engine/combat_node`: 적 상세 조회 실패 시 기본 난이도(6) 폴백으로 diff 생성 중단 방지.
    - `gm/http_client`: `rule_id <= 0`일 때 `scenario_*_id` 기반 entity_id 파싱 폴백.
    - `tester/runner`: 상태 로그에서 `current_hp` 우선 출력(전투 HP 변동 가시성 개선).
  - 검증:
    - E2E 실행: `PYTHONPATH=tester/src uv run python -m tester.runner smoke-combat3 18 three_sequence_combat`
    - 결과: 3턴 종료(`status=ended`) + `state_diff`에 enemy HP diff 생성 확인
    - 세션 조회 결과: 고블린 2체 HP `30 -> 24` 반영 확인
  - 잔여 이슈:
    - 종료 조건이 "적 전원 처치" 상태와 직접 연동되지 않아, 적 생존 상태에서도 `should_end`로 종료될 수 있음(후속 보완 필요).
- `2026-02-07`: 종료 조건-전투 상태 결합 보강.
  - 수정:
    - `gm/commit_state`: `scenario.should_end=true` 수신 시 즉시 종료하지 않고,
      최신 `get_state + get_sequence_details`를 합쳐 현재 시퀀스의 생존 적 존재 여부를 재검증.
    - 생존 적 존재 시 `end_session` 보류 + `scenario.should_end=false`로 다운그레이드(조기 종료/종료 문구 강제 방지).
    - 생존 적이 없을 때만 `end_session` 수행.
  - 테스트:
    - `services/gm/tests/test_plan_0003_contract_alignment.py` (6 passed)
  - E2E:
    - `PYTHONPATH=tester/src uv run python -m tester.runner smoke-combat5 18 three_sequence_combat`
    - 결과: 3턴 조기 종료 제거, 적 HP 단계 감소 후 전원 제거 시점(10턴)에서 `status=ended`, enemies `[]` 확인.
- 다음 갱신 우선순위:
  1. BE-router 경유 정상 동작 게이트(`plan_0012`) 구축/고정
  2. 턴-상태 정합성 부정 케이스(불가능 행동 거절/상태 불변) 자동 검증 강화
  3. `plan_0008` 재정렬은 상기 항목 완료 후 착수
<!-- PROJ_WORKNOTES_END -->
