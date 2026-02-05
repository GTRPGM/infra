# NPC/Enemy Cloning Fix Plan

## 1. 목적 (Purpose)

- 시나리오 주입 시 Master Session(ID 0)에 저장된 NPC, Enemy, Item 및 관련 그래프 데이터를 신규 세션 생성 시 자동으로 복제하여 세션 독립성을 확보하고 데이터 부재 현상을 해결함.

## 2. 현황 및 문제점 (Current Status & Problems)

- `inject_scenario`는 데이터를 `session_id = '000...0'`으로만 저장함.
- `SessionRepository.start` 호출 시 `session` 테이블에만 레코드가 생성되고, 실제 엔티티 데이터는 복제되지 않음.
- `npc.sql`, `enemy.sql` 내의 `initialize_npcs`, `initialize_enemies` 트리거가 플레이스홀더 상태임.
- Apache AGE 그래프 데이터(노드 및 관계)도 복제가 필요함.

## 3. 해결 방안 (Solution)

- **Step 1**: `state-manager`의 세션 생성 로직(`create_session` SQL 함수)을 확장하거나 전용 복제 함수(`clone_scenario_data`)를 구현.
- **Step 2**: SQL 테이블(`npc`, `enemy`, `item`) 복제 로직 구현.
- **Step 3**: Apache AGE 그래프 데이터(`npc`, `enemy` 노드 및 `RELATION` 엣지) 복제 로직 구현.
- **Step 4**: `router_COMMIT.py`에서 대소문자 구분 없이 필드를 매핑하도록 수정 (`HP` -> `hp`).
- **Step 5**: 통합 테스트를 통해 NPC 존재 여부 및 상태 업데이트 정상화 확인.

## 4. 상세 구현 계획

### 4.1 SQL 데이터 복제

`create_session` 함수 내에서 또는 별도 트리거에서 다음을 수행:

- `npc`, `enemy`, `item` 테이블의 데이터를 `MASTER_SESSION_ID`로부터 신규 `session_id`로 복사.
- 이때 `npc_id`, `enemy_id` 등 인스턴스 ID는 신규 생성.

### 4.2 그래프 데이터 복제

- Apache AGE의 `cypher`를 사용하여 특정 `scenario_id`와 `MASTER_SESSION_ID`를 가진 노드와 관계를 신규 `session_id`로 복제.

### 4.3 GM/Rule Engine 연동 보정

- `router_COMMIT.py` 내의 필드 매핑 로직을 유연하게 수정.
