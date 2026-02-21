\c state_db

-- Functions
CREATE OR REPLACE FUNCTION public.sync_entity_to_graph() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    label_name text;
    is_active boolean := true;
    target_id uuid;
    target_name text;
    target_tid text := 'none';
    target_scid uuid;
    target_rule integer := 0;
BEGIN
    IF TG_TABLE_NAME = 'player' THEN
        label_name := 'Player'; target_id := NEW.player_id; target_name := NEW.name;
        target_tid := 'player'; target_scid := NULL; target_rule := 0;
    ELSIF TG_TABLE_NAME = 'npc' THEN
        label_name := 'NPC'; target_id := NEW.npc_id; target_name := NEW.name;
        target_tid := NEW.scenario_npc_id; target_scid := NEW.scenario_id;
        target_rule := NEW.rule_id;
        is_active := NOT COALESCE(NEW.is_departed, false);
    ELSIF TG_TABLE_NAME = 'enemy' THEN
        label_name := 'Enemy'; target_id := NEW.enemy_id; target_name := NEW.name;
        target_tid := NEW.scenario_enemy_id; target_scid := NEW.scenario_id;
        target_rule := NEW.rule_id;
        is_active := NOT COALESCE(NEW.is_defeated, false);
    ELSIF TG_TABLE_NAME = 'inventory' THEN
        label_name := 'Inventory'; target_id := NEW.inventory_id; target_name := 'Inventory';
        target_tid := 'none'; target_scid := NULL; target_rule := 0;
    ELSIF TG_TABLE_NAME = 'item' THEN
        label_name := 'Item'; target_id := NEW.item_id; target_name := NEW.name;
        target_tid := NEW.scenario_item_id; target_scid := NEW.scenario_id;
        target_rule := NEW.rule_id;
    ELSIF TG_TABLE_NAME = 'session' THEN
        label_name := 'Session'; target_id := NEW.session_id; target_name := 'Session';
        target_tid := NEW.current_act_id; target_scid := NEW.scenario_id;
        target_rule := 0;
    ELSE RETURN NEW;
    END IF;

    -- 공통 속성 업데이트
    EXECUTE format('
        SELECT * FROM ag_catalog.cypher(''state_db'', $$
            MERGE (n:%s { id: %L, session_id: %L })
            SET n.name = %L, n.active = %s, n.tid = %L, n.scenario_id = %L, n.rule_id = %s
        $$) AS (result ag_catalog.agtype);
    ', label_name, target_id::text, NEW.session_id::text, COALESCE(target_name, 'Unknown'), is_active::text, COALESCE(target_tid, 'none'), target_scid::text, target_rule::text);

    -- Session 전용 속성 추가 업데이트
    IF TG_TABLE_NAME = 'session' THEN
        EXECUTE format('
            SELECT * FROM ag_catalog.cypher(''state_db'', $$
                MATCH (n:Session { id: %L, session_id: %L })
                SET n.current_act = %s, n.current_sequence = %s,
                    n.current_act_id = %L, n.current_sequence_id = %L
            $$) AS (result ag_catalog.agtype);
        ', target_id::text, NEW.session_id::text,
        COALESCE(NEW.current_act, 1)::text, COALESCE(NEW.current_sequence, 1)::text,
        COALESCE(NEW.current_act_id, 'none'), COALESCE(NEW.current_sequence_id, 'none'));
    END IF;

    RETURN NEW;
END;
$_$;

CREATE OR REPLACE FUNCTION public.create_session(p_scenario_id uuid, p_current_act integer DEFAULT 1, p_current_sequence integer DEFAULT 1, p_location text DEFAULT NULL::text) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_session_id UUID;
    v_first_act_id VARCHAR(100);
    v_first_sequence_id VARCHAR(100);
BEGIN
    SELECT act_id INTO v_first_act_id
    FROM scenario_act
    WHERE scenario_id = p_scenario_id
    ORDER BY act_id
    LIMIT 1;

    SELECT sequence_id INTO v_first_sequence_id
    FROM scenario_sequence
    WHERE scenario_id = p_scenario_id
    ORDER BY sequence_id
    LIMIT 1;

    IF v_first_act_id IS NULL THEN
        v_first_act_id := CONCAT('act-', p_current_act::text);
    END IF;

    IF v_first_sequence_id IS NULL THEN
        v_first_sequence_id := CONCAT('seq-', p_current_sequence::text);
    END IF;

    INSERT INTO session (
        scenario_id,
        current_act,
        current_sequence,
        current_act_id,
        current_sequence_id,
        location,
        status
    )
    VALUES (
        p_scenario_id,
        p_current_act,
        p_current_sequence,
        v_first_act_id,
        v_first_sequence_id,
        p_location,
        'active'
    )
    RETURNING session_id INTO new_session_id;

    RETURN new_session_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_enemies() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    MASTER_SESSION_ID CONSTANT UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    INSERT INTO enemy (
        enemy_id, entity_type, name, description, session_id,
        assigned_sequence_id, assigned_location, scenario_id, scenario_enemy_id,
        rule_id, tags,
        hp, max_hp, attack, defense,
        dropped_items, is_defeated
    )
    SELECT
        gen_random_uuid(), src.entity_type, src.name, src.description, NEW.session_id,
        src.assigned_sequence_id, src.assigned_location, src.scenario_id, src.scenario_enemy_id,
        src.rule_id, src.tags,
        src.hp, src.max_hp, src.attack, src.defense,
        src.dropped_items, false
    FROM enemy src
    WHERE src.session_id = MASTER_SESSION_ID
      AND src.scenario_id = NEW.scenario_id;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_graph_data() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    MASTER_SESSION_ID CONSTANT UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    EXECUTE format('
        SELECT * FROM ag_catalog.cypher(''state_db'', $$
            MATCH (v1)-[r:RELATION]->(v2)
            WHERE r.session_id = %L AND r.scenario_id = %L
            MATCH (nv1 {session_id: %L}), (nv2 {session_id: %L})
            WHERE nv1.tid = v1.tid AND nv2.tid = v2.tid
              AND nv1.tid <> ''none''
            CREATE (nv1)-[nr:RELATION {
                relation_type: r.relation_type,
                affinity: r.affinity,
                session_id: %L,
                scenario_id: %L,
                active: true,
                activated_turn: 0
            }]->(nv2)
        $$) AS (result ag_catalog.agtype);
    ', MASTER_SESSION_ID::text, NEW.scenario_id::text, NEW.session_id::text, NEW.session_id::text, NEW.session_id::text, NEW.scenario_id::text);

    RETURN NEW;
END;
$_$;

CREATE OR REPLACE FUNCTION public.initialize_items() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    MASTER_SESSION_ID CONSTANT UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    INSERT INTO item (
        item_id, rule_id, entity_type, session_id,
        scenario_id, scenario_item_id, name, description,
        item_type, meta, created_at
    )
    SELECT
        gen_random_uuid(), rule_id, entity_type, NEW.session_id,
        scenario_id, scenario_item_id, name, description,
        item_type, meta, NOW()
    FROM item
    WHERE session_id = MASTER_SESSION_ID
      AND scenario_id = NEW.scenario_id;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_npc_relations() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_player_id UUID;
    v_npc_record RECORD;
BEGIN
    SELECT player_id INTO v_player_id
    FROM player
    WHERE session_id = NEW.session_id
    LIMIT 1;

    IF v_player_id IS NOT NULL THEN
        FOR v_npc_record IN
            SELECT npc_id FROM npc WHERE session_id = NEW.session_id
        LOOP
            INSERT INTO player_npc_relations (
                player_id, npc_id, affinity_score, relation_type, created_at
            )
            VALUES (
                v_player_id, v_npc_record.npc_id, 50, 'neutral', NEW.started_at
            ) ON CONFLICT (player_id, npc_id) DO NOTHING;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_npcs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    MASTER_SESSION_ID CONSTANT UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    INSERT INTO npc (
        npc_id, entity_type, name, description, session_id,
        assigned_sequence_id, assigned_location, scenario_id, scenario_npc_id,
        rule_id, tags,
        hp, mp, str, dex, int, lux, san,
        is_departed
    )
    SELECT
        gen_random_uuid(), n.entity_type, n.name, n.description, NEW.session_id,
        n.assigned_sequence_id, n.assigned_location, n.scenario_id, n.scenario_npc_id,
        n.rule_id, n.tags,
        n.hp, n.mp, n.str, n.dex, n.int, n.lux, n.san,
        false
    FROM npc n
    WHERE n.session_id = MASTER_SESSION_ID
      AND n.scenario_id = NEW.scenario_id;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_phase() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO phase (
        phase_id, session_id, previous_phase, new_phase,
        turn_at_transition, transition_reason, transitioned_at
    )
    VALUES (
        gen_random_uuid(), NEW.session_id, NULL, NEW.current_phase,
        NEW.current_turn, 'session_start', NEW.started_at
    );
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_player() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO player (
        session_id, name, description, hp, mp, san, created_at
    )
    VALUES (
        NEW.session_id, 'Player', 'Default player character',
        100, 50, 10, NEW.started_at
    );
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.initialize_player_inventory() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    v_player_id UUID;
    v_inventory_id UUID;
    params_text text;
    cypher_query text;
BEGIN
    SELECT player_id INTO v_player_id
    FROM player
    WHERE session_id = NEW.session_id
    LIMIT 1;

    IF v_player_id IS NOT NULL THEN
        INSERT INTO inventory (
            session_id, capacity, weight_limit, created_at
        )
        VALUES (
            NEW.session_id, NULL, NULL, NEW.started_at
        )
        RETURNING inventory_id INTO v_inventory_id;

        params_text := jsonb_build_object(
            'player_id', v_player_id,
            'inventory_id', v_inventory_id,
            'session_id', NEW.session_id
        )::text;

        cypher_query := '
            MATCH (p:Player {id: $player_id, session_id: $session_id})
            MATCH (inv:Inventory {id: $inventory_id, session_id: $session_id})
            CREATE (p)-[:HAS_INVENTORY {
                active: true,
                activated_turn: 0,
                session_id: $session_id
            }]->(inv)
        ';
        EXECUTE format('
            SELECT * FROM ag_catalog.cypher(''state_db'', $$%s$$, $1) AS (result ag_catalog.agtype);
        ', cypher_query)
        USING params_text::ag_catalog.agtype;
    END IF;
    RETURN NEW;
END;
$_$;

CREATE OR REPLACE FUNCTION public.initialize_turn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO turn (
        turn_id, session_id, turn_number, turn_type, state_changes, created_at
    )
    VALUES (
        gen_random_uuid(), NEW.session_id, 0, 'initial_state', '{}'::jsonb, NEW.started_at
    );
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.update_session_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Utility Functions
CREATE OR REPLACE FUNCTION public.update_enemy_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.update_inventory_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.update_npc_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.update_player_inventory_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.update_player_npc_relations_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.update_player_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.update_scenario_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;
CREATE OR REPLACE FUNCTION public.set_scenario_published_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.is_published = true AND (OLD.is_published IS FALSE OR OLD.is_published IS NULL) THEN NEW.published_at = NOW(); END IF; RETURN NEW; END; $$;

-- Triggers
DROP TRIGGER IF EXISTS trg_scenario_published ON public.scenario;
CREATE TRIGGER trg_scenario_published BEFORE UPDATE ON public.scenario FOR EACH ROW EXECUTE FUNCTION public.set_scenario_published_at();

DROP TRIGGER IF EXISTS trg_scenario_updated_at ON public.scenario;
CREATE TRIGGER trg_scenario_updated_at BEFORE UPDATE ON public.scenario FOR EACH ROW EXECUTE FUNCTION public.update_scenario_updated_at();

DROP TRIGGER IF EXISTS trigger_100_session_init_turn ON public.session;
CREATE TRIGGER trigger_100_session_init_turn AFTER INSERT ON public.session FOR EACH ROW EXECUTE FUNCTION public.initialize_turn();

DROP TRIGGER IF EXISTS trigger_110_session_init_player ON public.session;
CREATE TRIGGER trigger_110_session_init_player AFTER INSERT ON public.session FOR EACH ROW EXECUTE FUNCTION public.initialize_player();

DROP TRIGGER IF EXISTS trigger_120_session_init_inventory ON public.session;
CREATE TRIGGER trigger_120_session_init_inventory AFTER INSERT ON public.session FOR EACH ROW EXECUTE FUNCTION public.initialize_player_inventory();

DROP TRIGGER IF EXISTS trigger_200_session_copy_items ON public.session;
CREATE TRIGGER trigger_200_session_copy_items AFTER INSERT ON public.session FOR EACH ROW WHEN ((new.session_id <> '00000000-0000-0000-0000-000000000000'::uuid)) EXECUTE FUNCTION public.initialize_items();

DROP TRIGGER IF EXISTS trigger_210_session_copy_npcs ON public.session;
CREATE TRIGGER trigger_210_session_copy_npcs AFTER INSERT ON public.session FOR EACH ROW WHEN ((new.session_id <> '00000000-0000-0000-0000-000000000000'::uuid)) EXECUTE FUNCTION public.initialize_npcs();

DROP TRIGGER IF EXISTS trigger_220_session_copy_enemies ON public.session;
CREATE TRIGGER trigger_220_session_copy_enemies AFTER INSERT ON public.session FOR EACH ROW WHEN ((new.session_id <> '00000000-0000-0000-0000-000000000000'::uuid)) EXECUTE FUNCTION public.initialize_enemies();

DROP TRIGGER IF EXISTS trigger_300_sync_player_graph ON public.player;
CREATE TRIGGER trigger_300_sync_player_graph AFTER INSERT OR UPDATE ON public.player FOR EACH ROW EXECUTE FUNCTION public.sync_entity_to_graph();

DROP TRIGGER IF EXISTS trigger_305_sync_session_graph ON public.session;
CREATE TRIGGER trigger_305_sync_session_graph AFTER INSERT OR UPDATE ON public.session FOR EACH ROW EXECUTE FUNCTION public.sync_entity_to_graph();

DROP TRIGGER IF EXISTS trigger_310_sync_npc_graph ON public.npc;
CREATE TRIGGER trigger_310_sync_npc_graph AFTER INSERT OR UPDATE ON public.npc FOR EACH ROW EXECUTE FUNCTION public.sync_entity_to_graph();

DROP TRIGGER IF EXISTS trigger_320_sync_enemy_graph ON public.enemy;
CREATE TRIGGER trigger_320_sync_enemy_graph AFTER INSERT OR UPDATE ON public.enemy FOR EACH ROW EXECUTE FUNCTION public.sync_entity_to_graph();

DROP TRIGGER IF EXISTS trigger_330_sync_inventory_graph ON public.inventory;
CREATE TRIGGER trigger_330_sync_inventory_graph AFTER INSERT OR UPDATE ON public.inventory FOR EACH ROW EXECUTE FUNCTION public.sync_entity_to_graph();

DROP TRIGGER IF EXISTS trigger_340_sync_item_graph ON public.item;
CREATE TRIGGER trigger_340_sync_item_graph AFTER INSERT OR UPDATE ON public.item FOR EACH ROW EXECUTE FUNCTION public.sync_entity_to_graph();

DROP TRIGGER IF EXISTS trigger_900_session_finalize_graph ON public.session;
CREATE TRIGGER trigger_900_session_finalize_graph AFTER INSERT ON public.session FOR EACH ROW WHEN ((new.session_id <> '00000000-0000-0000-0000-000000000000'::uuid)) EXECUTE FUNCTION public.initialize_graph_data();

DROP TRIGGER IF EXISTS trigger_update_session_timestamp ON public.session;
CREATE TRIGGER trigger_update_session_timestamp BEFORE UPDATE ON public.session FOR EACH ROW EXECUTE FUNCTION public.update_session_timestamp();

-- Entity updated_at triggers
DROP TRIGGER IF EXISTS trg_enemy_updated_at ON public.enemy;
CREATE TRIGGER trg_enemy_updated_at BEFORE UPDATE ON public.enemy FOR EACH ROW EXECUTE FUNCTION public.update_enemy_updated_at();

DROP TRIGGER IF EXISTS trg_inventory_updated_at ON public.inventory;
CREATE TRIGGER trg_inventory_updated_at BEFORE UPDATE ON public.inventory FOR EACH ROW EXECUTE FUNCTION public.update_inventory_updated_at();

DROP TRIGGER IF EXISTS trg_npc_updated_at ON public.npc;
CREATE TRIGGER trg_npc_updated_at BEFORE UPDATE ON public.npc FOR EACH ROW EXECUTE FUNCTION public.update_npc_updated_at();

DROP TRIGGER IF EXISTS trg_player_updated_at ON public.player;
CREATE TRIGGER trg_player_updated_at BEFORE UPDATE ON public.player FOR EACH ROW EXECUTE FUNCTION public.update_player_updated_at();
