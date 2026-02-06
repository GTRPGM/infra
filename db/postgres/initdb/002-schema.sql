create table public.abilities
(
    ability_id  serial
        primary key,
    name        varchar(20) not null
        unique,
    description text
);

comment on table public.abilities is '캐릭터의 기본 능력치(난폭함, 똘똘함, 영리함) 정의';

comment on column public.abilities.ability_id is '능력치 고유 식별자';

comment on column public.abilities.name is '능력치 이름 (예: 난폭함)';

comment on column public.abilities.description is '능력치 활용 범위 및 설명';

alter table public.abilities
    owner to gtrpgm;

create table public.enemies
(
    enemy_id        integer      default nextval('bestiary_mob_id_seq'::regclass) not null
        primary key,
    name            varchar(50)                                                   not null,
    base_difficulty integer                                                       not null,
    description     text,
    type            varchar(30),
    created_at      timestamp    default CURRENT_TIMESTAMP,
    creator         varchar(255) default 'GM'::character varying
);

comment on table public.enemies is '던전에서 조우하는 적과 NPC 데이터';

comment on column public.enemies.enemy_id is '몬스터 고유 식별자';

comment on column public.enemies.name is '몬스터 이름';

comment on column public.enemies.base_difficulty is '전투 난이도 (동시에 HP로 활용됨)';

comment on column public.enemies.description is '특수 행동 및 외형 묘사';

comment on column public.enemies.type is '적의 유형 (예: 식물/곤충, 기계, 정령, 심연 등)';

comment on column public.enemies.created_at is '데이터 생성 일시';

comment on column public.enemies.creator is '생성자 (기본값 GM)';

alter table public.enemies
    owner to gtrpgm;

create table public.disposition_levels
(
    level_id       serial
        primary key,
    level_name     varchar(20) not null,
    min_score      integer     not null,
    max_score      integer     not null,
    price_modifier numeric(3, 2) default 1.0,
    description    text
);

comment on table public.disposition_levels is '호감도 점수에 따른 관계 단계 및 상점 이용 혜택 정의';

comment on column public.disposition_levels.level_name is '단계 명칭 (예: 우호적, 적대적)';

comment on column public.disposition_levels.min_score is '해당 단계에 진입하기 위한 최소 점수';

comment on column public.disposition_levels.max_score is '해당 단계의 최대 점수';

comment on column public.disposition_levels.price_modifier is '상점 이용 시 가격 수정치 (예: 0.9는 10% 할인)';

comment on column public.disposition_levels.description is '해당 관계 단계에 대한 상세 설명 및 게임 내 작용';

alter table public.disposition_levels
    owner to gtrpgm;

create table public.items
(
    item_id      serial
        primary key,
    name         varchar(50)   not null,
    type         item_category not null,
    effect_value integer      default 0,
    description  text,
    weight       integer      default 1,
    grade        varchar(20),
    base_price   integer      default 0,
    created_at   timestamp    default CURRENT_TIMESTAMP,
    creator      varchar(255) default 'GM'::character varying
);

comment on table public.items is '세계관 내 존재하는 모든 아이템 도감';

comment on column public.items.item_id is '아이템 고유 식별자';

comment on column public.items.name is '아이템 이름';

comment on column public.items.type is '아이템 분류 (ENUM: 무기, 방어구, 도구, 소모품, 기타)';

comment on column public.items.effect_value is '아이템의 수치적 효과 (공격력, 방어력 등)';

comment on column public.items.description is '아이템의 상세 용도 및 서사적 설명';

comment on column public.items.weight is '소지품 슬롯 차지 점수 (기본 1)';

comment on column public.items.grade is '아이템 등급 (예: Common, Rare, Epic, Legendary)';

comment on column public.items.base_price is '아이템의 기본 시장 가치 (거래 시 기준 가격)';

comment on column public.items.created_at is '데이터 생성 일시';

comment on column public.items.creator is '생성자 (기본값 GM)';

alter table public.items
    owner to gtrpgm;

create table public.characters
(
    character_id     integer default nextval('backgrounds_bg_id_seq'::regclass) not null
        constraint backgrounds_pkey
            primary key,
    state            varchar(20)                                                not null,
    dice_roll        integer
        constraint backgrounds_dice_roll_check
            check ((dice_roll >= 1) AND (dice_roll <= 6)),
    class_name       varchar(50)                                                not null,
    ability_id       integer
        constraint backgrounds_ability_id_fkey
            references public.abilities,
    stat_bonus       integer default 1,
    starting_item_id integer
        constraint backgrounds_starting_item_id_fkey
            references public.items
);

comment on table public.characters is '캐릭터 생성 시 결정되는 소년기, 직업, 전쟁 배경 정보';

comment on column public.characters.character_id is '캐릭터 고유 식별자';

comment on column public.characters.state is '캐릭터 상태 분류 (예: 소년기, 직업, 전쟁 중)';

comment on column public.characters.dice_roll is '결정에 사용되는 주사위 눈금 (1~6)';

comment on column public.characters.class_name is '직업명 (예: 연기 닦이, 유랑민)';

comment on column public.characters.ability_id is '해당 배경 선택 시 향상되는 능력치 ID';

comment on column public.characters.stat_bonus is '능력치 상승량';

comment on column public.characters.starting_item_id is '시작 시 지급되는 기본 아이템 ID';

alter table public.characters
    owner to gtrpgm;

create table public.enemy_drops
(
    drop_id      serial
        primary key,
    enemy_id     integer
        references public.enemies
            on delete cascade,
    item_id      integer
        references public.items
            on delete cascade,
    drop_rate    numeric(5, 2) default 1.0 not null,
    min_quantity integer       default 1,
    max_quantity integer       default 1,
    created_at   timestamp     default CURRENT_TIMESTAMP,
    creator      varchar(255)  default 'GM'::character varying
);

comment on table public.enemy_drops is '적(Enemy) 처치 시 획득 가능한 전리품과 드롭 규칙을 정의하는 사전';

comment on column public.enemy_drops.drop_id is '드롭 규칙 고유 식별자';

comment on column public.enemy_drops.enemy_id is '아이템을 드롭하는 적 개체의 ID (enemies 테이블 참조)';

comment on column public.enemy_drops.item_id is '드롭되는 아이템의 ID (items 테이블 참조)';

comment on column public.enemy_drops.drop_rate is '해당 아이템이 드롭될 확률 (단위: %, 예: 0.50은 0.5% 확률)';

comment on column public.enemy_drops.min_quantity is '아이템 드롭 시 결정될 수 있는 최소 수량';

comment on column public.enemy_drops.max_quantity is '아이템 드롭 시 결정될 수 있는 최대 수량';

comment on column public.enemy_drops.created_at is '데이터 생성 일시';

comment on column public.enemy_drops.creator is '생성자 (기본값 GM)';

alter table public.enemy_drops
    owner to gtrpgm;

create table public.npcs
(
    npc_id             serial
        primary key,
    name               varchar(50) not null,
    disposition        varchar(20)  default '중립'::character varying,
    occupation         varchar(50),
    dialogue_style     text,
    description        text,
    base_difficulty    integer      default 10,
    combat_description text,
    created_at         timestamp    default CURRENT_TIMESTAMP,
    creator            varchar(255) default 'GM'::character varying
);

comment on table public.npcs is '세계관 내 NPC(상호작용 가능 인물) 도감';

comment on column public.npcs.npc_id is 'NPC 고유 식별자';

comment on column public.npcs.disposition is '초기 성향 (우호적, 적대적, 중립 등)';

comment on column public.npcs.occupation is 'NPC의 직업이나 역할';

comment on column public.npcs.dialogue_style is 'LLM이 대사를 생성할 때 참고할 말투나 성격 설정';

comment on column public.npcs.base_difficulty is '전투 발생 시 기준 난이도(HP)';

comment on column public.npcs.combat_description is '전투 시 NPC의 행동 패턴 묘사';

comment on column public.npcs.created_at is '데이터 생성 일시';

comment on column public.npcs.creator is '생성자 (기본값 GM)';

alter table public.npcs
    owner to gtrpgm;

create table public.npc_inventories
(
    inventory_id      serial
        primary key,
    npc_id            integer
        references public.npcs,
    item_id           integer
        references public.items,
    is_infinite_stock boolean      default false,
    creator           varchar(255) default 'GM'::character varying
);

comment on table public.npc_inventories is 'NPC가 기본적으로 판매하거나 소유한 아이템 목록';

comment on column public.npc_inventories.npc_id is '판매 주체 NPC 식별자';

comment on column public.npc_inventories.item_id is '판매되는 아이템 식별자';

comment on column public.npc_inventories.is_infinite_stock is '재고 무한 여부 (True일 경우 계속 구매 가능)';

comment on column public.npc_inventories.creator is '생성자 (기본값 GM)';

alter table public.npc_inventories
    owner to gtrpgm;

create table public.personality
(
    id          varchar(50)  not null
        primary key,
    category    varchar(50)  not null,
    label       varchar(100) not null,
    description text,
    opposite    text[]
);

comment on table public.personality is 'NPC 성격 사전 테이블';

comment on column public.personality.id is '성격 고유 식별자 (snake_case 권장)';

comment on column public.personality.category is '성격 카테고리 (emotion, hobby, socializing 등)';

comment on column public.personality.label is '사용자에게 표시될 성격 명칭';

comment on column public.personality.description is '해당 성격에 대한 구체적인 정의';

comment on column public.personality.opposite is '상충하는 성격 ID들의 배열';

alter table public.personality
    owner to gtrpgm;

create table public.system_configs
(
    config_key   varchar(50) not null
        primary key,
    config_value integer,
    description  text
);

comment on table public.system_configs is '게임 규칙 관련 상수값 관리 (난이도, 초기 체력 등)';

comment on column public.system_configs.config_key is '설정 키값 (예: HP_START)';

comment on column public.system_configs.config_value is '정수형 설정값';

comment on column public.system_configs.description is '설정 항목에 대한 상세 설명';

alter table public.system_configs
    owner to gtrpgm;

create table public.users
(
    user_id       serial
        primary key,
    username      varchar(50) not null
        unique,
    password_hash text        not null,
    email         varchar(100)
        unique,
    created_at    timestamp default CURRENT_TIMESTAMP,
    is_active     boolean   default true
);

comment on table public.users is 'GTRPGM 시스템 사용자 계정 정보';

comment on column public.users.user_id is '사용자 고유 식별자';

comment on column public.users.username is '로그인용 사용자 아이디';

comment on column public.users.password_hash is '암호화된 비밀번호 해시값';

comment on column public.users.email is '복구용 이메일 주소';

comment on column public.users.created_at is '계정 생성 일시';

comment on column public.users.is_active is '계정 활성 상태 여부';

alter table public.users
    owner to gtrpgm;

create table public.generation_logs
(
    gen_id             serial
        primary key,
    entity_type        varchar(20) not null,
    generated_enemy_id integer
        references public.enemies,
    generated_item_id  integer
        references public.items,
    generated_npc_id   integer
        references public.npcs,
    prompt_used        text,
    is_approved        boolean   default false,
    rejection_reason   text,
    created_at         timestamp default CURRENT_TIMESTAMP,
    requested_by       integer
        references public.users
);

comment on table public.generation_logs is 'LLM 생성 데이터의 통합 이력 관리';

comment on column public.generation_logs.gen_id is '생성 로그 고유 식별자';

comment on column public.generation_logs.entity_type is '생성된 개체 유형 (예: Enemy, Item, NPC)';

comment on column public.generation_logs.generated_enemy_id is '생성된 몬스터 식별자 (Enemy 타입일 경우)';

comment on column public.generation_logs.generated_item_id is '생성된 아이템 식별자 (Item 타입일 경우)';

comment on column public.generation_logs.generated_npc_id is '생성된 NPC 식별자 (NPC 타입일 경우)';

comment on column public.generation_logs.prompt_used is 'LLM 생성에 사용된 핵심 프롬프트 또는 요청 내용';

comment on column public.generation_logs.is_approved is 'GM 또는 검증 로직에 의한 승인 여부 (True일 경우에만 실제 게임에 사용)';

comment on column public.generation_logs.rejection_reason is '세계관 불일치 등의 이유로 반려되었을 경우 그 사유';

comment on column public.generation_logs.created_at is '데이터가 생성된 일시';

comment on column public.generation_logs.requested_by is '데이터 생성을 요청한 사용자(GM) ID';

alter table public.generation_logs
    owner to gtrpgm;

create table public.players
(
    player_id  serial
        primary key,
    user_id    integer     not null
        references public.users
            on delete cascade,
    name       varchar(50) not null,
    gold       integer   default 500
        constraint check_positive_gold_player
            check (gold >= 0),
    level      integer   default 1,
    experience integer   default 0,
    current_hp integer,
    max_hp     integer,
    created_at timestamp default CURRENT_TIMESTAMP
);

comment on table public.players is '사용자가 소유한 개별 플레이어 캐릭터 정보';

comment on column public.players.user_id is '해당 캐릭터를 소유한 계정 ID (users 참조)';

comment on column public.players.gold is '캐릭터가 보유한 자금';

alter table public.players
    owner to gtrpgm;

create table public.player_abilities
(
    player_id  integer not null
        references public.players
            on delete cascade,
    ability_id integer not null
        references public.abilities
            on delete cascade,
    score      integer default 10,
    primary key (player_id, ability_id)
);

comment on table public.player_abilities is '플레이어별 보유 능력치 수치 기록';

comment on column public.player_abilities.score is '플레이어가 해당 능력치를 보유한 정도 (예: 난폭함 15)';

alter table public.player_abilities
    owner to gtrpgm;

create table public.world_eras
(
    era_id        serial
        primary key,
    era_name      varchar(50) not null,
    stat_modifier numeric(3, 2) default 1.0,
    description   text,
    created_at    timestamp     default CURRENT_TIMESTAMP
);

comment on table public.world_eras is '게임의 시간적 배경 또는 환경적 변수 (예: 개척 시대, 심연의 밤)';

comment on column public.world_eras.stat_modifier is '해당 시간대에 적용되는 적들의 능력치 배율';

comment on column public.world_eras.created_at is '데이터 생성 일시';

alter table public.world_eras
    owner to gtrpgm;

create table public.world_locales
(
    locale_id   serial
        primary key,
    name        varchar(100) not null,
    theme       varchar(50),
    danger_min  integer      default 1,
    danger_max  integer      default 10,
    description text,
    created_at  timestamp    default CURRENT_TIMESTAMP,
    creator     varchar(255) default 'GM'::character varying
);

comment on table public.world_locales is '게임 내 탐험 가능한 지역 및 공간적 테마 정의';

comment on column public.world_locales.theme is '지역의 속성 (예: 습한 동굴, 버려진 기지, 차원 틈새)';

comment on column public.world_locales.danger_min is '해당 지역에서 생성될 적의 최소 난이도';

comment on column public.world_locales.created_at is '데이터 생성 일시';

alter table public.world_locales
    owner to gtrpgm;

create table public.play_logs
(
    id               serial
        primary key,
    turn_id          varchar(100) not null
        unique,
    session_id       varchar(50)  not null,
    act_id           varchar(50),
    sequence_id      varchar(50),
    sequence_type    varchar(50),
    sequence_seq     integer,
    turn_seq         integer      not null,
    active_entity_id varchar(50)  not null,
    user_input       text         not null,
    final_output     text,
    state_diff       jsonb,
    world_snapshot   jsonb,
    commit_id        varchar(50),
    created_at       timestamp with time zone default CURRENT_TIMESTAMP,
    meta_info        jsonb
);

alter table public.play_logs
    owner to gtrpgm;

create index idx_play_logs_session_id
    on public.play_logs (session_id);

create unique index idx_play_logs_session_turn_seq
    on public.play_logs (session_id, turn_seq);

create index idx_play_logs_hierarchy
    on public.play_logs (session_id, act_id, sequence_id);

create table public.scenario
(
    scenario_id                uuid        default gen_random_uuid() not null
        primary key,
    title                      varchar(200)                          not null
        constraint unique_scenario_title
            unique,
    description                text,
    author                     varchar(100),
    version                    varchar(20) default '1.0.0'::character varying,
    difficulty                 varchar(20) default 'normal'::character varying,
    genre                      varchar(50),
    tags                       text[]      default ARRAY []::text[],
    total_acts                 integer     default 3                 not null
        constraint scenario_total_acts_check
            check (total_acts > 0),
    estimated_duration_minutes integer,
    is_published               boolean     default false             not null,
    is_active                  boolean     default true              not null,
    created_at                 timestamp   default now()             not null,
    updated_at                 timestamp   default now()             not null,
    published_at               timestamp,
    play_count                 integer     default 0,
    completion_count           integer     default 0,
    average_rating             numeric(3, 2)
);

alter table public.scenario
    owner to gtrpgm;

create index idx_scenario_is_published
    on public.scenario (is_published);

create index idx_scenario_is_active
    on public.scenario (is_active);

create index idx_scenario_difficulty
    on public.scenario (difficulty);

create index idx_scenario_genre
    on public.scenario (genre);

create index idx_scenario_created_at
    on public.scenario (created_at desc);

create table public.session
(
    session_id          uuid                  default gen_random_uuid()               not null
        primary key,
    scenario_id         uuid                                                          not null
        references public.scenario
            on delete restrict,
    current_act         integer               default 1                               not null,
    current_sequence    integer               default 1                               not null,
    current_act_id      varchar(100)          default 'act-1'::character varying,
    current_sequence_id varchar(100)          default 'seq-1'::character varying,
    current_phase       public.phase_type     default 'dialogue'::public.phase_type   not null,
    current_turn        integer               default 0                               not null,
    location            text,
    status              public.session_status default 'active'::public.session_status not null,
    started_at          timestamp             default now()                           not null,
    ended_at            timestamp,
    paused_at           timestamp,
    created_at          timestamp             default now()                           not null,
    updated_at          timestamp             default now()                           not null
);

comment on table public.session is '플레이 세션 전역 컨테이너 - phase 중심 상태 관리';

comment on column public.session.session_id is '플레이 세션 식별자';

comment on column public.session.scenario_id is '진행 중인 시나리오 ID';

comment on column public.session.current_act is '현재 act 번호';

comment on column public.session.current_sequence is '현재 sequence 번호';

comment on column public.session.current_phase is '현재 플레이 상태 (exploration/combat/dialogue/rest)';

comment on column public.session.current_turn is '상태 확정 턴 카운터';

comment on column public.session.status is '세션 상태 (active/paused/ended)';

alter table public.session
    owner to gtrpgm;

create index idx_session_scenario_id
    on public.session (scenario_id);

create index idx_session_status
    on public.session (status);

create index idx_session_started_at
    on public.session (started_at desc);

create table public.scenario_act
(
    scenario_id     uuid         not null
        references public.scenario
            on delete cascade,
    act_id          varchar(100) not null,
    act_name        varchar(200) not null,
    act_description text,
    exit_criteria   text,
    sequence_ids    text[],
    metadata        jsonb default '{}'::jsonb,
    primary key (scenario_id, act_id)
);

comment on table public.scenario_act is '시나리오의 진행 단계(Act)별 상세 정보 및 조건 관리';

alter table public.scenario_act
    owner to gtrpgm;

create table public.scenario_sequence
(
    scenario_id   uuid                    not null
        references public.scenario
            on delete cascade,
    sequence_id   varchar(100)            not null,
    sequence_name varchar(200)            not null,
    location_name varchar(200),
    description   text,
    goal          text,
    exit_triggers jsonb     default '[]'::jsonb,
    metadata      jsonb     default '{}'::jsonb,
    created_at    timestamp default now() not null,
    updated_at    timestamp default now() not null,
    primary key (scenario_id, sequence_id)
);

comment on table public.scenario_sequence is '시나리오의 세부 진행 단위(Sequence)별 목표 및 탈출 조건 관리';

alter table public.scenario_sequence
    owner to gtrpgm;

create table public.player
(
    player_id   uuid        default gen_random_uuid()                                                                                                         not null
        primary key,
    entity_type varchar(50) default 'player'::character varying                                                                                               not null,
    name        varchar(20)                                                                                                                                   not null,
    description text        default ''::text,
    session_id  uuid                                                                                                                                          not null
        references public.session
            on delete cascade,
    created_at  timestamp   default now()                                                                                                                     not null,
    updated_at  timestamp   default now()                                                                                                                     not null,
    tags        text[]      default ARRAY ['player'::text],
    state       jsonb       default '{"boolean": {}, "numeric": {"HP": 100, "MP": 50, "DEX": null, "INT": null, "LUX": null, "SAN": 10, "STR": null}}'::jsonb not null,
    relations   jsonb       default '[]'::jsonb
);

comment on table public.player is '플레이어 캐릭터 정보 및 세션별 상태 관리';

alter table public.player
    owner to gtrpgm;

create index idx_player_session_id
    on public.player (session_id);

create table public.npc
(
    npc_id               uuid        default gen_random_uuid()                                                                                                         not null
        primary key,
    entity_type          varchar(50) default 'npc'::character varying                                                                                                  not null,
    name                 varchar(100)                                                                                                                                  not null,
    description          text        default ''::text,
    session_id           uuid                                                                                                                                          not null
        references public.session
            on delete cascade,
    assigned_sequence_id varchar(100),
    assigned_location    varchar(200),
    scenario_id          uuid                                                                                                                                          not null,
    scenario_npc_id      varchar(100)                                                                                                                                  not null,
    created_at           timestamp   default now()                                                                                                                     not null,
    updated_at           timestamp   default now()                                                                                                                     not null,
    tags                 text[]      default ARRAY []::text[],
    state                jsonb       default '{"boolean": {}, "numeric": {"HP": 100, "MP": 50, "DEX": null, "INT": null, "LUX": null, "SAN": 10, "STR": null}}'::jsonb not null,
    relations            jsonb       default '[]'::jsonb,
    is_departed          boolean     default false                                                                                                                     not null,
    departed_at          timestamp
);

comment on table public.npc is 'NPC 캐릭터 정보 및 세션별 상태 관리';

alter table public.npc
    owner to gtrpgm;

create index idx_npc_session_id
    on public.npc (session_id);

create index idx_npc_scenario_id
    on public.npc (scenario_id);

create index idx_npc_scenario_npc_id
    on public.npc (scenario_npc_id);

create table public.enemy
(
    enemy_id             uuid        default gen_random_uuid()                                                                                                          not null
        primary key,
    entity_type          varchar(50) default 'enemy'::character varying                                                                                                 not null,
    name                 varchar(100)                                                                                                                                   not null,
    description          text        default ''::text,
    session_id           uuid                                                                                                                                           not null
        references public.session
            on delete cascade,
    assigned_sequence_id varchar(100),
    assigned_location    varchar(200),
    scenario_id          uuid                                                                                                                                           not null,
    scenario_enemy_id    varchar(100)                                                                                                                                   not null,
    created_at           timestamp   default now()                                                                                                                      not null,
    updated_at           timestamp   default now()                                                                                                                      not null,
    tags                 text[]      default ARRAY []::text[],
    state                jsonb       default '{"boolean": {}, "numeric": {"HP": 100, "MP": 0, "DEX": null, "INT": null, "LUX": null, "SAN": null, "STR": null}}'::jsonb not null,
    is_defeated          boolean     default false                                                                                                                      not null,
    defeated_at          timestamp,
    relations            jsonb       default '[]'::jsonb,
    dropped_items        uuid[]      default ARRAY []::uuid[]
);

alter table public.enemy
    owner to gtrpgm;

create index idx_enemy_session_id
    on public.enemy (session_id);

create index idx_enemy_scenario_id
    on public.enemy (scenario_id);

create index idx_enemy_scenario_enemy_id
    on public.enemy (scenario_enemy_id);

create table public.item
(
    item_id          uuid        default gen_random_uuid()         not null
        primary key,
    entity_type      varchar(10) default 'item'::character varying not null,
    session_id       uuid                                          not null
        references public.session
            on delete cascade,
    scenario_id      uuid                                          not null,
    scenario_item_id varchar(100)                                  not null,
    name             varchar(20)                                   not null,
    description      text        default ''::text,
    item_type        varchar(20) default 'misc'::character varying,
    meta             jsonb       default '{}'::jsonb,
    created_at       timestamp   default now()                     not null
);

comment on table public.item is 'RuleEngine에서 관리하는 아이템 정의 테이블';

alter table public.item
    owner to gtrpgm;

create index idx_item_session_id
    on public.item (session_id);

create index idx_item_scenario_id
    on public.item (scenario_id);

create index idx_item_scenario_item_id
    on public.item (scenario_item_id);

create index idx_item_type
    on public.item (item_type);

create table public.phase
(
    phase_id           uuid      default gen_random_uuid() not null
        primary key,
    session_id         uuid                                not null
        constraint fk_phase_session
            references public.session
            on delete cascade,
    previous_phase     public.phase_type,
    new_phase          public.phase_type                   not null,
    turn_at_transition integer                             not null,
    transition_reason  text,
    transitioned_at    timestamp default now()             not null,
    constraint check_phase_change
        check (previous_phase IS DISTINCT FROM new_phase)
);

comment on table public.phase is 'Phase 전환 이력 추적 (디버깅 및 리플레이용)';

alter table public.phase
    owner to gtrpgm;

create index idx_phase_session_id
    on public.phase (session_id);

create index idx_phase_transitioned_at
    on public.phase (transitioned_at desc);

create index idx_phase_new_phase
    on public.phase (new_phase);

create table public.phase_rules
(
    phase           public.phase_type       not null
        primary key,
    description     text                    not null,
    rule_scope      text[]                  not null,
    allowed_actions text[]                  not null,
    created_at      timestamp default now() not null
);

alter table public.phase_rules
    owner to gtrpgm;

create table public.turn
(
    turn_id          uuid      default gen_random_uuid() not null
        primary key,
    session_id       uuid                                not null
        constraint fk_turn_session
            references public.session
            on delete cascade,
    turn_number      integer                             not null,
    phase_at_turn    public.phase_type                   not null,
    turn_type        varchar(50)                         not null,
    state_changes    jsonb     default '{}'::jsonb,
    related_entities uuid[],
    created_at       timestamp default now()             not null
);

comment on table public.turn is '상태 변화 발생 시마다 기록되는 턴 이력 테이블';

comment on column public.turn.turn_id is '턴 레코드 고유 ID';

comment on column public.turn.turn_number is '상태 변화에 따른 순차적 턴 번호';

alter table public.turn
    owner to gtrpgm;

create index idx_turn_session_id
    on public.turn (session_id);

create index idx_turn_session_number
    on public.turn (session_id, turn_number);

create table public.player_inventory
(
    player_id  uuid                    not null
        constraint fk_player_inventory_player
            references public.player
            on delete cascade,
    item_id    uuid                    not null
        constraint fk_player_inventory_item
            references public.item
            on delete cascade,
    quantity   integer   default 1     not null
        constraint player_inventory_quantity_check
            check (quantity >= 0),
    created_at timestamp default now() not null,
    updated_at timestamp default now() not null,
    primary key (player_id, item_id)
);

comment on table public.player_inventory is '플레이어 인벤토리 - 플레이어와 아이템의 관계 및 수량';

comment on column public.player_inventory.player_id is '플레이어 ID';

comment on column public.player_inventory.item_id is '아이템 ID';

comment on column public.player_inventory.quantity is '보유 수량';

alter table public.player_inventory
    owner to gtrpgm;

create index idx_player_inventory_player_id
    on public.player_inventory (player_id);

create index idx_player_inventory_item_id
    on public.player_inventory (item_id);

create table public.inventory
(
    inventory_id      uuid      default gen_random_uuid() not null
        primary key,
    session_id        uuid                                not null
        references public.session
            on delete cascade,
    owner_entity_type varchar(20)                         not null
        constraint inventory_owner_entity_type_check
            check ((owner_entity_type)::text = ANY
                   ((ARRAY ['player'::character varying, 'npc'::character varying])::text[])),
    owner_entity_id   uuid                                not null,
    capacity          integer,
    weight_limit      numeric,
    state             jsonb     default '{}'::jsonb,
    created_at        timestamp default now()             not null,
    updated_at        timestamp default now()             not null,
    constraint uq_inventory_owner
        unique (session_id, owner_entity_type, owner_entity_id)
);

comment on table public.inventory is '세션 내 엔티티(Player/NPC)별 인벤토리 관리 테이블';

alter table public.inventory
    owner to gtrpgm;

create table public.player_npc_relations
(
    player_id           uuid                      not null
        constraint fk_player_npc_relations_player
            references public.player
            on delete cascade,
    npc_id              uuid                      not null
        constraint fk_player_npc_relations_npc
            references public.npc
            on delete cascade,
    affinity_score      integer     default 50    not null
        constraint player_npc_relations_affinity_score_check
            check ((affinity_score >= 0) AND (affinity_score <= 100)),
    relation_type       varchar(50) default 'neutral'::character varying,
    interaction_count   integer     default 0     not null,
    last_interaction_at timestamp,
    created_at          timestamp   default now() not null,
    updated_at          timestamp   default now() not null,
    primary key (player_id, npc_id)
);

comment on table public.player_npc_relations is '플레이어-NPC 관계 및 호감도 관리 테이블';

alter table public.player_npc_relations
    owner to gtrpgm;

create index idx_player_npc_relations_player_id
    on public.player_npc_relations (player_id);

create index idx_player_npc_relations_npc_id
    on public.player_npc_relations (npc_id);

create index idx_player_npc_relations_affinity
    on public.player_npc_relations (affinity_score);

-- Seed Data
INSERT INTO public.world_locales (locale_id, name, theme, description)
VALUES (1, '기본 시작 지점', '탐험', '어둡고 축축한 동굴 입구입니다.')
ON CONFLICT (locale_id) DO NOTHING;

INSERT INTO public.abilities (name, description) VALUES
('난폭함', '물리적인 힘과 파괴적인 행동'),
('똘똘함', '지식과 분석력'),
('영리함', '재치와 기만')
ON CONFLICT (name) DO NOTHING;