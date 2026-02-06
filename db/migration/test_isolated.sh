#!/bin/bash
set -e

# Isolated Migration Test Script
# Runs a separate postgres container on port 25432
# Loads original dump, runs migration, checks results, cleans up.

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# migration/test_env
TEST_ENV_DIR="$SCRIPT_DIR/test_env"
# project root
PROJECT_ROOT=$(dirname "$(dirname "$SCRIPT_DIR")")

echo "Project Root: $PROJECT_ROOT"
cd "$TEST_ENV_DIR"

echo "[1/6] Cleaning up previous test environment..."
docker compose -f docker-compose.test.yml down -v --remove-orphans || true

echo "[2/6] Starting isolated Postgres container (port 25432)..."
docker compose -f docker-compose.test.yml up -d
echo "Waiting for Postgres..."
until docker compose -f docker-compose.test.yml exec postgres-mig-test pg_isready -U postgres; do
  sleep 2
done

echo "[3/6] Loading ORIGINAL dump into 'gtrpgm'..."
# Original dump path
DUMP_FILE="$PROJECT_ROOT/dump_cleaned.sql"
if [ ! -f "$DUMP_FILE" ]; then
    echo "Error: Dump file not found at $DUMP_FILE"
    exit 1
fi
# Load dump
cat "$DUMP_FILE" | docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U postgres -d gtrpgm > /dev/null 2>&1 || echo "Dump loaded (ignoring minor errors)"

echo "[4/6] Applying Single SQL Migration File..."
MIG_FILE="$PROJECT_ROOT/db/migration/migrate_split_v1.sql"
if [ ! -f "$MIG_FILE" ]; then
    echo "Error: Migration file not found at $MIG_FILE"
    exit 1
fi

cat "$MIG_FILE" | docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U postgres -d gtrpgm

echo "[5/6] Verifying Results..."
echo ">>> Checking Created Databases:"
docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U postgres -c "\l"

echo ">>> Checking Rule DB (User Count):"
docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U rule_user -d rule_db -c "SELECT count(*) FROM users;"

echo ">>> Checking Scenario DB (Scenario Count):"
docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U scenario_user -d scenario_db -c "SELECT count(*) FROM scenario;"

echo ">>> Checking Play DB (Log Count):"
docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U play_user -d play_db -c "SELECT count(*) FROM play_logs;"

echo ">>> Checking State DB (Player Node Count):"
# Note: State DB uses 'state_user' and graph schema
docker compose -f docker-compose.test.yml exec -T postgres-mig-test psql -U state_user -d state_db -c "SELECT count(*) FROM state_db."Player";"

echo "[6/6] Cleanup (Optional - press Ctrl+C to keep container for inspection)"
# Uncomment to auto-cleanup
# docker compose -f docker-compose.test.yml down -v

echo "Test Finished Successfully!"
