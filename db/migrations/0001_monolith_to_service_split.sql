\set ON_ERROR_STOP on

-- 0001_monolith_to_service_split.sql
-- 목적:
--   로컬 기준에서 모놀리식 `gtrpgm` DB를 서비스별 DB로 분리하여
--   "DB/유저/테이블이 각각 보이는" 상태를 만든다.
--
-- 핵심 규칙:
--   - rule-engine + BE-router 는 기존 `gtrpgm` DB / `gtrpgm` 유저를 그대로 사용
--   - gm/scenario/state 는 별도 DB + 별도 유저 사용
--
-- 주의:
--   - 로컬 검증용 스크립트다.
--   - gm/scenario/state 는 template0 기반으로 재생성한다(데이터 비이관 전제).

-- =====================================================
-- Phase 0. Role bootstrap
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gtrpgm') THEN
        RAISE EXCEPTION 'Required role gtrpgm not found. Create/import source first.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gm_user') THEN
        CREATE ROLE gm_user LOGIN PASSWORD 'gm_local_change_me';
    ELSE
        ALTER ROLE gm_user WITH LOGIN PASSWORD 'gm_local_change_me';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scenario_user') THEN
        CREATE ROLE scenario_user LOGIN PASSWORD 'scenario_local_change_me';
    ELSE
        ALTER ROLE scenario_user WITH LOGIN PASSWORD 'scenario_local_change_me';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'state_user') THEN
        CREATE ROLE state_user LOGIN PASSWORD 'state_local_change_me';
    ELSE
        ALTER ROLE state_user WITH LOGIN PASSWORD 'state_local_change_me';
    END IF;
END
$$;

-- =====================================================
-- Phase 1. Recreate service DBs
-- =====================================================
-- 매번 재현 가능한 로컬 테스트를 위해 타깃 DB를 재생성
SELECT 'DROP DATABASE IF EXISTS gm_db' \gexec
SELECT 'DROP DATABASE IF EXISTS scenario_db' \gexec
SELECT 'DROP DATABASE IF EXISTS state_db' \gexec

-- 서비스 DB는 템플릿0에서 생성해 확장/스키마 오염을 차단
SELECT 'CREATE DATABASE gm_db WITH TEMPLATE template0 ENCODING ''UTF8''' \gexec
SELECT 'CREATE DATABASE scenario_db WITH TEMPLATE template0 ENCODING ''UTF8''' \gexec
SELECT 'CREATE DATABASE state_db WITH TEMPLATE template0 ENCODING ''UTF8''' \gexec

ALTER DATABASE gm_db OWNER TO gm_user;
ALTER DATABASE scenario_db OWNER TO scenario_user;
ALTER DATABASE state_db OWNER TO state_user;

GRANT CONNECT ON DATABASE gm_db TO gm_user;
GRANT CONNECT ON DATABASE scenario_db TO scenario_user;
GRANT CONNECT ON DATABASE state_db TO state_user;

-- =====================================================
-- Phase 2. Keep only service tables in each DB
-- =====================================================
\connect gm_db

-- 확장 정책(gm): vector만 활성화
DO $$
DECLARE ext text;
BEGIN
    FOREACH ext IN ARRAY ARRAY['age', 'pg_trgm', 'btree_gin', 'pgcrypto', 'pg_stat_statements']
    LOOP
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = ext) THEN
                EXECUTE format('DROP EXTENSION %I CASCADE', ext);
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'skip dropping extension %: %', ext, SQLERRM;
        END;
    END LOOP;
END
$$;
CREATE EXTENSION IF NOT EXISTS vector;

-- GM 최소 스키마 보장 (source DB가 비어있어도 테이블 가시성 확보)
CREATE TABLE IF NOT EXISTS play_logs (
    id SERIAL PRIMARY KEY,
    turn_id VARCHAR(100) NOT NULL UNIQUE,
    session_id VARCHAR(50) NOT NULL,
    act_id VARCHAR(50),
    sequence_id VARCHAR(50),
    sequence_type VARCHAR(50),
    sequence_seq INT,
    turn_seq INT NOT NULL,
    active_entity_id VARCHAR(50) NOT NULL,
    user_input TEXT NOT NULL,
    final_output TEXT,
    state_diff JSONB,
    world_snapshot JSONB,
    commit_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    meta_info JSONB
);
ALTER TABLE play_logs OWNER TO gm_user;

GRANT USAGE, CREATE ON SCHEMA public TO gm_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gm_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO gm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO gm_user;

\connect scenario_db

-- 확장 정책(scenario): age만 활성화
DO $$
DECLARE ext text;
BEGIN
    FOREACH ext IN ARRAY ARRAY['vector', 'pg_trgm', 'btree_gin', 'pgcrypto', 'pg_stat_statements']
    LOOP
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = ext) THEN
                EXECUTE format('DROP EXTENSION %I CASCADE', ext);
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'skip dropping extension %: %', ext, SQLERRM;
        END;
    END LOOP;
END
$$;
CREATE EXTENSION IF NOT EXISTS age CASCADE;

CREATE TABLE IF NOT EXISTS scenarios (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    concept TEXT,
    state_manager_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE scenarios OWNER TO scenario_user;

CREATE TABLE IF NOT EXISTS session_states (
    session_id UUID PRIMARY KEY,
    scenario_id UUID NOT NULL,
    current_act_id TEXT NOT NULL,
    current_sequence_id TEXT NOT NULL,
    context_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE session_states OWNER TO scenario_user;

GRANT USAGE, CREATE ON SCHEMA public TO scenario_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scenario_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO scenario_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scenario_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO scenario_user;

\connect state_db

-- 확장 정책(state): age만 활성화
DO $$
DECLARE ext text;
BEGIN
    FOREACH ext IN ARRAY ARRAY['vector', 'pg_trgm', 'btree_gin', 'pgcrypto', 'pg_stat_statements']
    LOOP
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = ext) THEN
                EXECUTE format('DROP EXTENSION %I CASCADE', ext);
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'skip dropping extension %: %', ext, SQLERRM;
        END;
    END LOOP;
END
$$;
CREATE EXTENSION IF NOT EXISTS age CASCADE;

GRANT USAGE, CREATE ON SCHEMA public TO state_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO state_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO state_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO state_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO state_user;

-- =====================================================
-- Phase 3. Verification snapshots
-- =====================================================
\connect postgres

SELECT datname
FROM pg_database
WHERE datname IN ('gtrpgm', 'gm_db', 'scenario_db', 'state_db')
ORDER BY datname;

SELECT rolname
FROM pg_roles
WHERE rolname IN ('gtrpgm', 'gm_user', 'scenario_user', 'state_user')
ORDER BY rolname;

\connect gm_db
\dt public.*

\connect scenario_db
\dt public.*

\connect state_db
\dt public.*

\connect gtrpgm
-- rule-engine + BE-router shared DB (role/password unchanged)
-- 확장 정책(gtrpgm): 커스텀 확장 없음(plpgsql 기본 확장은 예외)
DO $$
DECLARE ext text;
BEGIN
    FOREACH ext IN ARRAY ARRAY['age', 'vector', 'pg_trgm', 'btree_gin', 'pgcrypto', 'pg_stat_statements']
    LOOP
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = ext) THEN
                EXECUTE format('DROP EXTENSION %I CASCADE', ext);
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'skip dropping extension %: %', ext, SQLERRM;
        END;
    END LOOP;
END
$$;

-- source DB가 비어있는 경우를 위한 최소 테이블 보장
CREATE TABLE IF NOT EXISTS users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    user_id BIGINT NOT NULL,
    session_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS items (
    item_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    effect_value INTEGER,
    description TEXT,
    weight NUMERIC,
    grade TEXT,
    base_price NUMERIC
);

CREATE TABLE IF NOT EXISTS npcs (
    npc_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    disposition TEXT,
    occupation TEXT,
    dialogue_style TEXT,
    description TEXT,
    base_difficulty INTEGER,
    combat_description TEXT
);

CREATE TABLE IF NOT EXISTS npc_inventories (
    inventory_id SERIAL PRIMARY KEY,
    npc_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    is_infinite_stock BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS enemies (
    enemy_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    base_difficulty INTEGER,
    description TEXT,
    type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enemy_drops (
    drop_id SERIAL PRIMARY KEY,
    enemy_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    drop_rate NUMERIC,
    min_quantity INTEGER,
    max_quantity INTEGER
);

CREATE TABLE IF NOT EXISTS personality (
    id TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS abilities (
    ability_id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS characters (
    character_id SERIAL PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS system_configs (
    config_key TEXT PRIMARY KEY,
    config_value TEXT
);

CREATE TABLE IF NOT EXISTS world_eras (
    era_id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS world_locales (
    locale_id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT
);

\dt public.*

\connect gm_db
SELECT extname FROM pg_extension ORDER BY extname;

\connect scenario_db
SELECT extname FROM pg_extension ORDER BY extname;

\connect state_db
SELECT extname FROM pg_extension ORDER BY extname;

\connect gtrpgm
SELECT extname FROM pg_extension ORDER BY extname;
