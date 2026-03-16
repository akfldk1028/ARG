# QueryCoordinator Agent

**Status**: 미구현 (Phase 5에서 구현 예정)

## Purpose

다중 도메인 에이전트 간 쿼리 라우팅 및 응답 종합. 현재 `server.py`가 단일 도메인(용도지역)으로 자동 라우팅하므로 coordinator는 불필요.

Phase 5 (Agent 협업)에서 건축관련법 전체 적재 후 다중 도메인 병렬 검색 시 필요.

## 예상 Architecture

```
User Query
    ↓
QueryCoordinator
    ├─> Domain 1: 용도지역 (land_use_zones)
    ├─> Domain 2: 개발행위 (development_activities)
    ├─> Domain 3: 토지거래 (land_transactions)
    ├─> Domain 4: 도시계획 (urban_planning)
    └─> Domain 5: 도시개발 (urban_development)
    ↓
RRF Merging + Synthesis
    ↓
Final Response
```

## 현재 대안

`law_search_engine.py`의 5-stage hybrid search가 단일 도메인 내에서 exact + vector + relationship + RNE + RRF를 모두 처리.
