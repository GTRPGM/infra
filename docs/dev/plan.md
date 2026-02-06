<!-- PROJ_ARCH_BEGIN -->
## Architecture
- current: v0.0.0
- docs/dev/architect/architecture_v0.0.0.md
<!-- PROJ_ARCH_END -->

<!-- PROJ_DASHBOARD_BEGIN -->
## Feature Dashboard
| ID | Feature | Detail | Status |
|---|---|---|---|
| F-001 | Local MSA Orchestration | `docker-compose.local.yml` + `bin/project`로 9개 서비스(Postgres/Redis 포함) 기동 | done |
| F-002 | BE Router API Gateway | 인증/유저/GM/State/Info/Minigame 라우팅 (`services/BE-router/src/configs/api_routers.py`) | done |
| F-003 | GM Turn Pipeline | `fetch_state -> rule -> scenario -> commit -> narrative -> log` LangGraph 파이프라인 | done |
| F-004 | Auto NPC Turn | 플레이어 턴 후 엔티티 존재 시 NPC/내레이터 턴 자동 연쇄 처리 | done |
| F-005 | Scenario Generation | `pure/grounded/informed` 생성 API + DB 저장 (`scenario-service`) | done |
| F-006 | Scenario Injection | Scenario Service -> State Manager 주입 API 연동 (`/api/v1/manage/scenarios/{id}/inject`) | done |
| F-007 | State SOT + Graph | State Manager SQL + Apache AGE 그래프 초기화/동기화 및 commit API | done |
| F-008 | LLM Gateway Provider Routing | OpenAI/Gemini 라우팅 + config 변경 API + SSE stream 지원 | done |
| F-009 | Integration Runner | `tester/src/tester/runner.py` 기반 생성-주입-세션시작-턴루프 E2E 러너 | done |
| F-010 | Session Transition API | Scenario Service `/sessions/transition`가 state-manager act/sequence 갱신을 실제 수행 | done |
| F-011 | Service Path Migration | 서비스 서브모듈을 `services/`로 재배치하고 테스터 코드를 `tester/src`로 이동 | done |
| plan_0008 | DB 분리 및 마이그레이션 | `docs/dev/detail/plan_0008.md` | done |
| plan_0009 | Session Transition 정렬 | `docs/dev/detail/plan_0009.md` | done |
| plan_0010 | 테스터 정합성 어설트 강화 | `docs/dev/detail/plan_0010.md` | done |
| plan_0011 | 시퀀스 전이 누락 탐지 강화 | `docs/dev/detail/plan_0011.md` | done |
<!-- PROJ_DASHBOARD_END -->

<!-- PROJ_TODO_BEGIN -->
## TODO (Undone detail plans)
- 없음 (상세 플랜 `plan_0001`~`plan_0011` 완료)
<!-- PROJ_TODO_END -->
