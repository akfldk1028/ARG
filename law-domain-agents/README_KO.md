# Law Domain Agents - 법률 검색 멀티 에이전트 시스템

## 개요

A2A(Agent-to-Agent) 프로토콜을 사용하는 법률 조항 검색 멀티 에이전트 시스템입니다.

## 아키텍처

```
QueryCoordinator (port 8010)
    ├─> Domain 1: 도시계획 및 이용 (port 8011)
    ├─> Domain 2: 토지이용 및 보상 (port 8012)
    ├─> Domain 3: 토지등 및 계획 (port 8013)
    ├─> Domain 4: 도시계획 및 환경관리 (port 8014)
    └─> Domain 5: 토지이용 및 보상절차 (port 8015)
```

## 기술 스택

- **LangGraph**: 워크플로우 관리
- **FastAPI**: A2A 서버
- **Neo4j**: 그래프 데이터베이스 (법률 데이터)
- **KR-SBERT**: 한국어 시맨틱 검색
- **OpenAI**: 임베딩 및 LLM

## 기능

- **A2A Protocol**: JSON-RPC 2.0 기반 에이전트 간 통신
- **Hybrid Search**: Exact Match + Vector Search + Relationship Search
- **RNE (Relationship-aware Node Embedding)**: 관계 기반 그래프 확장
- **INE (Initial Node Embedding)**: 시맨틱 검색

## 빠른 시작

### 1. 사전 요구사항

- Neo4j Database (localhost:7687)
- Python 3.11+
- OpenAI API Key

### 2. 환경 설정

```bash
cd D:\Data\25_ACE\AG\agent\law-domain-agents

# .env 파일 확인 (이미 생성됨)
# NEO4J_PASSWORD를 실제 값으로 수정
```

### 3. 도메인 초기화

```bash
# Neo4j에 도메인 노드 생성
cd D:\Data\25_ACE\AG\agent
python law-domain-setup/initialize_domains.py
```

### 4. 에이전트 실행

```bash
cd law-domain-agents
python run_domain_1.py
```

### 5. 테스트

```bash
# 새 터미널에서
python test_domain_1.py

# 또는 curl로 직접 테스트
curl http://localhost:8011/health
curl http://localhost:8011/.well-known/agent-card.json
```

## API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /health` | 헬스 체크 |
| `GET /.well-known/agent-card.json` | A2A 에이전트 카드 |
| `POST /messages` | A2A 메시지 (JSON-RPC 2.0) |
| `GET /api/domains` | 도메인 목록 |
| `POST /api/search` | 법률 검색 |

## 프로젝트 구조

```
law-domain-agents/
├── .env                    # 환경 설정
├── run_domain_1.py         # 실행 스크립트
├── test_domain_1.py        # 테스트 스크립트
├── server.py               # 메인 FastAPI 서버
├── law_search_engine.py    # 검색 엔진
├── law_orchestrator.py     # 오케스트레이터
│
├── domain-1-agent/         # Domain 1 구현
│   ├── server.py           # FastAPI A2A 서버
│   ├── graph.py            # LangGraph 워크플로우
│   ├── domain_logic.py     # 검색 로직
│   └── config.py           # 설정
│
├── shared/                 # 공유 유틸리티
│   ├── neo4j_client.py     # Neo4j 클라이언트
│   └── openai_client.py    # OpenAI 클라이언트
│
└── coordinator/            # QueryCoordinator (향후)
```

## 현재 상태

### 완료된 기능
- Hybrid Search (Exact + Vector + Relationship)
- RNE/INE 알고리즘
- A2A 프로토콜 엔드포인트
- REST API
- Google ADK RemoteA2aAgent 패턴

### 진행 중
- QueryCoordinator 프론트엔드 연동
- 크로스 도메인 쿼리

자세한 상태: [STATUS.md](./STATUS.md)

## 문제 해결

### Neo4j 연결 실패
```bash
# Neo4j 실행 확인
curl http://localhost:7474
```

### 도메인 없음 오류
```bash
# 도메인 초기화 실행
python ../law-domain-setup/initialize_domains.py
```

## 관련 문서

- [QUICKSTART.md](./QUICKSTART.md) - 5분 가이드
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - 구현 요약
- [STATUS.md](./STATUS.md) - 현재 상태
- [STREAMING_GUIDE.md](./STREAMING_GUIDE.md) - 스트리밍 가이드
