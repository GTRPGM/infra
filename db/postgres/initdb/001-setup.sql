-- Create gtrpgm role if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'gtrpgm') THEN
        CREATE ROLE gtrpgm WITH LOGIN PASSWORD 'postgres' SUPERUSER;
    END IF;
END
$$;

-- Global search path configuration
DO $$
BEGIN
    EXECUTE format(
        'ALTER DATABASE %I SET search_path = ag_catalog, "$user", public;',
        current_database()
    );
END $$;
SET search_path = ag_catalog, "$user", public;

-- Create missing types
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item_category') THEN
        CREATE TYPE public.item_category AS ENUM ('무기', '방어구', '도구', '소모품', '기타');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'phase_type') THEN
        CREATE TYPE public.phase_type AS ENUM ('exploration', 'combat', 'dialogue', 'rest', '탐험', '전투', '대화', '흥정', '휴식', '회복', '알 수 없음');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'session_status') THEN
        CREATE TYPE public.session_status AS ENUM ('active', 'paused', 'ended');
    END IF;
END$$;

-- Create missing sequences
CREATE SEQUENCE IF NOT EXISTS public.bestiary_mob_id_seq;
CREATE SEQUENCE IF NOT EXISTS public.backgrounds_bg_id_seq;
