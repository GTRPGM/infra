#!/bin/bash
set -e

# Test Migration Script
# 1. Resets Docker (Single Postgres)
# 2. Loads Original Dump to 'gtrpgm'
# 3. Runs Migration SQL
# 4. Verifies Results

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(dirname "$(dirname "$SCRIPT_DIR")")

cd "$PROJECT_ROOT"

echo "1. Restarting Postgres..."
./bin/project down
# Ensure we start fresh
docker volume rm infra_pgdata || true
./bin/project up -d postgres
# Wait for health
echo "Waiting for Postgres..."
until docker compose -f docker-compose.local.yml exec postgres pg_isready -U postgres; do
  sleep 2
done

echo "2. Loading Original Dump..."
# Use dump_cleaned.sql
DUMP_FILE="$SCRIPT_DIR/dump_cleaned.sql"
if [ ! -f "$DUMP_FILE" ]; then
    echo "Dump file not found: $DUMP_FILE"
    exit 1
fi

cat "$DUMP_FILE" | docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -d gtrpgm > /dev/null 2>&1 || echo "Dump loaded (some errors ignored)"

echo "3. Running Migration..."
cat "$SCRIPT_DIR/migrate_split_v1.sql" | docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -d gtrpgm

echo "4. Verifying Results..."
# Check DBs
docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -c "\l"

# Check Rule DB Users
echo "--- Rule DB Users ---"
docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -d rule_db -c "SELECT count(*) FROM users;"

# Check Play DB Logs
echo "--- Play DB Logs ---"
docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -d play_db -c "SELECT count(*) FROM play_logs;"

# Check Scenario DB
echo "--- Scenario DB ---"
docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -d scenario_db -c "SELECT count(*) FROM scenario;"

# Check State DB Graph (via Cypher if possible, or just table count)
echo "--- State DB Graph ---"
docker compose -f docker-compose.local.yml exec -T postgres psql -U postgres -d state_db -c "SELECT count(*) FROM state_db."Player";"

echo "Test Complete."
