# Law Domain Agents - Claude Code Context

## Overview

FastAPI server (port 8011) providing Korean law article search via A2A protocol + REST API.
Hybrid search engine using Neo4j graph DB with exact match, vector search, relationship search, and RNE expansion.

## Architecture

```
law-domain-agents/
├── server.py                  # FastAPI server (port 8011) - A2A + REST endpoints
├── law_search_engine.py       # Core search (501 lines) - hybrid + RRF merging
├── domain_manager.py          # Neo4j domain loader (DomainInfo, DomainManager)
├── domain_agent_factory.py    # LangGraph agent wrapper (LawDomainAgent)
├── law_utils.py               # Result enrichment (law_name, law_type)
├── law_orchestrator.py        # Multi-domain orchestration (TODO)
├── shared/
│   ├── neo4j_client.py        # Singleton Neo4j driver (bolt://localhost:7687)
│   └── openai_client.py       # OpenAI text-embedding-3-large (3072-dim)
├── domain-1-agent/            # Legacy single-domain agent (superseded by server.py)
└── multilayer_embedding_redesign/  # Embedding upgrade scripts
```

## Prerequisites

- **Neo4j** running on `bolt://localhost:7687` (user: neo4j, password: from NEO4J_PASSWORD env)
- **OpenAI API key** in OPENAI_API_KEY env var (for embeddings)
- **Python venv**: `.venv/` has all dependencies installed

## Run

```bash
cd AG/agent/law-domain-agents
.venv/Scripts/python server.py    # http://localhost:8011
```

## REST API Endpoints (for ACE MCP integration)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/api/search` | `{query, limit}` | Cross-domain search (domain_id=None, "전체 검색") |
| POST | `/api/domain/{domain_id}/search` | `{query, limit}` | Domain-specific search |
| GET | `/api/domains` | - | List all domains |
| GET | `/api/health` | - | Health check |

### Search Response Format
```json
{
  "results": [{
    "hang_id": "국토의_계획_및_이용에_관한_법률_법률_제17조_제1항",
    "content": "도시·군관리계획은...",
    "unit_path": "...",
    "similarity": 0.95,
    "stages": ["vector"],
    "law_name": "국토의 계획 및 이용에 관한 법률",
    "law_type": "법률",
    "article": "제17조"
  }],
  "stats": {"total": 10, "vector_count": 5, "relationship_count": 3, "graph_expansion_count": 2},
  "domain_id": "domain_09b3af0d",
  "domain_name": "국토 계획 및 이용",
  "response_time": 342
}
```

## A2A Protocol Endpoints (for agent-to-agent)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/.well-known/agent-card/{slug}.json` | Agent capability card |
| POST | `/messages/{slug}` | JSON-RPC 2.0 message/send |

## Search Algorithm (2026-02-24 v2 — 7 stages all working)

1. **Exact Match**: Regex `r'제?(\d+)조'` -> Cypher `h.full_id CONTAINS` (no section filter)
2. **Fulltext Keyword** (NEW): Neo4j CJK fulltext index `hang_content_fulltext`, 조항번호 제거 후 키워드 검색. 법률당 max 3개 cap.
3. **Vector Search (INE)**: OpenAI 3072-dim embedding -> `hang_embedding_index`, 법률당 max 4개 cap. 4x fetch for diversity.
4. **Relationship Search**: Edge embedding similarity >= 0.65 on `contains_embedding` index (requires step5 rel-embeddings)
5. **RRF Merging**: Reciprocal Rank Fusion with k=60, 4 signals (exact+fulltext+vector+rel), 2x top_k candidates
6. **RNE Expansion**: Top 3 results -> JO neighbor HANG -> cosine >= 0.35 (lowered from 0.65)
7. **MMR Reranking** (NEW): Maximal Marginal Relevance (Carbonell & Goldstein 1998), λ=0.7. 관련성+다양성 균형.
8. **Hierarchy Expansion**: 법률↔시행령↔시행규칙 인용 기반 교차 검색
   - 결과에서 법명별 present/missing 법타입 분석
   - Missing 타입의 HANG content에서 `"제N조"` 인용 검색 (Cypher `STARTS WITH` + `CONTAINS`)
   - 조항당 max 2, similarity=0.75, stage=`hierarchy_expansion`
   - 상위 5개 결과 뒤에 삽입 (top_k 내 포함 보장)
9. **Enrichment**: `law_utils.enrich_search_results()` adds law_name, law_type, article fields
   - **FIXED (2026-02-23)**: `parse_hang_id()` checks `(시행규칙)` → `(시행령)` → `(법률)` order (was always returning "법률")

**검색 다양성**: "용도지역" limit=40 → 6/6 laws, limit=15 → 4 laws. Per-law cap + MMR + hierarchy expansion으로 법률별 골고루 검색.

## Neo4j Graph Schema (2026-02-27)

- **LAW** nodes: 18 (6개 법률 × 3 types: 법률/시행령/시행규칙)
- **HANG** nodes: 6171 law article paragraphs (content, full_id, embedding 3072-dim OpenAI)
- **HO** nodes: 6026 numbered items (호)
- **MOK** nodes: 1284 sub-items (목)
- **JO** nodes: 2431 law articles (조)
- **JANG** nodes: 96 chapters (장)
- **JEOL** nodes: 50 sections (절)
- **Domain** nodes: 5 domains
- Relationships: `CONTAINS` (LAW->JANG->JO->HANG->HO->MOK, all with 3072-dim embeddings), `NEXT` (JO->JO, HANG->HANG), `BELONGS_TO_DOMAIN` (HANG->Domain)
- Vector indexes: `hang_embedding_index`, `ho_embedding_index`, `mok_embedding_index`, `jo_embedding_index`, `contains_embedding` (all ONLINE, 3072-dim cosine)
- Fulltext indexes: `hang_content_fulltext` (CJK bi-gram analyzer on HANG.content), `jo_content_fulltext`
- **Neo4j**: `bolt://localhost:7687`, pw=`11111111` (Neo4j Community 5.26.0)
- **Total nodes**: 16,081

## 5 Domains (2026-02-27)

| Domain ID | Name | Nodes |
|-----------|------|-------|
| land_use_regulation | 토지이용규제 | 2286 |
| national_land_planning | 국토계획 총론 | 2004 |
| building_standards | 건축기준 | 1018 |
| zoning_regulation | 용도지역 및 건축규제 | 614 |
| urban_planning | 도시계획 | 249 |

Structure-based classification via `AG/agent/law-domain-setup/initialize_domains.py`.

## Upstream Consumers

This server is called by two upstream services. Do NOT change the REST API contract without updating both:

```
ACE MCP Server (autogen_studio_server.py)
  ├── law_search()         → POST /api/search          (direct, fast)
  ├── law_search_domain()  → POST /api/domain/{id}/search
  ├── law_domains()        → GET  /api/domains
  └── law_health()         → GET  /api/health

ARR Django Backend (:8000, law/views.py)
  ├── /law/search/         → POST /api/search           (proxied, logged to DB)
  ├── /law/domain/{id}/search/ → POST /api/domain/{id}/search
  ├── /law/domains/        → GET  /api/domains
  └── /law/health/         → GET  /api/health
```

## Pipeline Status (2026-02-27 — FULL PIPELINE COMPLETE)

- **18 laws loaded** (2026-02-27): 6개 법률(국토계획법, 건축법, 농지법, 산지관리법, 자연공원법, 수도법) × 3 types
- **Node counts**: LAW 18, HANG 6171, HO 6026, MOK 1284, JO 2431, JANG 96, JEOL 50, Domain 5 (total 16,081)
- **Step3 embeddings**: DONE - ALL 6171 HANG nodes, OpenAI text-embedding-3-large 3072-dim
- **Step4 domains**: DONE - 5 domains (land_use:2286, national:2004, building:1018, zoning:614, urban:249)
- **Step5 rel-embeddings**: DONE - ALL 16,058 CONTAINS rel embeddings, `contains_embedding` ONLINE
- **Vector indexes**: 5 ONLINE (hang, ho, mok, jo, contains — all 3072-dim cosine)
- **Fulltext indexes**: `hang_content_fulltext` (CJK bi-gram), `jo_content_fulltext`
- **Cross-law search**: "용도지역"→6 laws(ALL), "농지전용"→농지+산지+국토(법률+시행령+시행규칙), "수도시설"→수도법(3 types)
- **Search improvements (2026-02-24 v2)**: Fulltext CJK, MMR diversity, RNE 0.35, per-law cap
- **Pipeline docs**: `SEARCH_PIPELINE_REVIEW.md`, `ARR/backend/law/PIPELINE.md`
- Previous fixes: server.py cross-domain, KR-SBERT removed, 제4절 filter removed, session leak fixed

## Testing

- **Without Neo4j**: Only unit-test pure functions (`_reciprocal_rank_fusion`, `_merge_results`)
- **With Neo4j**: Full integration tests via `/api/search` endpoint
- **Neo4j check**: `curl http://localhost:8011/api/health`
- **Cross-project**: `C:/Python313/python tests/test_law_pipeline.py -v` (from 25_ACE root)
- **Test results**: 28 structural + 21 integration + 5 live E2E = 54 tests all pass
