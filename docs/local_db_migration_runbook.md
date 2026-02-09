# Local DB Migration Runbook (Step 1 Baseline)

목적:
- 원격 반영 전에 로컬에서만 DB 분리 이관을 검증한다.
- 테이블 경계는 `docs/db_table_inventory_by_service.md`를 기준으로 한다.
- `BE-router`는 `rule-engine`과 동일 DB를 사용한다.

## 0. Preconditions

- Docker 실행 중
- `platform-net` 네트워크 존재
- 단일 마이그레이션 파일: `db/migrations/0001_monolith_to_service_split.sql`

## 1. Local DB Start

```bash
bin/db up
docker ps --filter name=postgres
```

## 2. Baseline Backup (local only)

```bash
mkdir -p /tmp/gtrpgm-local-dump
docker exec -t postgres pg_dump -U "$DB_USER" -d "$DB_NAME" --schema-only > /tmp/gtrpgm-local-dump/schema.sql
docker exec -t postgres pg_dump -U "$DB_USER" -d "$DB_NAME" --data-only > /tmp/gtrpgm-local-dump/data.sql
```

## 3. Apply Single SQL

```bash
docker exec -i postgres psql -U "$DB_USER" -d "$DB_NAME" -f /dev/stdin < db/migrations/0001_monolith_to_service_split.sql
```

## 3-1. DB / User visibility check

```bash
docker exec -i postgres psql -U "$DB_USER" -d postgres <<'SQL'
\\l
\\du
SQL
```

## 4. Quick Verification Queries

```bash
for db in gm_db scenario_db state_db gtrpgm; do
  echo "== $db"
  docker exec -i postgres psql -U "$DB_USER" -d "$db" -c "\\dt public.*"
done
```

기대 상태:
- `gm_db` -> `play_logs`
- `scenario_db` -> `scenarios`, `session_states`
- `state_db` -> `scenario`, `scenario_act`, `scenario_sequence`, `session`, `player`, `npc`, `enemy`, `item`, `inventory`, `turn`
- `gtrpgm` -> rule-engine + BE-router 기존 테이블 유지

## 4-1. gtrpgm 유지 확인 (rule-engine / BE-router)

```bash
docker exec -i postgres psql -U "$DB_USER" -d postgres <<'SQL'
SELECT rolname FROM pg_roles WHERE rolname='gtrpgm';
SELECT datname FROM pg_database WHERE datname='gtrpgm';
SQL
```

## 5. Service-level Verification

- state-manager:
```bash
cd state-manager
uv run python scripts/verify_sql_syntax.py
uv run python scripts/api_verification.py
uv run python scripts/integration_commit_flow.py
uv run python scripts/integration_state_guards.py
```

## 6. Rollback (when failed)

```bash
# 단일 SQL이 아직 템플릿 단계이므로, 실패 시 dump를 기준으로 재기동/복구
bin/db down
bin/db up
```

필요 시 2단계에서 만든 dump를 사용해 수동 복원한다.

## 7. Approval Gate

- 로컬 검증 로그와 결과 표를 먼저 확인한다.
- 사용자 승인 전에는 리모트 DB 대상 작업(덤프/적용)을 진행하지 않는다.

## 8. Local Compose (DB-split aware)

루트 `docker-compose.local.yml` 기준:
- `rule-engine`, `BE-router` -> `gtrpgm` / `gtrpgm` 유지
- `gm` -> `gm_db` / `gm_user`
- `scenario-service` -> `scenario_db` / `scenario_user`
- `state-manager` -> `state_db` / `state_user`
- `db-migrator` 원샷 서비스가 `db/migrations/0001_monolith_to_service_split.sql` 자동 적용

권장 실행 순서:

```bash
# 기존 postgres(15432) 사용 중이면 먼저 정리
docker compose -f db/postgres/docker-compose.dev.yml down

# 루트 compose 실행
docker compose -f docker-compose.local.yml up --build -d
```
