# GTRPGM Project Handheld (Integration & Development)

이 문서는 프로젝트의 구조, 현재 진행 상황 및 개발 규칙을 요약하여 협업과 빠른 온보딩을 돕습니다.

## 1. 아키텍처 및 인프라 (Architecture & Infra)

### 서비스 맵
- GM (Port 18020): 게임 마스터링 엔진. LangGraph를 통해 룰 엔진, 시나리오 서비스, 상태 관리자를 오케스트레이션합니다.
- State Manager (Port 18030): 세션, 플레이어, 인벤토리, NPC 등의 모든 동적 상태를 관리합니다.
- Scenario Service (Port 18040): 시나리오 생성(LLM), 주입 및 마스터 데이터 관리를 담당합니다.
- Rule Engine (Port 18050): 플레이어의 행동(Story)을 분석하여 성공/실패 여부와 상태 변화(Diff)를 계산합니다.
- PostgreSQL (Port 15432): 데이터 지속성 계층. ag_catalog를 통한 그래프 구조와 일반 관계형 테이블을 병행 사용합니다.

### 통신 규칙
- 모든 서비스 간 통신은 JSON 기반 REST API를 사용합니다.
- 외부 노출 포트는 호스트에서 10000 + 컨테이너 내부 포트 형식을 따릅니다.

## 2. 개발 상태 (Development Status)

### Done (역사적 기록)
- 테스터 오케스트레이션 구현 (src.tester.agent).
- 모든 ID 식별자 UUID(string) 통일.
- PostgreSQL shm_size 1gb 설정.
- GM RuleManagerHTTPClient ID 매핑 로직 추가 (Master ID -> Instance ID).
- GM GameEngine 내 NPC/Enemy 엔티티 통합 처리.
- State Manager npc 테이블 내 is_departed, departed_at 컬럼 추가 및 initdb 반영.
- PostgreSQL pgdata 볼륨 매핑을 통한 데이터 영속성 확보.
- 테스터 로거 명칭 변경 (uvicorn.error -> gtrpgm.tester).
- Scenario Service ID 정규화 로직 추가 (언더바를 하이픈으로 자동 변환).
- Scenario Service 그래프 조회 시 ID 문자열 변환 보장 로직 추가.

### In Progress
- 통합 테스트 완주 (5턴 시나리오 성공 확인).
- Scenario Service 404 에러 최종 수정 사항 반영 확인.

## 3. 핵심 복잡성 및 주의 사항 (Core Complexities)

### ID 정합성 문제
- 서비스마다 ID 명명 규칙이 다름 (act_1 vs act-1). Scenario Service 진입 시 반드시 정규화 로직을 거쳐야 함.
- entity_id (Master)와 state_entity_id (Instance)를 혼용하지 않도록 GM 레벨에서 매핑 테이블 관리 필수.

### 데이터 참조 전파
- GM은 항상 State Manager의 snapshot을 최우선으로 참조하여 다음 단계(Act/Seq) ID를 결정해야 함.

### 인프라 초기화 정합성
- PostgreSQL initdb 스크립트(002-schema.sql)와 각 서비스의 초기화 SQL이 일치하지 않을 경우, IF NOT EXISTS 구문으로 인해 신규 컬럼이 누락되는 현상 발생 주의.

## 4. 핵심 규칙 (Key Rules)

### 세부 준수 사항
- 마크다운 작성 시 이모지 사용 금지 및 엄격한 형식 준수.
- 코드 내 주석은 라인별 출력 추적 시를 제외하고 사용 금지.
- 모든 기능 수정 전 /docs에 계획 작성 및 업데이트.
- 단위 코드마다 테스트 작성 필수.
- 한국어 응답 원칙 및 영어 코드/문서화 원칙 준수.
