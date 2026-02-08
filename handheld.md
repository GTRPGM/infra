# GTRPGM Project Handheld (Integration & Development)

이 문서는 프로젝트의 구조, 현재 진행 상황 및 개발 규칙을 요약하여 협업과 빠른 온보딩을 돕습니다.

## 1. 아키텍처 및 인프라 (Architecture & Infra)

### 서비스 맵
- **GM (Port 18020):** 게임 마스터링 엔진. LangGraph를 통해 룰 엔진, 시나리오 서비스, 상태 관리자를 오케스트레이션합니다.
- **State Manager (Port 18030):** 세션, 플레이어, 인벤토리, NPC 등의 모든 동적 상태를 관리합니다. (PostgreSQL + Apache AGE)
- **Scenario Service (Port 18040):** 시나리오 생성(LLM), 주입 및 마스터 데이터 검증을 담당합니다.
- **Rule Engine (Port 18050):** 캐릭터의 행동(Story)을 분석하여 성공/실패 여부와 상태 변화(Diff)를 계산합니다.
- **LLM Gateway (Port 18060):** 다양한 LLM 모델(Gemini, OpenAI 등)에 대한 통합 인터페이스를 제공합니다.

## 2. 개발 상태 (Development Status) - 2026.02.05 Updated

### ✅ Done (완료된 작업)
- **[Feature] 오프닝 브리핑 (Opening Narrative)**:
  - `POST /api/v1/game/summary` 엔드포인트 신설.
  - 게임 시작/재개 시 플레이어 입력 없이 현재 상황(위치, NPC, 분위기)을 먼저 묘사하여 몰입감 조성 및 "기억 상실" 클리셰 방지.
- **[Fix] 환각(Hallucination) 방지**:
  - 나레이터 프롬프트에 `World Snapshot`에 없는 장소/아이템 생성을 엄격히 금지하는 제약 추가. (없는 숲, 펜던트 생성 방지)
- **[Fix] 데이터 무결성 & 흐름**:
  - `scenario_id` 유실 버그 수정 (UUID가 LangGraph 컨텍스트를 타고 정확히 전달됨).
  - `state-manager`의 아이템 조회 500 에러 및 DB 함수(`create_session`) 중복 정의 문제 해결.
- **[UX] 서사적 묘사 강화**:
  - 기계적인 "1. 공격 2. 대화" 선택지 제시를 금지하고, 소설과 같은 자연스러운 행동 유도 서술 적용.
- **[Logic] 시나리오 트리거 & 비전투 판정 개선**:
  - 시나리오 서비스가 전체 시퀀스 목록을 참조하여 정확한 장소 이동(Sequence Jump)을 판정하도록 개선.
  - 시나리오 서비스가 비전투 상황(함정, 퍼즐 등)의 보상 및 상태 변화(`correction_diffs`)를 제안할 수 있도록 확장.
- **[Data] 기본 아이템 지급 자동화**:
  - 세션 생성 시 플레이어에게 횃불과 로프를 자동 지급하도록 `State Manager` 트리거 수정.

### 🚧 In Progress / To Do (개선 필요)
- **[UX] UI 연동 최적화**:
  - `correction_diffs`가 발생했을 때 프론트엔드 UI에서 아이템 획득 알림 등이 자연스럽게 연출되도록 연동 데이터 보강.
- **[Perf] 컨텍스트 요약(Summarization)**:
  - 히스토리가 길어질 경우 슬라이딩 윈도우 외에 핵심 요약을 별도 레이어로 관리하여 LLM 기억력 보존.

## 3. 핵심 규칙 (Key Rules)
- **객체지향 원칙**: Router와 Service는 클래스 기반 구현을 유지합니다.
- **상태 관리**: GM은 상태를 직접 저장하지 않고, 매 턴 `State Manager`에서 조회(`fetch`)하고 계산된 결과만 반영(`commit`)합니다.
- **컨텍스트 관리**: 히스토리 참조 시 무한 어펜드가 아닌 슬라이딩 윈도우(`limit=5`) 방식을 고수합니다.
- **테스트**: 통합 테스트 시 `src.tester.runner`를 사용하며, 반드시 로그 파일을 생성하여 트래픽을 추적합니다.

## 4. 실행 및 관리 가이드 (Usage Guide)

### 통합 테스트 실행
`uv` 환경을 사용하여 테스터를 실행하며, 실시간으로 한글 로그를 확인합니다.
- **명령어**: `PYTHONPATH=tester/src uv run python -m tester.runner [session_id] [max_turns]`
- **결과 확인**: 콘솔 출력 및 `test_output_{timestamp}.log` 파일 생성.

### 주요 엔드포인트
- **오프닝/요약**: `POST /api/v1/game/summary` (body: `{"session_id": "..."}`)
- **턴 진행**: `POST /api/v1/game/turn` (body: `{"session_id": "...", "content": "행동"}`)
- **상태 조회**: `GET /state/session/{session_id}/sequence/details` (State Manager 직접 호출)
