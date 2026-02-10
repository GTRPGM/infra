# GTRPGM Technical Stack

이 문서는 GTRPGM 프로젝트에서 사용된 주요 기술 스택과 각 기술의 채택 이유, 그리고 구체적인 사용 목적을 정리합니다.

---

## 1. 공통 기반 기술 (Common Infrastructure)

프로젝트 전반에서 표준으로 사용되는 핵심 기술입니다.

| 기술                 |      구분       | 사용 목적 및 상세                                                                  |
| :------------------- | :-------------: | :--------------------------------------------------------------------------------- |
| **Python 3.11+**     |    Language     | 비동기 처리 및 풍부한 LLM 생태계(LangChain 등) 활용을 위한 주력 언어               |
| **uv**               | Package Manager | 초고속 패키지 설치, 의존성 격리, `pyproject.toml` 기반의 현대적 프로젝트 관리      |
| **FastAPI**          |    Framework    | 고성능 비동기 API 서버 구축. Pydantic을 통한 자동 데이터 검증 및 Swagger 문서 제공 |
| **Docker / Compose** | Infrastructure  | 서비스 컨테이너화 및 로컬/운영 환경의 동일한 실행 환경(Environment) 보장           |
| **PostgreSQL**       |    Database     | 관계형 데이터 저장. 서비스별 논리적 DB 분리를 통해 데이터 독립성 및 확장성 확보    |
| **Redis**            |  Cache/Broker   | 세션 관리, API 게이트웨이의 라우팅 정보 저장 및 빈번한 데이터의 캐싱               |
| **Ruff**             |   Lint/Format   | Rust 기반의 초고속 린터 및 포맷터. 팀 내 코드 스타일 통일 및 품질 유지             |
| **MyPy**             |   Type Check    | 정적 타입 체크를 통해 대규모 모노레포 환경에서의 타입 안정성 확보                  |

---

## 2. 서비스별 상세 기술 활용 (Service-Specific)

### 🧩 GM Service (Game Master)

- **LangGraph**: 게임 진행 로직을 상태 머신(State Machine)으로 관리. 플레이어-NPC-나레이터 간의 턴 전환과 서사 흐름을 비결정론적인 LLM 응답 속에서도 구조적으로 제어합니다.
- **LangChain**: LLM 프롬프트 엔지니어링 및 출력 파싱(Structured Output)의 표준 인터페이스로 사용.
- **AsyncPG**: DB I/O 병목을 최소화하기 위한 비동기 PostgreSQL 드라이버.

### 🧩 Scenario Service

- **LangGraph (Multi-Agent)**: Planner, Writer, Reviewer 에이전트 간의 협업 워크플로우를 구현. 특히 Reviewer가 결함을 발견하면 이전 단계로 되돌려 수정을 요청하는 '자가 수정 루프(Self-Correction Loop)'의 핵심 엔진입니다.
- **Pydantic Settings**: 환경 변수 및 서비스 설정을 타입 안전하게 관리.

### 🧩 Rule Engine

- **Pydantic**: 캐릭터 시트 및 아이템 능력치 등 복잡한 데이터 구조의 유효성 검사.
- **Logic Separation**: 복잡한 게임 판정 로직(주사위 굴림, 보정치 계산 등)을 비즈니스 로직과 분리하여 독립적으로 테스트 가능하게 설계.

### 🧩 State Manager

- **PostgreSQL (JSONB)**: 캐릭터의 동적인 상태 변화(HP, 경험치, 소지품 등)를 유연하게 저장하고 쿼리하기 위해 JSONB 타입을 적극 활용.
- **Snapshot Logic**: 게임의 특정 시점 상태를 스냅샷 형태로 제공하여 GM 서비스가 문맥을 파악할 수 있도록 지원.

### 🧩 LLM Gateway

- **Provider Abstraction**: OpenAI, Google Gemini 등 다양한 LLM 제공사의 SDK를 추상화하여, 상위 서비스가 모델 변경에 영향을 받지 않도록 설계.
- **Tenacity**: 네트워크 불안정성이나 외부 API의 일시적 장애에 대응하기 위한 지수 백오프(Exponential Backoff) 기반 재시도 전략 적용.

### 🧩 BE-Router & WEB

- **Vite (React)**: 프론트엔드 빌드 도구로 사용하여 빠른 개발 피드백 및 최적화된 번들링 제공.
- **HTTPX**: 마이크로서비스 간 비동기 HTTP 통신을 수행하는 클라이언트.

---

## 3. 설계 중점 사항 (Design Principles)

1.  **Strict Typing**: 모든 파이썬 코드에 타입 힌트를 강제하여 유지보수성 향상.
2.  **Decoupling**: 서비스 간 통신은 표준화된 REST API를 사용하며, 각 서비스의 내부 구현은 외부에서 알 수 없도록 캡슐화.
3.  **LLM Reliability**: LLM의 환각(Hallucination)이나 오류를 시스템적으로 보완하기 위해 검증용 에이전트(Reviewer)와 후처리 로직(Guardrails)을 기술적으로 배치.
