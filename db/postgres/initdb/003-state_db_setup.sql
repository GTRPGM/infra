-- Create state_user role if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'state_user') THEN
        CREATE ROLE state_user WITH LOGIN PASSWORD 'state_user_password' SUPERUSER;
    ELSE
        -- Ensure existing user has SUPERUSER privilege for AGE extension loading
        ALTER ROLE state_user WITH SUPERUSER;
    END IF;
END
$$;

-- Create state_db database if it doesn't exist
SELECT 'CREATE DATABASE state_db OWNER state_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'state_db')\gexec

-- Switch to state_db to install extensions
\c state_db

-- Enable commonly used extensions explicitly first
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable all other available extensions
DO $$
DECLARE
    ext text;
BEGIN
    FOR ext IN SELECT name FROM pg_available_extensions WHERE name NOT IN ('plpgsql') LOOP
        BEGIN
            EXECUTE 'CREATE EXTENSION IF NOT EXISTS "' || ext || '" CASCADE';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Skipping extension %: %', ext, SQLERRM;
        END;
    END LOOP;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE state_db TO state_user;
GRANT ALL ON SCHEMA public TO state_user;

-- Set search_path for state_user (Critical for AGE extension)
ALTER ROLE state_user SET search_path = ag_catalog, "$user", public;
