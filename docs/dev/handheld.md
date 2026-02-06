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
    - Graph (State/Scenario): `15432 -> 5432` (`postgres-graph`)
    - Play (Logs/RAG): `15433 -> 5432` (`postgres-play`)
    - Rule (User/Session): `15434 -> 5432` (`postgres-rule`)
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
- **Split DB Architecture**:
  - `Graph DB`: Apache AGE 기반. `state-manager`, `scenario-service`가 참조.
  - `Play DB`: `pgvector` 기반. `gm`이 플레이 로그 적재 및 RAG용으로 사용.
  - `Rule DB`: 유저 정보 및 세션 매핑 관리. `BE-router`, `rule-engine` 등이 참조.
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
- 다음 갱신 우선순위:
  1. 시나리오 주입 스키마 정렬 완료 시 본 문서의 "gotchas" -> "resolved"로 승격
  2. `transition_session` 구현 완료 시 플로우/대시보드 업데이트
  3. 통합 테스트 기준(10/20턴) 확정 후 검증 절차 고정
<!-- PROJ_WORKNOTES_END -->