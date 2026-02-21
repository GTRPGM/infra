# ref_contract_matrix - Contract Inventory (plan_0001)

## 1) Immutable Contract Sources
- State inject schema: `services/state-manager/src/state_db/schemas/scenario.py`
- State inject persistence: `services/state-manager/src/state_db/repositories/scenario.py`
- State commit/session boundary:
  - `services/state-manager/src/state_db/schemas/requests.py`
  - `services/state-manager/src/state_db/schemas/management_requests.py`
  - `services/state-manager/src/state_db/routers/router_COMMIT.py`
  - `services/state-manager/src/state_db/routers/router_SESSION.py`
- Rule play contract:
  - `services/rule-engine/src/domains/play/dtos/play_dtos.py`
  - `services/rule-engine/src/domains/play/play_router.py`

## 2) Inter-service Contract Matrix
### Scenario Service -> State Manager (`/state/scenario/inject`)
| Boundary | Producer Field | Canonical Field (State) | Status | Note |
|---|---|---|---|---|
| Item ID | `item_id` or `scenario_item_id` | `scenario_item_id: str` | compatible (mapped) | `_to_state_injection_payload` normalizes |
| Rule ID | `master_id` or `rule_id` | `rule_id: int` | compatible (mapped) | `_coerce_rule_id` converts |
| Enemy drop refs | `dropped_items: [str/int]` | `dropped_items: List[int]` | compatible (mapped) | item ref -> item `rule_id` |
| Sequence assets | `items/npcs/enemies` | same id lists | compatible | id normalization before inject |

### GM -> Rule Engine (`/play/scenario`)
| Boundary | GM Payload | Rule Canonical | Status | Note |
|---|---|---|---|---|
| Request object | `session_id/scenario_id/locale_id/entities/relations/story` | `PlaySceneRequest` | compatible | wrapped response `data` handled |
| Entity diff id | `state_entity_id` + optional `entity_id` | `EntityUnit` | partial | non-numeric source ids lose `entity_id` precision |

### GM -> Scenario Service (`/api/v1/check/validate`)
| Boundary | GM Payload | Scenario Canonical | Status | Note |
|---|---|---|---|---|
| progression check | `scenario_id/act_id/seq_id/user_input` | `ValidationRequest` | compatible | response mapped to `ScenarioSuggestion` |

### GM -> State Manager
| Boundary | GM Payload | State Canonical | Status | Note |
|---|---|---|---|---|
| Commit | `turn_id`, `diffs[]` | `CommitRequest` | compatible | state accepts legacy `diffs` fallback |
| Act update | `{\"new_act\": int}` | `ActChangeRequest` | mismatch | missing `new_act_id/new_sequence_id` |
| Sequence update | `{\"new_sequence\": int}` | `SequenceChangeRequest` | mismatch | missing `new_sequence_id` |

### BE-router -> GM proxy (`/gm/turn`)
| Boundary | BE-router Payload | GM Canonical | Status | Note |
|---|---|---|---|---|
| turn relay | `session_id/content` | `UserInput` | compatible | passthrough proxy |

## 3) Defect List (Severity / Owner)
| Severity | Defect | Owner | Evidence | Next Plan |
|---|---|---|---|---|
| Blocker | GM act/sequence transition request body does not satisfy State required schema | `gm` | `services/gm/src/gm/plugins/external/http_client.py` vs `services/state-manager/src/state_db/schemas/management_requests.py` | resolved in `plan_0003` |
| Major | Scenario internal generation schema still uses `master_id/item_id` naming; full equivalence relies on mapper | `scenario-service` | `services/scenario-service/src/scenario/core/models/generation.py` | resolved in `plan_0002` |
| Major | GM rule payload can degrade `entity_id` fidelity for non-numeric source ids | `gm` | `parse_entity_id` in `services/gm/src/gm/plugins/external/http_client.py` | `plan_0003` |
| Minor | BE-router GM proxy has debug `print()` in request path | `BE-router` | `services/BE-router/src/gm/gm_routers.py` | resolved in `plan_0004` |

## 4) plan linkage
- `plan_0002`: Scenario schema naming and canonical parity hardening.
- `plan_0003`: GM request/response strict contract alignment (especially transition path).
- `plan_0004`: BE-router proxy contract hygiene and parity checks.

## 5) BE-router Game Flow Endpoints (plan_0012)
| Step | Action | Endpoint | Method | Key Fields |
|---|---|---|---|---|
| 1 | Login | `/auth/login` | POST | `username`, `password` |
| 2 | Scenario Selection | `/state/scenarios` | GET | - |
| 3 | Scenario Inject | `/scenario/manage/scenarios/{id}/inject` | POST | `id` (scenario_id) |
| 4 | Session Start | `/state/session/start` | POST | `scenario_id` (state_manager_id) |
| 5 | Opening Summary | `/gm/summary` | POST | `session_id` |
| 6 | Turn Loop | `/gm/turn` | POST | `session_id`, `content` |
| 7 | State Probe | `/state/session/{id}/...` | GET | `id` (session_id) |

## 6) Key Identity Fields and Ownership
| Field | Type | Owner | Note |
|---|---|---|---|
| `scenario_id` | UUID/Str | Scenario Service | Primary scenario template ID |
| `state_manager_scenario_id` | Int/Str | State Manager | Primary key in `scenarios` table |
| `session_id` | UUID | State Manager | Active game session identifier |
| `turn_id` | Str | GM | Format: `{session_id}:{turn_num}` |
| `act_id` | Str | Scenario/State | Format: `act-{N}` |
| `seq_id` | Str | Scenario/State | Format: `seq-{N}` |
| `entity_id` | Str | Scenario/State | Format: `npc-{N}`, `enemy-{N}`, `item-{N}` |
