\set ON_ERROR_STOP on

-- 0002_remote_split_non_destructive.sql
-- 목적:
--   리모트 환경에서 "서비스별 논리 DB 분리"를 안전하게 맞춘다.
--   - 기존 DB/데이터를 DROP 하지 않는다.
--   - gm/scenario DB와 유저를 생성하고, 최소 스키마/확장을 보장한다.
--   - state_db는 존재/접속 중일 수 있으므로 DROP/재생성하지 않는다.
--   - gtrpgm(rule-engine + BE-router 공유 DB)은 확장/데이터를 건드리지 않는다.
--
-- 주의:
--   이 스크립트는 로컬과 동일한 기본 패스워드를 설정한다.
--   (gm_local_change_me / scenario_local_change_me / state_local_change_me)
--   리모트에서 다른 비밀번호 정책을 쓰면 적용 후 ALTER ROLE로 재설정할 것.

-- =====================================================
-- Phase 0. Role bootstrap (idempotent)
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gm_user') THEN
        CREATE ROLE gm_user LOGIN PASSWORD 'gm_local_change_me';
    ELSE
        ALTER ROLE gm_user WITH LOGIN PASSWORD 'gm_local_change_me';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scenario_user') THEN
        -- scenario-service loads Apache AGE per-connection (LOAD 'age'), which requires superuser.
        CREATE ROLE scenario_user LOGIN PASSWORD 'scenario_local_change_me' SUPERUSER;
    ELSE
        ALTER ROLE scenario_user WITH LOGIN PASSWORD 'scenario_local_change_me';
        ALTER ROLE scenario_user WITH SUPERUSER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'state_user') THEN
        -- state-manager loads Apache AGE per-connection (LOAD 'age'), which requires superuser.
        CREATE ROLE state_user LOGIN PASSWORD 'state_local_change_me' SUPERUSER;
    ELSE
        ALTER ROLE state_user WITH LOGIN PASSWORD 'state_local_change_me';
        ALTER ROLE state_user WITH SUPERUSER;
    END IF;
END
$$;

-- =====================================================
-- Phase 1. Ensure service DBs exist (no drops)
-- =====================================================
-- Create DBs if missing
SELECT 'CREATE DATABASE gm_db WITH TEMPLATE template0 ENCODING ''UTF8'' OWNER gm_user'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'gm_db') \gexec

SELECT 'CREATE DATABASE scenario_db WITH TEMPLATE template0 ENCODING ''UTF8'' OWNER scenario_user'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'scenario_db') \gexec

SELECT 'CREATE DATABASE state_db WITH TEMPLATE template0 ENCODING ''UTF8'' OWNER state_user'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'state_db') \gexec

-- state_db may already exist; ensure owner if it does.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'state_db') THEN
        EXECUTE 'ALTER DATABASE state_db OWNER TO state_user';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE gm_db TO gm_user;
GRANT CONNECT ON DATABASE scenario_db TO scenario_user;
GRANT CONNECT ON DATABASE state_db TO state_user;

-- =====================================================
-- Phase 2. gm_db: ensure vector extension + minimal table
-- =====================================================
\connect gm_db

CREATE EXTENSION IF NOT EXISTS vector;

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

-- =====================================================
-- Phase 3. scenario_db: ensure age extension + minimal tables
-- =====================================================
\connect scenario_db

CREATE EXTENSION IF NOT EXISTS age CASCADE;

CREATE TABLE IF NOT EXISTS scenarios (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    genre TEXT,
    difficulty TEXT,
    description TEXT,
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE scenarios OWNER TO scenario_user;

CREATE TABLE IF NOT EXISTS session_states (
    id SERIAL PRIMARY KEY,
    scenario_id UUID NOT NULL,
    session_id UUID NOT NULL,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE session_states OWNER TO scenario_user;

GRANT USAGE, CREATE ON SCHEMA public TO scenario_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scenario_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO scenario_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scenario_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO scenario_user;

-- =====================================================
-- Phase 4. state_db: ensure age extension exists (no drops)
-- =====================================================
\connect state_db
CREATE EXTENSION IF NOT EXISTS age CASCADE;

-- =====================================================
-- Phase 5. gtrpgm: do not modify (remote-safe)
-- =====================================================
\connect gtrpgm
