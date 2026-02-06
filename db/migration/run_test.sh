#!/bin/bash
# run_test.sh
# 마이그레이션 SQL 테스트를 위한 범용 스크립트
# 사용법: ./db/migration/run_test.sh <migration_sql_file> [dump_file]

CONTAINER="postgres-test"

MIGRATION_SQL=$1
DUMP_FILE=$2

if [ -z "$MIGRATION_SQL" ]; then
    echo "❌ 마이그레이션 SQL 파일을 지정해주세요."
    echo "사용법: ./db/migration/run_test.sh <migration_sql_file> [dump_file]"
    exit 1
fi

# 1. 덤프 준비 (인자가 없으면 최신 dump/*.sql 사용)
if [ -z "$DUMP_FILE" ]; then
    DUMP_FILE=$(ls -t db/migration/dump/dump_*.sql 2>/dev/null | head -n 1)
fi

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ 덤프 파일을 찾을 수 없습니다: $DUMP_FILE"
    exit 1
fi

echo "📂 원본 덤프: $DUMP_FILE"
echo "📜 마이그레이션 SQL: $MIGRATION_SQL"

# 2. 로컬 테스트 DB 초기화
echo "🔄 [1/3] 테스트 DB 초기화 및 데이터 로드 중..."
docker exec $CONTAINER psql -U postgres -c "DROP DATABASE IF EXISTS gtrpgm;" >/dev/null
docker exec $CONTAINER psql -U postgres -c "CREATE DATABASE gtrpgm OWNER gtrpgm;" >/dev/null

docker cp "$DUMP_FILE" "$CONTAINER:/dump.sql"
docker exec $CONTAINER psql -U gtrpgm -d gtrpgm -f /dump.sql > /dev/null 2>&1

# 3. 마이그레이션 SQL 실행
echo "🚀 [2/3] 마이그레이션 SQL 실행 중..."
docker cp "$MIGRATION_SQL" "$CONTAINER:/migration.sql"
docker exec $CONTAINER psql -U gtrpgm -d gtrpgm -f /migration.sql

# 4. 결과 확인
echo "📊 [3/3] 최종 테이블 목록 확인:"
docker exec $CONTAINER psql -U gtrpgm -d gtrpgm -c "\dt public.*"

echo "📊 최종 확장(Extension) 목록 확인:"
docker exec $CONTAINER psql -U gtrpgm -d gtrpgm -c "\dx"
