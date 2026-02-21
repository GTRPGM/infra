import json
import httpx
import asyncio
import os

SCENARIO_SERVICE_URL = "http://localhost:18040/api/v1/scenarios/debug/inject-save"

async def inject_payload(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    request_body = {
        "payload": payload,
        "concept": f"injection-{os.path.basename(file_path)}",
        "inject_to_state": True
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"Injecting {file_path}...")
            response = await client.post(SCENARIO_SERVICE_URL, json=request_body)
            response.raise_for_status()
            print(f"Successfully injected {file_path}")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except httpx.HTTPStatusError as e:
            print(f"Failed to inject {file_path}: {e.response.status_code}")
            print(e.response.text)
        except Exception as e:
            print(f"Error injecting {file_path}: {str(e)}")

async def main():
    payloads = [
        "tester/src/tester/scenario_payloads/six_sequence_three_act_eval.inject.json",
        "tester/src/tester/scenario_payloads/three_sequence_combat.inject.json"
    ]
    for p in payloads:
        await inject_payload(p)

if __name__ == "__main__":
    asyncio.run(main())
