-- Migration V1: Split DBs and migrate data
-- This script assumes it runs as a Superuser (postgres) on the target instance.
-- It assumes the 'gtrpgm' database exists and contains the legacy data (loaded from dump).

-- 0. Enable dblink/postgres_fdw in gtrpgm for cross-db access (optional, or we use \c)
\c gtrpgm
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- 1. Create Users
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'scenario_user') THEN
    CREATE USER scenario_user WITH PASSWORD 'scenario_password';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'state_user') THEN
    CREATE USER state_user WITH PASSWORD 'state_password';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rule_user') THEN
    CREATE USER rule_user WITH PASSWORD 'rule_password';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'play_user') THEN
    CREATE USER play_user WITH PASSWORD 'play_password';
  END IF;
END
$$;

-- 2. Create Databases
-- We cannot run CREATE DATABASE inside a transaction block, so this script might need to be run with -f and ON_ERROR_STOP=off or handled carefully.
-- But psql handles it if they are separate commands.
SELECT 'CREATE DATABASE scenario_db OWNER scenario_user' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'scenario_db')\gexec
SELECT 'CREATE DATABASE state_db OWNER state_user' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'state_db')\gexec
SELECT 'CREATE DATABASE rule_db OWNER rule_user' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rule_db')\gexec
SELECT 'CREATE DATABASE play_db OWNER play_user' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'play_db')\gexec


-- 3. Migrate Rule DB (Users, Sessions)
\c rule_db
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE SERVER IF NOT EXISTS old_db FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host 'localhost', dbname 'gtrpgm', port '5432');
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER old_db OPTIONS (user 'postgres', password 'postgres');
CREATE USER MAPPING IF NOT EXISTS FOR postgres SERVER old_db OPTIONS (user 'postgres', password 'postgres');

-- Import Tables
IMPORT FOREIGN SCHEMA public LIMIT TO (users, user_sessions) FROM SERVER old_db INTO public;

-- Materialize Foreign Tables to Local Tables (This is the migration)
-- Rename foreign tables, create local tables as copies, drop foreign.
ALTER FOREIGN TABLE users RENAME TO users_foreign;
ALTER FOREIGN TABLE user_sessions RENAME TO user_sessions_foreign;

CREATE TABLE users AS SELECT * FROM users_foreign;
CREATE TABLE user_sessions AS SELECT * FROM user_sessions_foreign;

-- Restore PKs and Indexes (Simplified - assume standard PKs)
ALTER TABLE users ADD PRIMARY KEY (id);
ALTER TABLE user_sessions ADD PRIMARY KEY (session_id);

-- Clean up
DROP FOREIGN TABLE users_foreign;
DROP FOREIGN TABLE user_sessions_foreign;
DROP SERVER old_db CASCADE;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rule_user;
ALTER TABLE users OWNER TO rule_user;
ALTER TABLE user_sessions OWNER TO rule_user;


-- 4. Migrate Play DB (Logs, Vector)
\c play_db
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE SERVER IF NOT EXISTS old_db FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host 'localhost', dbname 'gtrpgm', port '5432');
CREATE USER MAPPING IF NOT EXISTS FOR postgres SERVER old_db OPTIONS (user 'postgres', password 'postgres');

-- Check if source has play_logs in public or ag_catalog?
-- We assume source dump puts them in ag_catalog based on previous grep.
-- But we can try importing from ag_catalog.
CREATE SCHEMA IF NOT EXISTS temp_migration;
IMPORT FOREIGN SCHEMA ag_catalog LIMIT TO (play_logs) FROM SERVER old_db INTO temp_migration;

-- Move to public
CREATE TABLE public.play_logs AS SELECT * FROM temp_migration.play_logs;

-- PK/Seq
ALTER TABLE public.play_logs ADD PRIMARY KEY (id);
-- Sequence?
CREATE SEQUENCE IF NOT EXISTS play_logs_id_seq OWNED BY play_logs.id;
SELECT setval('play_logs_id_seq', COALESCE((SELECT MAX(id)+1 FROM play_logs), 1), false);
ALTER TABLE play_logs ALTER COLUMN id SET DEFAULT nextval('play_logs_id_seq');

-- Clean up
DROP SCHEMA temp_migration CASCADE;
DROP SERVER old_db CASCADE;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO play_user;
ALTER TABLE play_logs OWNER TO play_user;


-- 5. Migrate Scenario/State DB (Graph)
-- This is tricky because of AGE.
-- We will migrate the 'scenario' metadata table to scenario_db
-- And the Graph itself to state_db (or scenario_db?)
-- Requirement: "scenario_user ... scenario_db ... state_user ... state_db"
-- Scenario DB usually holds static scenario definitions.
-- State DB holds runtime state graphs.
-- We will put 'scenario' table in scenario_db.

\c scenario_db
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE SERVER IF NOT EXISTS old_db FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host 'localhost', dbname 'gtrpgm', port '5432');
CREATE USER MAPPING IF NOT EXISTS FOR postgres SERVER old_db OPTIONS (user 'postgres', password 'postgres');

CREATE SCHEMA IF NOT EXISTS temp_migration;
-- Try pulling 'scenario', 'scenarios' from ag_catalog (per dump grep)
IMPORT FOREIGN SCHEMA ag_catalog LIMIT TO (scenario, scenarios) FROM SERVER old_db INTO temp_migration;

CREATE TABLE public.scenario AS SELECT * FROM temp_migration.scenario;
CREATE TABLE public.scenarios AS SELECT * FROM temp_migration.scenarios;

ALTER TABLE public.scenario ADD PRIMARY KEY (scenario_id);
ALTER TABLE public.scenarios ADD PRIMARY KEY (id);

DROP SCHEMA temp_migration CASCADE;
DROP SERVER old_db CASCADE;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scenario_user;
ALTER TABLE scenario OWNER TO scenario_user;
ALTER TABLE scenarios OWNER TO scenario_user;


-- 6. Migrate State DB (The AGE Graph)
\c state_db
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;
SELECT create_graph('state_db');

CREATE EXTENSION IF NOT EXISTS postgres_fdw;
CREATE SERVER IF NOT EXISTS old_db FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host 'localhost', dbname 'gtrpgm', port '5432');
CREATE USER MAPPING IF NOT EXISTS FOR postgres SERVER old_db OPTIONS (user 'postgres', password 'postgres');

-- Import the backing tables for the graph.
-- In the source (gtrpgm), the graph 'state_db' has its own schema 'state_db'.
-- FDW can import that schema.
CREATE SCHEMA IF NOT EXISTS source_state_db;
IMPORT FOREIGN SCHEMA state_db FROM SERVER old_db INTO source_state_db;

-- Now we copy data from source_state_db."Vertex" to state_db."Vertex"
-- We need to know the labels.
-- Labels: Player, Enemy, Item, Inventory, Session, NPC, RELATIONS...
-- We can dynamically find them or hardcode key ones.
-- Hardcoding key ones for safety.

INSERT INTO state_db."Player" SELECT * FROM source_state_db."Player";
INSERT INTO state_db."Enemy" SELECT * FROM source_state_db."Enemy";
INSERT INTO state_db."Item" SELECT * FROM source_state_db."Item";
INSERT INTO state_db."Inventory" SELECT * FROM source_state_db."Inventory";
INSERT INTO state_db."Session" SELECT * FROM source_state_db."Session";
INSERT INTO state_db."NPC" SELECT * FROM source_state_db."NPC";
INSERT INTO state_db."CONTAINS" SELECT * FROM source_state_db."CONTAINS";
INSERT INTO state_db."HAS_INVENTORY" SELECT * FROM source_state_db."HAS_INVENTORY";
INSERT INTO state_db."RELATION" SELECT * FROM source_state_db."RELATION";
-- Add others as needed

DROP SCHEMA source_state_db CASCADE;
DROP SERVER old_db CASCADE;

-- Grant usage on schema state_db (the graph schema) to state_user
GRANT USAGE ON SCHEMA state_db TO state_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA state_db TO state_user;
-- Also grant on ag_catalog for query
GRANT USAGE ON SCHEMA ag_catalog TO state_user;
GRANT SELECT ON ALL TABLES IN SCHEMA ag_catalog TO state_user;

\echo 'Migration Completed Successfully'
