# Law Domain Agents

한국 법률 검색 엔진. FastAPI + Neo4j 기반 하이브리드 검색 (exact match + vector + relationship + RNE expansion).

## Architecture

```
server.py (FastAPI, port 8011)
  ├── REST API: /api/search, /api/domain/{id}/search, /api/domains, /api/health
  ├── A2A Protocol: /.well-known/agent-card/{slug}.json, /messages/{slug}
  │
  ├── law_search_engine.py    # 5-stage hybrid search + RRF merging
  ├── domain_manager.py       # Neo4j domain loader (DomainInfo, DomainManager)
  ├── domain_agent_factory.py # LangGraph agent wrapper (LawDomainAgent)
  ├── law_utils.py            # Result enrichment (law_name, law_type, article)
  └── shared/
      ├── neo4j_client.py     # Singleton Neo4j driver (bolt://localhost:7687)
      └── openai_client.py    # OpenAI text-embedding-3-large (3072-dim)
```

## Quick Start

```bash
cd AG/agent/law-domain-agents
cp .env.example .env   # NEO4J_PASSWORD, OPENAI_API_KEY 설정

# 서버 실행
.venv/Scripts/python server.py   # http://localhost:8011

# 헬스체크
curl http://localhost:8011/api/health
```

## REST API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/api/search` | `{query, limit}` | 자동 도메인 라우팅 검색 |
| POST | `/api/domain/{id}/search` | `{query, limit}` | 도메인 지정 검색 |
| GET | `/api/domains` | - | 도메인 목록 |
| GET | `/api/health` | - | 상태 확인 |

### Response Format

```json
{
  "results": [{
    "hang_id": "국토의 계획 및 이용에 관한 법률(시행령)::제12장::제4절::제71조::①",
    "content": "법 제76조제1항에 따른 용도지역안에서의 건축물의...",
    "unit_path": "제12장_제4절_제71조_①",
    "similarity": 0.884,
    "stages": ["vector_search"],
    "law_name": "국토의 계획 및 이용에 관한 법률",
    "law_type": "시행령",
    "article": "제71조"
  }],
  "stats": {"total": 10, "vector_count": 5, "relationship_count": 3, "graph_expansion_count": 2},
  "domain_id": "land_use_zones",
  "domain_name": "용도지역",
  "response_time": 342
}
```

## Search Algorithm (5-stage)

1. **Exact Match**: `r'제?(\d+)조'` → Cypher `h.full_id CONTAINS`
2. **Vector Search (INE)**: OpenAI 3072-dim → Neo4j `hang_embedding_index`, top-k=10
3. **Relationship Search**: Edge embedding similarity >= 0.65 (`contains_embedding` index, step5 필요)
4. **RNE Expansion**: Top 3 → `(start)<-[:CONTAINS]-(jo:JO)-[:CONTAINS]->(neighbor:HANG)` → cosine >= 0.65
5. **RRF Merging**: Reciprocal Rank Fusion (k=60), 중복 제거

## Neo4j Schema

```
LAW (3개: 법률, 시행령, 시행규칙)
 └── JANG (장) → JEOL (절) → JO (조, 1053개)
                                └── HANG (항, 1591개) ← 검색 대상, 3072-dim embedding
                                     └── HO (호) → MOK (목)
Domain (5개) ←[:BELONGS_TO_DOMAIN]─ HANG
```

- **Embeddings**: OpenAI text-embedding-3-large, 3072-dim, cosine
- **Vector index**: `hang_embedding_index` (ONLINE)
- **Rel index**: `contains_embedding` (NOT YET - step5 미실행)

## 5 Domains

| Domain ID | Name | Description |
|-----------|------|-------------|
| `land_use_zones` | 용도지역 | 용도지역/지구/구역 (제4장) |
| `development_activities` | 개발행위 | 개발행위 허가/제한 |
| `land_transactions` | 토지거래 | 토지거래 허가/제한 |
| `urban_planning` | 도시계획 및 이용 | 도시계획시설 |
| `urban_development` | 도시개발 | 도시개발/정비 |

## Upstream Consumers

이 서버를 호출하는 두 시스템. API 계약 변경 시 반드시 둘 다 업데이트:

```
ACE MCP Server (57 tools)
  ├── law_search()         → POST /api/search          (direct)
  ├── law_search_domain()  → POST /api/domain/{id}/search
  ├── law_domains()        → GET  /api/domains
  └── law_health()         → GET  /api/health

ARR Django Backend (:8000)
  ├── /law/search/         → POST /api/search           (proxied, logged)
  ├── /law/domain/{id}/search/ → POST /api/domain/{id}/search
  ├── /law/domains/        → GET  /api/domains
  └── /law/health/         → GET  /api/health
```

## Pipeline Status (2026-02-23)

| Step | Status | Detail |
|------|--------|--------|
| Step1 PDF→JSON | DONE | 3개 법률 파싱 |
| Step2 JSON→Neo4j | DONE | 1591 HANG, 1053 JO |
| Step3 Embeddings | DONE | OpenAI 3072-dim |
| Step4 Domains | DONE | 5 domains, 1 active |
| Step5 RelEmbeddings | TODO | ~30min, $2-3 |

## Testing

```bash
# 구조 테스트 (Neo4j 불필요)
C:/Python313/python tests/test_law_pipeline.py -v

# 통합 테스트 (mock server)
C:/Python313/python tests/test_law_pipeline_integration.py -v

# 검색 품질 테스트 (Neo4j + server 필요)
C:/Python313/python tests/test_law_depth.py
```

## Prerequisites

- Neo4j on `bolt://localhost:7687` (pw: `demodemo`)
- OPENAI_API_KEY env var
- Python 3.11+ with `.venv/` dependencies
