-- migration_final.sql

-- [1] 로그 및 히스토리 데이터 삭제
DROP TABLE IF EXISTS public.play_logs CASCADE;
DROP TABLE IF EXISTS public.turn CASCADE;
-- generation_logs는 유지 (LLM 생성 이력 데이터)

-- [2] 인스턴스 데이터 (세션 종속) 삭제
DROP TABLE IF EXISTS public.inventory CASCADE;
DROP TABLE IF EXISTS public.item CASCADE;
DROP TABLE IF EXISTS public.npc CASCADE;          -- NPC 인스턴스
DROP TABLE IF EXISTS public.enemy CASCADE;        -- Enemy 인스턴스
DROP TABLE IF EXISTS public.player CASCADE;
-- player_abilities 및 npc_inventories는 유지 (Rule/Template 데이터)

-- [3] 시나리오 데이터 삭제 (Rule DB에는 불필요하다고 판단 시)
DROP TABLE IF EXISTS public.scenario_sequence CASCADE;
DROP TABLE IF EXISTS public.scenario_act CASCADE;
DROP TABLE IF EXISTS public.scenario CASCADE;

-- [4] 세션 테이블 처리
-- user_sessions 테이블은 유지하되, session 테이블은 삭제해야 함.
-- FK 제약조건 때문에 session 테이블을 그냥 지우면 에러가 발생하므로, 먼저 제약조건을 제거.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'user_sessions_session_id_fkey') THEN
        ALTER TABLE public.user_sessions DROP CONSTRAINT user_sessions_session_id_fkey;
    END IF;
END $$;

-- 이제 session 테이블 삭제
DROP TABLE IF EXISTS public.session CASCADE;

-- [5] 정리
VACUUM FULL;
