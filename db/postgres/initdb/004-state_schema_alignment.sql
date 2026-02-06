-- Align state-manager runtime schema with state SST expectations.
-- This runs safely on fresh DBs and existing DBs (IF NOT EXISTS guards).

-- Player (flattened)
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS hp INTEGER NOT NULL DEFAULT 100;
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS mp INTEGER NOT NULL DEFAULT 50;
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS str INTEGER;
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS dex INTEGER;
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS int INTEGER;
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS lux INTEGER;
ALTER TABLE IF EXISTS public.player ADD COLUMN IF NOT EXISTS san INTEGER NOT NULL DEFAULT 10;

-- NPC (flattened + rule_id)
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS rule_id INT NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS hp INTEGER NOT NULL DEFAULT 100;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS mp INTEGER NOT NULL DEFAULT 50;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS str INTEGER;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS dex INTEGER;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS int INTEGER;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS lux INTEGER;
ALTER TABLE IF EXISTS public.npc ADD COLUMN IF NOT EXISTS san INTEGER NOT NULL DEFAULT 10;

-- Enemy (flattened + rule_id)
ALTER TABLE IF EXISTS public.enemy ADD COLUMN IF NOT EXISTS rule_id INT NOT NULL DEFAULT 0;
ALTER TABLE IF EXISTS public.enemy ADD COLUMN IF NOT EXISTS hp INTEGER NOT NULL DEFAULT 30;
ALTER TABLE IF EXISTS public.enemy ADD COLUMN IF NOT EXISTS max_hp INTEGER NOT NULL DEFAULT 30;
ALTER TABLE IF EXISTS public.enemy ADD COLUMN IF NOT EXISTS attack INTEGER NOT NULL DEFAULT 10;
ALTER TABLE IF EXISTS public.enemy ADD COLUMN IF NOT EXISTS defense INTEGER NOT NULL DEFAULT 5;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'enemy'
          AND column_name = 'dropped_items'
          AND udt_name = '_uuid'
    ) THEN
        ALTER TABLE public.enemy
            ALTER COLUMN dropped_items DROP DEFAULT;
        ALTER TABLE public.enemy
            ALTER COLUMN dropped_items TYPE JSONB
            USING to_jsonb(dropped_items);
        ALTER TABLE public.enemy
            ALTER COLUMN dropped_items SET DEFAULT '[]'::jsonb;
    END IF;
END $$;

-- Inventory (legacy owner 필드 nullable 호환)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'inventory'
          AND column_name = 'owner_entity_type'
    ) THEN
        ALTER TABLE public.inventory
            ALTER COLUMN owner_entity_type DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'inventory'
          AND column_name = 'owner_entity_id'
    ) THEN
        ALTER TABLE public.inventory
            ALTER COLUMN owner_entity_id DROP NOT NULL;
    END IF;
END $$;

-- Item (rule_id)
ALTER TABLE IF EXISTS public.item ADD COLUMN IF NOT EXISTS rule_id INT NOT NULL DEFAULT 0;

-- Turn (phase 제거 이후 호환)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'turn'
          AND column_name = 'phase_at_turn'
    ) THEN
        ALTER TABLE public.turn
            ALTER COLUMN phase_at_turn DROP NOT NULL;
    END IF;
END $$;
