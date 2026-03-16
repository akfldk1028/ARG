# Law Domain Setup

`law-domain-agents` 프로젝트를 위한 Neo4j Domain 노드 초기화 및 벡터 인덱스 관리.

## Scripts

| File | Purpose | 필수 |
|------|---------|------|
| `initialize_domains.py` | Domain 노드 5개 생성, HANG→Domain 분류 | O |
| `recreate_vector_index.py` | 벡터 인덱스 재생성 (3072-dim, cosine) | 선택 |
| `check_hang_patterns.py` | HANG 노드 패턴 진단 | 선택 |
| `check_article_36.py` | 제36조 데이터 확인 | 선택 |

## Prerequisites

- Neo4j on `bolt://localhost:7687` (pw: `demodemo`)
- 법률 데이터 로드 완료 (Step 1-3)
- `../law-domain-agents/.env` 설정

## Run

```bash
cd AG/agent
python law-domain-setup/initialize_domains.py
```

## 5 Domains

| Domain ID | Name | Description |
|-----------|------|-------------|
| `land_use_zones` | 용도지역 | 용도지역/지구/구역 (제4장) |
| `development_activities` | 개발행위 | 개발행위 허가/제한 |
| `land_transactions` | 토지거래 | 토지거래 허가/제한 |
| `urban_planning` | 도시계획 및 이용 | 도시계획시설 |
| `urban_development` | 도시개발 | 도시개발/정비 |

## Status (2026-02-23)

- **Domains**: 5개 생성, law-domain-agents에서 1개 로드 (용도지역, 1591 nodes)
- **Vector index `hang_embedding_index`**: ONLINE (3072-dim, cosine)
- **Vector index `contains_embedding`**: 미생성 (step5 미실행)
- **Embeddings**: 1591 HANG, OpenAI text-embedding-3-large 3072-dim

## Neo4j Graph

```
(HANG)-[:BELONGS_TO_DOMAIN]->(Domain)
```

분류 방식: HANG full_id 내 키워드 매칭 (장/절 구조 기반).
