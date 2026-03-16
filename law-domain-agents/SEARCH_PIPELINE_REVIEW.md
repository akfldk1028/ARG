# Law Search Pipeline Review (2026-02-24, v2 — Post-Improvement)

## Pipeline Overview (CURRENT)

```
[1] Embedding     → OpenAI text-embedding-3-large (3072-dim)
[2] Hybrid Search → Exact Match + Fulltext CJK + Vector Search + Relationship → RRF
                    (각 stage에 법률별 다양성 cap 적용)
[3] RNE           → Graph expansion (JO 이웃 HANG, cosine >= 0.35)
[4] Merge         → Hybrid + RNE dedup (2x top_k 후보)
[4.5] MMR         → Maximal Marginal Relevance 재정렬 (λ=0.7)
[4.6] Hierarchy   → 법률↔시행령↔시행규칙 인용 교차검색
[5] Enrichment    → law_name, law_type, article 추가 + top_k 절단
```

## Stage별 상태

| Stage | 상태 | 비고 |
|-------|------|------|
| Exact Match | ✅ 작동 | 조항번호 있을 때만 |
| Fulltext Keyword | ✅ **NEW** | CJK bi-gram, 법률당 max 3개 cap |
| Vector Search | ✅ 작동 | 법률당 max 4개 cap |
| Relationship | ❌ 비활성 | `contains_embedding` 인덱스 없음 (step5 미완) |
| RNE Expansion | ✅ **FIXED** | threshold 0.65→0.35, 이제 결과 나옴 |
| MMR Reranking | ✅ **NEW** | λ=0.7, 2x 후보에서 top_k 선별 |
| Hierarchy Expansion | ✅ 작동 | 법률↔시행령↔시행규칙 인용 교차 |
| RRF + Enrichment | ✅ 작동 | 4 signals (exact, fulltext, vector, rel) |

## 개선 이력 (2026-02-24)

### P0 — Fulltext CJK Keyword Search [DONE]

- Neo4j fulltext index `hang_content_fulltext` (CJK bi-gram analyzer)
- `_fulltext_keyword_search()`: 조항번호 제거 후 키워드로 content 검색
- **법률별 다양성**: 4x fetch + 법률당 max 3개 cap
- 효과: "건폐율" → 건축법 직접 발견, "용도지역" → 6개 법률 발견

### P1 — MMR Diversity Reranking [DONE]

- Carbonell & Goldstein 1998 기반 MMR (λ=0.7)
- `MMR = argmax [λ·Sim(d,q) - (1-λ)·max Sim(d,d_j)]`
- `_hybrid_search()` 2x limit 반환 → MMR이 top_k 선별
- `_fetch_embeddings()`: Neo4j에서 HANG 임베딩 일괄 조회
- Fallback: `_jo_level_dedup()` (조당 max 2항)

### P1.5 — 법률별 다양성 Cap [DONE]

- `_fulltext_keyword_search()`: 법률당 max 3개
- `_vector_search()`: 법률당 max 4개
- 4x fetch → per-law cap → diverse candidates for RRF
- 효과: "용도지역" limit=40 → ALL 6 laws represented

### P2 — RNE Threshold [DONE]

- 0.65 → 0.35 (`domain_agent_factory.py` 하드코딩도 수정)
- 이제 평균 3-11개 결과 (쿼리에 따라)
- HANG 항 단위 이웃은 유사도 0.15-0.39 범위

## 검색 결과 비교 (Before vs After)

### "용도지역" (limit=15)
| | Before | After |
|---|--------|-------|
| 법률 수 | 1 (국토계획법만) | **4** (국토+자연공원+농지+산지) |
| Stage | vector only | vector+fulltext+hierarchy |
| 법타입 | 시행령만 | 법률+시행령+시행규칙 |

### "용도지역" (limit=40)
| | Before | After |
|---|--------|-------|
| 법률 수 | 1 | **6 (ALL)** |
| 건축법 | 0 | 12 |
| 산지관리법 | 0 | 7 |
| 자연공원법 | 0 | 4 |

### "건폐율" (limit=15)
| | Before | After |
|---|--------|-------|
| 법률 수 | 1-2 | **3** (국토+건축+농지) |
| 건축법 | 0-1 | **5** |
| RNE | 0 | 작동 |

### "농지전용" (limit=15)
| | Before | After |
|---|--------|-------|
| 법률 수 | 2 | **3** (농지+산지+국토) |
| RNE | 0 | 1 |

## 임베딩 검증

```
쿼리 임베딩:   OpenAI text-embedding-3-large (3072-dim) ✅
DB 임베딩:     동일 모델 (step3에서 생성)               ✅
Vector Index:  hang_embedding_index (ONLINE, cosine)     ✅
Fulltext Idx:  hang_content_fulltext (CJK bi-gram)       ✅ NEW
RNE 계산:      Python cosine_similarity, thresh=0.35     ✅ FIXED
MMR 계산:      Python cosine_similarity, λ=0.7           ✅ NEW
Rel Index:     contains_embedding → 존재하지 않음         ❌ (step5 미완)
```

## 남은 과제

### BUG #3 — Exact match substring 오탐 [LOW]

`h.full_id CONTAINS '제7조'` → 제17조, 제77조도 매칭. `'_제7조_'` 경계 지정 필요.

### ISSUE #5 — Relationship search 미구현 [LOW, 장기]

`contains_embedding` 인덱스 없음. step5 실행 필요. 현재 graceful degradation.

### 용도지역 limit=15 미비 [MEDIUM]

limit=15에서 4/6 법률만 포함. limit=40이면 6/6. 건축법은 "용도지역" 단어 빈도가 낮아 fulltext score에서 밀림.
가능한 개선: 법률별 최소 보장 슬롯 (min 1-2 per law).
