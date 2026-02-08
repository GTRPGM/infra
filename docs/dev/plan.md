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
| plan_0008 | DB 분리 및 마이그레이션 | `docs/dev/detail/plan_0008.md` | drifted |
| plan_0009 | Session Transition 정렬 | `docs/dev/detail/plan_0009.md` | done |
| plan_0010 | 테스터 정합성 어설트 강화 | `docs/dev/detail/plan_0010.md` | done |
| plan_0011 | 시퀀스 전이 누락 탐지 강화 | `docs/dev/detail/plan_0011.md` | done |
| plan_0012 | BE-router 전체 게임 플로우 정상 동작 검증 | `docs/dev/detail/plan_0012.md` | in_progress |
| plan_0017 | 3액트/6시퀀스 고도화 시나리오 평가 | `docs/dev/detail/plan_0017.md` | done |
| plan_0018 | 인벤토리 표현 불일치 원인 확정 | `docs/dev/detail/plan_0018.md` | done |
| plan_0019 | 인벤토리 경로 정렬 및 E2E 재검증 | `docs/dev/detail/plan_0019.md` | done |
| plan_0020 | seq-4 전이 고착 수정 | `docs/dev/detail/plan_0020.md` | done |
| plan_0021 | 인벤토리 표기/세션 종료 잔존 이슈 해소 | `docs/dev/detail/plan_0021.md` | done |
| plan_0022 | rule-engine 아이템 ID 파싱 정렬 및 종료 정합성 복구 | `docs/dev/detail/plan_0022.md` | done |
| plan_0023 | state-manager 리모트 동기화 및 회귀 점검 | `docs/dev/detail/plan_0023.md` | done |
| plan_0024 | 잔존 운영 이슈 정리 (manifest/표시정합/session-add) | `docs/dev/detail/plan_0024.md` | done |
| plan_0025 | sequence_type 기반 판정 컨텍스트 도입 | `docs/dev/detail/plan_0025.md` | done |
| plan_0026 | 종료 게이트 정합성 및 터미널 반복 보강 | `docs/dev/detail/plan_0026.md` | done |
| plan_0027 | require_session_end 강제 장기 회귀 | `docs/dev/detail/plan_0027.md` | done |
| plan_0028 | 서사-상태 정합 가드레일 | `docs/dev/detail/plan_0028.md` | done |
<!-- PROJ_DASHBOARD_END -->

<!-- PROJ_TODO_BEGIN -->
## TODO (Undone detail plans)
- `[P0] plan_0012` BE-router 경유 전체 게임 진행 플로우(로그인->시나리오->세션->상태요약->턴) 정상 동작 및 턴/상태 정합성 게이트 구축
- `[P9 - 최하순위] plan_0008` DB 분리 상태 재정렬 (현재 `docker-compose.local.yml`은 단일 `postgres` 구성, 문서/실행환경 불일치)
<!-- PROJ_TODO_END -->
