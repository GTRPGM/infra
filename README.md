# GTRPGM Infrastructure

## 📖 개요 (Overview)

**GTRPGM (Generative TRPG Game Master)** 프로젝트의 인프라스트럭처 및 모노레포(Monorepo) 루트입니다.  
이 저장소는 전체 마이크로서비스의 소스 코드, 인프라 설정(Docker), 데이터베이스 스키마, 그리고 개발 편의를 위한 CLI 도구들을 통합 관리합니다.

본 프로젝트는 AI 에이전트(LLM)를 활용하여 TRPG의 게임 마스터(GM) 역할을 수행하는 시스템을 구축하는 것을 목표로 합니다.

## 🏗️ 전체 아키텍처 (Global Architecture)

시스템은 기능별로 분리된 마이크로서비스(Microservices) 아키텍처를 따르며, 각 서비스는 독립적인 생명주기를 가집니다.

### 🧩 서비스 구성 (Microservices)

|       서비스명       | 역할 (Responsibility)                                              | 기술 스택              |
| :------------------: | :----------------------------------------------------------------- | :--------------------- |
|    **GM Service**    | 게임의 메인 루프 실행, 턴 관리, 서사 생성, 에이전트 오케스트레이션 | FastAPI, LangGraph     |
| **Scenario Service** | 사용자 컨셉 기반 시나리오(Act/Sequence) 자동 생성 및 검증          | FastAPI, LangGraph     |
|   **Rule Engine**    | 게임 내 행동 판정(성공/실패), 주사위 굴림, 상태 변화 계산          | FastAPI                |
|  **State Manager**   | 게임 월드 상태(State) 저장 및 관리, 스냅샷 제공                    | FastAPI, PostgreSQL    |
|   **LLM Gateway**    | 모든 LLM 요청의 중앙 프록시, 모델 추상화 및 로깅                   | FastAPI, OpenAI/Gemini |
|    **BE-Router**     | 클라이언트와 내부 서비스 간의 API 게이트웨이 및 라우팅             | FastAPI                |
|       **Web**        | 사용자 인터페이스 (프론트엔드)                                     | React/Vite (추정)      |

### 🛠️ 인프라 및 기반 기술 (Infrastructure)

- **Containerization**: Docker & Docker Compose
- **Database**: PostgreSQL (서비스별 논리적 DB 분리)
- **Cache/Message Broker**: Redis
- **Package Manager**: `uv` (Python)

## 📂 디렉토리 구조 (Directory Structure)

```bash
/
├── bin/                 # 프로젝트 관리 CLI 스크립트 (project, db, remote)
├── db/                  # 데이터베이스 마이그레이션 스크립트 및 스키마
├── docs/                # 프로젝트 문서
├── scripts/             # 유틸리티 및 테스트 스크립트
├── services/            # 마이크로서비스 소스 코드
│   ├── gm/
│   ├── scenario-service/
│   ├── rule-engine/
│   ├── state-manager/
│   ├── llm-gateway/
│   ├── BE-router/
│   └── WEB/
├── tests/               # 통합 테스트
├── docker-compose.local.yml # 로컬 개발용 오케스트레이션 설정
└── pyproject.toml       # 루트 프로젝트 설정
```

## 🚀 시작하기 (Getting Started)

### 1. 사전 요구사항 (Prerequisites)

- Docker & Docker Compose
- Python 3.11+ (권장: `uv` 패키지 매니저 사용)
- `.env` 설정 (LLM API Key 등)

### 2. 환경 변수 설정

`services/llm-gateway/.env` 또는 루트 환경 변수에 필요한 키를 설정합니다.

```bash
export GOOGLE_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
```

### 3. 서비스 실행 (Run Services)

`bin/project` 스크립트를 사용하여 전체 서비스를 실행할 수 있습니다.

```bash
# 컨테이너 빌드 및 실행 (Detached mode)
./bin/project up --build

# 상태 확인
./bin/project ps

# 로그 확인
./bin/project logs -f [service_name]

# 서비스 종료
./bin/project down
```

## 📜 개발 가이드 (Development Guide)

### 의존성 관리 (Dependency Management)

본 프로젝트는 **`uv`** 를 사용하여 파이썬 가상환경 및 패키지를 관리합니다. 각 서비스 디렉토리(`services/*`) 내에서 개별적으로 의존성을 관리합니다.

### 데이터베이스 관리 (Database)

`bin/db` 스크립트 또는 `db/` 디렉토리의 스크립트를 통해 마이그레이션 및 초기화를 수행합니다. 로컬 실행 시 `postgres` 컨테이너가 자동으로 초기화 스크립트를 실행합니다.
