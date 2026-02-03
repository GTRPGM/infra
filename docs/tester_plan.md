# LLM Tester Agent 구축 계획

## 1. 목적
- `gm` 서비스의 게임 진행 로직을 자동으로 테스트하기 위한 LLM 에이전트 구축.
- LLM 에이전트는 사용자를 대신하여 게임에 참여하고, `gm` 서비스의 응답을 분석하여 적절한 행동을 선택함.

## 2. 현황
- `gm` 서비스는 FastAPI 기반으로 구축되어 있으며, 게임 진행 API(`v1/game/*`)를 제공함.
- `gm` 서비스 내에 `llm-gateway`와 통신하기 위한 LangChain 기반 어댑터(`NarrativeChatModel`)가 구현되어 있음.
- `infra` 루트 디렉토리에 `uv` 기반의 새로운 환경이 초기화됨.

## 3. 구현 계획
### 3.1 환경 설정
- [x] `uv init --app`으로 프로젝트 초기화.
- [x] 필수 의존성 설치: `fastapi`, `uvicorn`, `langchain-core`, `httpx`, `pydantic-settings`.

### 3.2 핵심 컴포넌트 개발 (`src/tester`)
- [x] **LLM 어댑터 (`src/tester/adapter.py`)**: `gm`의 `NarrativeChatModel`을 참고하여 `llm-gateway` 전용 LangChain 챗 모델 구현. (포트 8060, 8020으로 조정 완료)
- [x] **게임 클라이언트 (`src/tester/client.py`)**: `gm` 서비스의 API를 호출하는 비동기 클라이언트 구현.
- [x] **테스터 에이전트 (`src/tester/agent.py`)**: 
    - `langchain-core`를 사용하여 게임 루프(관찰 -> 생각 -> 행동) 구현.
    - `gm/docs` 내의 문서를 참고하여 게임 규칙 및 목표 이해.
- [x] **FastAPI 서버 (`src/tester/main.py`)**: 에이전트 실행 및 테스트 시나리오 제어를 위한 엔드포인트 제공. (중복 임포트 및 문법 오류 수정 완료)
- [x] **통합 테스트 러너 (`src/tester/runner.py`)**: 자동 테스트 시나리오 실행 로직 구현.

### 3.4 실행 방법
- 루트 디렉토리에서 아래 명령어로 테스터 API를 실행합니다.
```bash
uv run uvicorn src.tester.main:app --host 0.0.0.0 --port 8002 --reload
```

## 4. 일정
- [x] 1단계: LLM 어댑터 및 게임 클라이언트 구현.
- [x] 2단계: 에이전트 로직 및 프롬프트 구성.
- [x] 3단계: FastAPI 서버 통합 및 최종 테스트.
- [ ] 4단계: 실제 GM 서비스와의 연동 테스트 및 버그 수정.
