# Handheld

<!-- PROJ_UNDERSTANDING_BEGIN -->
## Project Understanding
### What this project is
- **GTRPGM**: LLM 기반 TRPG 진행을 위한 마이크로서비스 플랫폼.
- **핵심 구조**:
  - `BE-router`: 외부 진입점(API Gateway, 인증/중계)
  - `gm`: 턴 오케스트레이션(룰/시나리오/상태/서술 통합)
  - `rule-engine`: 룰 판정, 상태 diff 제안 (전투/대화/탐험 등 페이즈별 노드 실행)
  - `scenario-service`: 시나리오 생성/검증/주입
  - `state-manager`: 상태 SOT(SQL + Apache AGE 그래프)
  - `llm-gateway`: Gemini/OpenAI 공통 호출 계층
  - `WEB`: 프론트엔드

### Architecture link
- <!-- PROJ_ARCH_LINK -->docs/dev/architect/architecture_v0.1.0.md

### Repository map (핵심)
- `docker-compose.local.yml`: 로컬 통합 실행 정의
- `bin/project`: 통합 실행 래퍼(`up/down/ps/logs/build`)
- `services/`: 서브모듈 서비스 루트(`BE-router`, `gm`, `state-manager`, `scenario-service`, `rule-engine`, `llm-gateway`, `WEB`)
- `tester/src/tester/`: 시나리오 생성~턴 루프 E2E 러너
- `docs/global-plan.md`, `todo.md`: 상위 설계/정합성 TODO

### Current priorities
- `[P0]` BE-router 경유 전체 게임 진행 플로우 정상 동작 검증
- `[P1]` NPC/적 턴 `dialogue` 필드 제공(행동은 응답 미노출, 나레이션 입력으로만 사용)
- `[Investigating]` 플레이어-NPC 관계 미생성 원인 파악 (rule-engine 로직 이슈 의심)

### Runtime topology (local compose)
- External ports:
  - BE-router `18010 -> 8010`
  - GM `18020 -> 8020`
  - State Manager `18030 -> 8030`
  - Scenario Service `18040 -> 8040`
  - Rule Engine `18050 -> 8050`
  - LLM Gateway `18060 -> 8060`
  - Web `18080 -> 8080`
  - Postgres: `15432 -> 5432` (통합, 논리 분리)
  - Redis `16379`

### How to run
- 전체 스택 (권장):
  ```bash
  ./bin/project up
  ./bin/project ps
  ```
- 소스 수정 후 재빌드:
  ```bash
  ./bin/project build <service_name>
  ./bin/project up  # 변경 사항 반영하여 재시작
  ```
- 로그 확인:
  ```bash
  ./bin/project logs -f <service_name>
  ```
- 종료:
  ```bash
  ./bin/project down
  ```

### Health checks
- `GET /health` on ports `18010` ~ `18060`.

### Core request flows
- 플레이어 턴:
  1. Client -> `BE-router` -> `GM`
  2. GM -> State snapshot 조회 -> `Rule Engine` (판정)
  3. Rule Engine -> `Scenario Service` (검증) -> `State Manager` (Commit)
  4. GM -> LLM (Narrative) -> Response

### How to test
- 서비스별 단위 테스트 (각 서비스 루트에서):
  ```bash
  uv run pytest tests/
  ```
- 통합 턴 테스트 (루트에서):
  ```bash
  PYTHONPATH=tester/src uv run python -m tester.runner <session_id> <max_turns>
  ```

### Conventions / gotchas
- **Rule Engine - Relationship Issue**:
  - `dialogue_node.py` 분석 결과, 요청에 포함된 관계(`state.request.relations`)가 존재해야만 `target_npc_state_id`를 식별하고 우호도를 업데이트함.
  - **초기 만남 시 관계가 없으면(None) 관계 생성 로직을 타지 않고 로그만 남김("대화할 NPC를 찾을 수 없어...").** 이로 인해 신규 NPC와의 관계가 생성되지 않는 현상 발생 추정.
- **DB 구성**: 단일 Postgres 컨테이너 내 논리적 DB 분리 사용.
- **Migration**: `db/migration/run_migration.sh` 사용.
<!-- PROJ_UNDERSTANDING_END -->

<!-- PROJ_WORKNOTES_BEGIN -->
## Work Notes by Detail
- `2026-02-06`: 루트 `docs/dev` 문서를 코드베이스 실상(다중 서비스/실제 엔드포인트/실행 커맨드) 기준으로 정리.
- `2026-02-07`: 우선순위 재정렬. 정상 동작 검증(`plan_0012`)을 최우선으로 승격, DB 분리(`plan_0008`)는 최하순위로 이관.
- `2026-02-09`: DB 분리 목표를 "논리 분리"로 확정.
  - `plan_0008`은 `deprecated`로 전환.
  - 현행 기준은 단일 Postgres 클러스터 내 서비스별 DB/권한/확장 분리 유지.
- `2026-02-09`: 리모트 운영 환경 이슈 정리.
  - `state-manager`: `REDIS_PORT`가 빈 문자열로 주입되면 부팅 중 `int('')` 파싱으로 크래시하며 재시작 루프에 빠짐. (운영 compose/env 주입 시 필수값 보장 필요)
  - `scenario-service` debug inject/save: AGE `cypher()` 호출 시 graph/query/params 타입 캐스팅 누락으로 `cypher(...) does not exist` / `type agtype does not exist` 계열 오류가 발생할 수 있음.
  - `scenario-service` 시나리오 생성: LLM 응답이 엄격 스키마(`PlannerOutput`) 필수 필드를 누락하면 `pydantic ValidationError`로 500이 발생. (생성 노드 리트라이/수정-재요청/스키마 완화 등 보강 필요)
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
- `2026-02-09`: `plan_0030` 완료.
  - `docs/dev/architect/architecture_v0.1.0.md` 생성: 전체 서비스/DB 구조도 및 서비스별 내부 아키텍처 포함.
  - 서비스 경로 확인: `services/` 내부가 아니라 프로젝트 루트(`BE-router`, `gm`, `rule-engine` 등)가 실제 소스 위치임.
- `2026-02-10`: `plan_0031` 완료.
  - **문제 원인**: GM Service의 `TurnContext` (TypedDict)에 `final_relations` 필드가 누락되어, LangGraph 상태 전이 시 해당 정보가 유실되는 버그 확인.
  - **조치**: `TurnContext` 스키마 보강 및 Rule Engine/GM/State Manager 전 구간 관계 형성 유닛 테스트 추가/검증 완료.
- `2026-02-10`: `plan_0032` 완료.
  - **작업 내용**: NPC/적 엔티티의 관계 기반 아이템 소유 및 드롭 시스템 구현.
  - **핵심 조치**:
    - `state-manager`: SQL `npc`, `enemy` 테이블에 `owned_items` 컬럼 추가 및 세션 시작 시 그래프 자동 동기화 트리거(`L_entity_inventory.sql`) 구현.
    - `state-manager`: 엔티티 비활성화(`defeat_enemy`, `depart_npc`) 시 소유 아이템을 필드(Sequence)로 드롭하는 로직 구현.
    - `scenario-service`: 주입 모델 및 LLM 프롬프트에 아이템 소유 구조 반영.
- 다음 갱신 우선순위:
  1. BE-router 경유 정상 동작 게이트(`plan_0012`) 구축/고정
  2. 턴-상태 정합성 부정 케이스(불가능 행동 거절/상태 불변) 자동 검증 강화
  3. DB 물리 분리 필요성 재발생 시 신규 플랜으로 별도 기안
<!-- PROJ_WORKNOTES_END -->
