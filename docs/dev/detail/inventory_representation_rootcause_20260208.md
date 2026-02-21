# inventory_representation_rootcause_20260208

## 목적
- “state-manager 인벤토리 표현과 시나리오 표현 차이 때문에 인벤토리가 비어 보인다” 가설을 코드/실행 근거로 확정한다.

## 핵심 결론
1. `PUT /state/inventory/update`는 현재 no-op이며 실제 인벤토리를 갱신하지 않는다.
2. 실제 반영 경로는 `POST /state/player/item/earn`(item UUID 기반)인데, BE-router에서 이 경로를 중계하지 않는다.
3. 시나리오의 `relations: owns`는 플레이어 인벤토리와 별개 모델이라 자동 소지로 이어지지 않는다.
4. 시퀀스 단위 엔티티 다중 삽입 + relation 복제 방식 때문에 중복 관계가 증폭된다.

## 코드 근거
- no-op 구현:
  - `services/state-manager/src/state_db/repositories/player.py:201`
- no-op 엔드포인트 연결:
  - `services/state-manager/src/state_db/routers/router_UPDATE.py:66`
- 실제 인벤토리 반영 구현(그래프 CONTAINS):
  - `services/state-manager/src/state_db/repositories/player.py:377`
  - `services/state-manager/src/state_db/Query/CYPHER/inventory/earn_item.cypher:1`
- 시나리오 주입 시 엔티티 삽입 방식(시퀀스별 삽입):
  - `services/state-manager/src/state_db/repositories/scenario.py:107`
- 세션 시작 시 마스터 복제:
  - `services/state-manager/src/state_db/Query/BASE/L_npc.sql:10`
  - `services/state-manager/src/state_db/Query/BASE/L_enemy.sql:10`
  - `services/state-manager/src/state_db/Query/BASE/L_item.sql:13`
- relation 복제( tid 매칭으로 조합 확장 가능 ):
  - `services/state-manager/src/state_db/Query/BASE/L_graph.sql:97`
- 테스터 관측 오차(list를 dict로 가정):
  - `tester/src/tester/runner.py:148`

## 재현 근거
1. no-op 경로 재현 (BE-router)
- 실행:
  - `PUT /state/inventory/update` with `{player_id, rule_id, quantity}`
- 결과:
  - 응답은 success
  - 이후 `GET /state/session/{session_id}/inventory`는 `[]`
  - 이후 `GET /state/player/{player_id}`의 `items`도 `[]`

2. 실제 반영 경로 재현 (state-manager direct)
- 실행:
  - `POST /state/player/item/earn` with `{session_id, player_id, item_id(UUID), quantity}`
- 결과:
  - `GET /state/session/{session_id}/inventory`에 아이템 추가됨
  - `GET /state/player/{player_id}`의 `items`에도 반영됨

3. BE-router 경로 격차 확인
- BE-router OpenAPI path 추출 결과:
  - `['/state/inventory/update']`
- 즉, `'/state/player/item/earn'`, `'/state/player/item/use'`는 미노출

## 왜 “시나리오 owns가 있는데 인벤토리가 비는가”
- `owns`는 `RELATION` 그래프 엣지(엔티티 간 관계)이고,
- 플레이어 소지는 `Player -> Inventory -> CONTAINS -> Item` 그래프/조회 계약을 따른다.
- 두 표현이 연결되지 않았으므로 owns 정의만으로 플레이어 인벤토리는 증가하지 않는다.

## 부수 현상: 관계 중복 증폭
- 동일 `scenario_npc_id/scenario_enemy_id`가 여러 시퀀스에 배치되면 SQL row가 복수 생성된다.
- session 초기화 시 이를 전량 복제하고, relation 초기화가 `tid` 기준 매칭/생성되어 edge가 중복될 수 있다.
- 관측 예:
  - `seq-4 entity_relations`: total 32, unique 3

## 권장 수정 순서
1. BE-router에 `/state/player/item/earn`, `/state/player/item/use` 프록시 추가
2. 테스터 starter loadout 경로를 `inventory/update(rule_id)`에서 `player/item/earn(item_uuid)`로 전환
3. `inventory/update`는 실제 구현하거나(deprecate 전까지) 실패를 반환하도록 변경
4. 시나리오 주입/세션 초기화에서 동일 relation dedupe 또는 시퀀스-스코프 relation 조회로 축소
