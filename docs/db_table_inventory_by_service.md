# DB Table Inventory by Service (Code-based)

기준:
- 각 서비스 코드에서 실제로 참조하는 SQL 파일/스키마 정의를 기준으로 분류.
- `BE-router`는 사용자 요청대로 `rule-engine`과 동일 DB를 사용한다고 가정.
- 아래 표는 **로컬 마이그레이션 테스트용 1차 기준선**.

## 1) GM DB

- DB: `gm_db`
- User: `gm_user`
- Password (local migration default): `gm_local_change_me`
- `play_logs`

근거:
- `gm/src/gm/infra/db/schema.sql`
- `gm/src/gm/infra/db/queries/play_logs.sql`

## 2) Scenario Service DB

- DB: `scenario_db`
- User: `scenario_user`
- Password (local migration default): `scenario_local_change_me`
- `scenarios`
- `session_states`

근거:
- `scenario-service/src/scenario/infra/db/queries/sql/init_db.sql`
- `scenario-service/src/scenario/infra/db/queries/sql/*.sql`

## 3) State Manager DB

- DB: `state_db`
- User: `state_user`
- Password (local migration default): `state_local_change_me`
- `scenario`
- `scenario_act`
- `scenario_sequence`
- `session`
- `player`
- `npc`
- `enemy`
- `item`
- `inventory`
- `turn`

근거:
- `state-manager/src/state_db/Query/BASE/B_scenario.sql`
- `state-manager/src/state_db/Query/BASE/B_scenario_act.sql`
- `state-manager/src/state_db/Query/BASE/B_scenario_sequence.sql`
- `state-manager/src/state_db/Query/BASE/B_session.sql`
- `state-manager/src/state_db/Query/BASE/B_player.sql`
- `state-manager/src/state_db/Query/BASE/B_npc.sql`
- `state-manager/src/state_db/Query/BASE/B_enemy.sql`
- `state-manager/src/state_db/Query/BASE/B_item.sql`
- `state-manager/src/state_db/Query/BASE/B_inventory.sql`
- `state-manager/src/state_db/Query/BASE/B_turn.sql`

## 4) Rule Engine + BE-router Shared DB

- DB: `gtrpgm`
- User: `gtrpgm` (기존 user/password 유지)
- Password: 기존 `gtrpgm` 비밀번호 그대로 사용 (마이그레이션 SQL에서 변경하지 않음)
- `users`
- `user_sessions`
- `items`
- `npcs`
- `npc_inventories`
- `enemies`
- `enemy_drops`
- `personality`
- `abilities`
- `characters`
- `system_configs`
- `world_eras`
- `world_locales`

근거:
- `rule-engine/src/domains/info/queries/*.sql`
- `rule-engine/src/domains/scenario/queries/*.sql`
- `rule-engine/src/domains/session/queries/*.sql`
- `rule-engine/src/domains/user/queries/*.sql`
- `BE-router/src/auth/queries/*.sql`
- `BE-router/src/info/queries/*.sql`

## 5) LLM Gateway DB

- 없음 (현재 코드 기준 DB 테이블 직접 사용 없음)

근거:
- `llm-gateway/src` 하위 DB 쿼리 파일 부재
