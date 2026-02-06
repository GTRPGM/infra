# Architecture v0.0.0

## Summary
- 현재 저장소는 **AI TRPG 진행용 MSA**로 구성되어 있으며, GM 오케스트레이션 + 상태 저장소 분리를 중심으로 동작한다.
- 실행 기준은 `docker-compose.local.yml` + `bin/project`이며, 서비스 간 HTTP 호출로 턴 파이프라인을 연결한다.

## Context
- 목적: 플레이어 자연어 입력을 룰 판정/시나리오 제약/상태 커밋/서술 생성의 일관된 턴 처리로 변환.
- 제약:
  - 상태 반영은 `state-manager`를 단일 SOT로 사용.
  - GM은 턴마다 단일 파이프라인을 실행하고 로그를 저장.
  - LLM 호출은 `llm-gateway`를 통해 표준화.

## System overview
- **코드 레이아웃**: 서비스 코드는 `services/*`, 테스트 에이전트 코드는 `tester/src/tester/*`에 배치.
- **BE-router** (`18010`): 외부 API 진입점, 인증 및 내부 서비스 중계.
- **GM Core** (`18020`): `LangGraph` 기반 턴 엔진. Rule/Scenario/State/LLM을 오케스트레이션.
- **Rule Engine** (`18050`): 장면 분석/페이즈 분류/룰 제안(diffs, relations) 생성.
- **Scenario Service** (`18040`):
  - 시나리오 생성 (`/api/v1/generation/*`)
  - 진행 검증 (`/api/v1/check/*`)
  - 상태 주입 브리지 (`/api/v1/manage/scenarios/{id}/inject`)
- **State Manager** (`18030`):
  - 세션/엔티티/진행 상태 관리 API
  - 커밋 API(`/state/commit`)
  - PostgreSQL + Apache AGE 초기화 및 쿼리/트리거 기반 상태 동기화
- **LLM Gateway** (`18060`): Gemini/OpenAI provider 라우팅, chat completion/SSE 제공.
- **WEB** (`18080`): 클라이언트 UI.
- **Infra**: Postgres(`15432`), Redis(`16379`).

## Data flow
- **A. Player Turn**
  1. Client -> BE-router `/gm/turn`
  2. BE-router -> GM `/api/v1/game/turn`
  3. GM `fetch_state`: State snapshot/act/sequence 조회
  4. GM `check_rule`: Rule Engine 제안 수신
  5. GM `check_scenario`: Scenario 제약/전이 제안 수신
  6. GM `resolve_conflicts`: Rule/Scenario diff 병합
  7. GM `commit_state`: State Manager 커밋 + act/sequence 전이 반영
  8. GM `generate_narrative`: LLM Gateway 서술 생성
  9. GM `save_log`: PlayLog 저장 후 응답
- **B. NPC Turn**
  1. GM이 active entity 선택(`npc` 또는 `narrator`)
  2. NPC 입력 생성 후 A 플로우 재실행
- **C. Scenario Authoring**
  1. Scenario Service가 LLM으로 시나리오 생성
  2. 내부 DB 저장 + 구조화 패키징
  3. State Manager 주입 API로 동기화

## Decisions
- Decision: **State/Rule/Scenario 책임 분리 + GM 중심 오케스트레이션**
- Reason: 변경 빈도가 높은 룰/서술 로직과 강한 일관성이 필요한 상태 저장을 분리해 장애 격리 및 교체 용이성 확보.
- Impact: 서비스 간 스키마 계약 정확성이 중요하며, DTO 불일치 시 턴 실패 가능.

- Decision: **State Manager에 SQL + AGE(그래프) 병행 사용**
- Reason: 정형 데이터(세션/엔티티 속성)와 관계 그래프(엔티티 상호작용)를 동시에 관리.
- Impact: 초기화/트리거/쿼리 순서 및 그래프 스키마 검증이 운영 안정성의 핵심.

- Decision: **LLM Gateway 단일 진입**
- Reason: 모델 교체(OpenAI/Gemini), 스트리밍, 설정 변경을 앱 계층에서 표준화.
- Impact: 개별 서비스는 provider 세부 구현을 몰라도 됨.

## Compatibility / migration notes
- `docs/global-plan.md`, `todo.md` 기준으로 다음 정합성 작업이 필요:
  - Scenario Service 주입 스키마(`master_id/item_id`)와 State Manager 주입 스키마(`rule_id/scenario_item_id`) 완전 정렬
  - Scenario transition API 미구현 구간 보강
  - 통합 테스트(10~20턴) 기준선 고정 및 회귀 자동화
- 현재 버전(`v0.0.0`)은 구조는 동작하나, 스키마 계약/전이 경계에 운영 리스크가 남아 있음.
