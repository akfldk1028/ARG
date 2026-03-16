# Law Domain Setup - Claude Code Context

## Overview

Neo4j initialization scripts for the law domain graph database.
Creates Domain nodes, classifies HANG nodes into domains, and manages vector indexes.

## Files

| File | Purpose |
|------|---------|
| `initialize_domains.py` | Create 2 Domain nodes, classify HANG->Domain via keyword/structural rules |
| `recreate_vector_index.py` | Drop + recreate Neo4j vector indexes (3072-dim OpenAI) |
| `check_hang_patterns.py` | Diagnostic: sample HANG node identifiers |
| `check_article_36.py` | Diagnostic: locate specific article (제36조) |

## Prerequisites

- **Neo4j** on `bolt://localhost:7687` (NEO4J_PASSWORD env required)
- **Python**: Uses shared neo4j_client from `../law-domain-agents/shared/`

## Run

```bash
cd AG/agent/law-domain-setup
# First time: create domains and classify nodes
python initialize_domains.py

# If vector indexes need rebuild:
python recreate_vector_index.py
```

## Domain Classification Rules (5 domains, 18 laws)

Each HANG node is classified into one of 5 domains based on full_id prefix + chapter:

| Domain | domain_id | Rule | Nodes |
|--------|-----------|------|-------|
| 토지이용규제 | land_use_regulation | full_id starts with 농지법/산지관리법/자연공원법/수도법 | 2286 |
| 국토계획 총론 | national_land_planning | 국토계획법 catch-all | 2004 |
| 건축기준 | building_standards | full_id starts with "건축법" | 1018 |
| 용도지역 및 건축규제 | zoning_regulation | 국토계획법 + "::제4장::" in full_id | 614 |
| 도시계획 | urban_planning | 국토계획법 + "::제3장::" or "::제6장::" | 249 |

Rule priority: building_standards → land_use_regulation → zoning → urban_planning → national_land_planning

## Current Status (2026-02-27)

- **Neo4j**: `bolt://localhost:7687`, pw=`11111111` (Neo4j Desktop)
- **18 laws loaded**: 6개 법률(국토계획법, 건축법, 농지법, 산지관리법, 자연공원법, 수도법) × 3 types
- **Domains**: 5 created (total 6171 HANG nodes classified, 0 orphans)
- **Node counts**: LAW 18, HANG 6171, HO 6026, MOK 1284, JO 2431, JANG 96, JEOL 50 (total 16,081)
- **Vector indexes**: 5 ONLINE (hang, ho, mok, jo, contains — all 3072-dim cosine)
- **Embeddings**: ALL 6171 HANG nodes + ALL 16,058 CONTAINS rels have OpenAI text-embedding-3-large 3072-dim vectors
- **Pipeline docs**: `ARR/backend/law/PIPELINE.md`

## Testing

All scripts require Neo4j. No mock-based testing available.

## New Data Source (2026-02-23)

`ARR/backend/law/scripts/law_downloader.py` downloads structured law data via law.go.kr Open API.
Output JSON is compatible with step2 (json_to_neo4j). After downloading new laws, re-run step2→step3→step4.
See `ARR/backend/CLAUDE.md` for usage.
