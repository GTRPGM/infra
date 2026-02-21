#!/bin/bash
set -e

# Usage: ./db/migration/run_migration.sh <dump_file_path>

DUMP_FILE=$1

if [ -z "$DUMP_FILE" ]; then
    echo "Usage: $0 <dump_file>"
    exit 1
fi

# Ensure we are in the project root or handle paths correctly
# Assume script is at db/migration/run_migration.sh
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(dirname "$(dirname "$SCRIPT_DIR")")

echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT/db/migration"

echo "Splitting dump file ($DUMP_FILE)..."
DUMP_FILE_ABS=$(readlink -f "$DUMP_FILE")

uv run python split_dump.py "$DUMP_FILE_ABS" dump_graph.sql dump_play.sql dump_rule.sql

echo "Restoring Graph DB (postgres-graph)..."
cat dump_graph.sql | docker compose -f ../../docker-compose.local.yml exec -T postgres-graph psql -U postgres -d gtrpgm_graph || echo "Graph DB restore warning (check logs)"

echo "Restoring Play DB (postgres-play)..."
cat dump_play.sql | docker compose -f ../../docker-compose.local.yml exec -T postgres-play psql -U postgres -d gtrpgm_play || echo "Play DB restore warning (check logs)"

echo "Restoring Rule DB (postgres-rule)..."
cat dump_rule.sql | docker compose -f ../../docker-compose.local.yml exec -T postgres-rule psql -U postgres -d gtrpgm_rule || echo "Rule DB restore warning (check logs)"

echo "Cleaning up split files..."
rm dump_graph.sql dump_play.sql dump_rule.sql

echo "Migration completed."
