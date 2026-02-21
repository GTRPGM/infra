import json
import httpx
import uuid

SCENARIO_SERVICE_URL = "http://localhost:18040"  # 외부 노출 포트

def inject_minimal_scenario():
    scenario_id = str(uuid.uuid4())
    payload = {
        "title": f"Relation Test Scenario {scenario_id[:8]}",
        "description": "NPC 조우 및 관계 생성 테스트용",
        "acts": [
            {
                "id": "act-1",
                "name": "제 1막: 조우",
                "description": "NPC를 만나는 막",
                "exit_criteria": "NPC와 대화 완료",
                "sequences": ["seq-1"]
            }
        ],
        "sequences": [
            {
                "id": "seq-1",
                "name": "시퀀스 1: 평원",
                "location_name": "조용한 평원",
                "description": "NPC '떠돌이 상인'이 서 있는 평원입니다.",
                "goal": "NPC와 대화하여 관계를 형성하라.",
                "npcs": ["npc-merchant"],
                "enemies": [],
                "items": [],
                "exit_triggers": []
            }
        ],
        "npcs": [
            {
                "scenario_npc_id": "npc-merchant",
                "name": "떠돌이 상인",
                "description": "친절해 보이는 상인입니다.",
                "rule_id": 101,
                "state": {"numeric": {"HP": 100, "SAN": 10}}
            }
        ],
        "enemies": [],
        "items": [],
        "relations": [] # 초기 관계 없음 (조우 시 생성되어야 함)
    }

    payload_wrapper = {
        "payload": payload,
        "concept": "relation-test",
        "inject_to_state": True
    }

    resp = httpx.post(f"{SCENARIO_SERVICE_URL}/api/v1/manage/scenarios/debug/inject-save", json=payload_wrapper)
    resp.raise_for_status()
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print(f"Scenario Injected: {data.get('scenario_id')}")
    return data.get('scenario_id')

if __name__ == "__main__":
    inject_minimal_scenario()
