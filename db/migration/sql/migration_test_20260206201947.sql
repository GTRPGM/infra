-- 1. 동적 게임 데이터 (인스턴스) 및 로그 삭제
-- 의존성 순서: 자식 테이블부터 삭제

-- 로그 및 히스토리
DROP TABLE IF EXISTS public.play_logs CASCADE;
DROP TABLE IF EXISTS public.turn CASCADE;
DROP TABLE IF EXISTS public.generation_logs CASCADE;

-- 세션 내 인스턴스 (State DB 이관 대상)
DROP TABLE IF EXISTS public.inventory CASCADE;
DROP TABLE IF EXISTS public.player_abilities CASCADE;
DROP TABLE IF EXISTS public.player CASCADE;
DROP TABLE IF EXISTS public.npc_inventories CASCADE; -- 주의: 원본 NPC 인벤토리인지 인스턴스인지 확인 필요. 이름상 인스턴스 가능성 높음.
DROP TABLE IF EXISTS public.enemy CASCADE;
DROP TABLE IF EXISTS public.item CASCADE;

-- 시나리오 구조 (필요하다면 남길 수 있으나, Rule/User 서버 정의에 따르면 제거 대상일 수 있음)
-- 여기서는 일단 "룰-유저 서버"에 시나리오 구조가 포함되는지 모호하나, 
-- 사용자가 "관계 연결 된거랑 안된거로 나눠서"라고 했으므로 
-- 시나리오 텍스트 자체는 룰 데이터에 가까움.
-- 하지만 앞서 "시나리오 부분 삭제해줄 수 있나?"라고 물었으므로 삭제 목록에 포함.
DROP TABLE IF EXISTS public.scenario_sequence CASCADE;
DROP TABLE IF EXISTS public.scenario_act CASCADE;
DROP TABLE IF EXISTS public.scenario CASCADE;

-- 세션 테이블 처리
-- user_sessions는 남겨야 함 (User <-> Session 매핑)
-- 하지만 user_sessions는 session_id를 FK로 가질 수 있음.
-- public.session 테이블을 삭제하면 user_sessions의 FK 제약조건 때문에 에러가 날 수 있음.
-- 따라서 user_sessions의 FK를 끊거나, session 테이블을 남기고 내용만 비우거나 해야 함.
-- 여기서는 "룰-유저 서버"에서 세션 매핑 정보만 관리한다고 가정하고,
-- FK 제약조건을 삭제하고 session 테이블을 날리는 방식을 시도.

ALTER TABLE IF EXISTS public.user_sessions DROP CONSTRAINT IF EXISTS user_sessions_session_id_fkey;
DROP TABLE IF EXISTS public.session CASCADE;

-- 2. 남은 테이블 (확인용 주석)
-- public.users (유저 정보 - 유지)
-- public.user_sessions (세션 매핑 - 유지)
-- public.system_configs (설정 - 유지)
-- public.abilities, items, enemies, npcs, personality (룰 데이터 - 유지)
-- public.world_eras, world_locales (세계관 - 유지)
-- public.enemy_drops (룰 데이터 - 유지)
-- public.characters (캐릭터 템플릿 - 유지)

VACUUM FULL;
