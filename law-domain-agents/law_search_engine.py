"""
Law Search Engine - Django 없이 독립 실행

Backend의 RNE/INE 검색 알고리즘을 추출하여 FastAPI에서 사용
Django 의존성 완전 제거

핵심 기능:
- Hybrid Search (Exact + Vector + Relationship)
- RNE Graph Expansion
- INE Semantic Search

Dependencies:
- Neo4j
- OpenAI API (text-embedding-3-large, 3072-dim)
- numpy, sklearn
"""

import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Import law utilities for result enrichment
from law_utils import enrich_search_results

logger = logging.getLogger(__name__)


class LawSearchEngine:
    """
    독립 실행 가능한 법률 검색 엔진

    Backend domain_agent.py에서 추출한 RNE/INE 알고리즘 사용
    """

    def __init__(
        self,
        neo4j_client,  # shared.neo4j_client.get_neo4j_client()
        openai_client,  # shared.openai_client.get_openai_client()
        domain_id: Optional[str] = None,
        domain_name: str = "전체",
        rne_threshold: float = 0.35,
        ine_k: int = 10
    ):
        """
        Args:
            neo4j_client: Neo4j 클라이언트 (agent/shared/neo4j_client.py)
            openai_client: OpenAI 클라이언트 (agent/shared/openai_client.py)
            domain_id: 도메인 ID (None = 전체 검색)
            domain_name: 도메인 이름
            rne_threshold: RNE 유사도 임계값 (0.65 권장)
            ine_k: INE top-k 결과 (10 권장)
        """
        self.neo4j_client = neo4j_client
        self.openai_client = openai_client

        self.domain_id = domain_id
        self._effective_domain_id = domain_id  # default; overridden per-search call
        self.domain_name = domain_name

        self.rne_threshold = rne_threshold
        self.ine_k = ine_k

        logger.info(f"LawSearchEngine initialized for '{domain_name}'")

    # ========== PUBLIC API ==========

    def search(self, query: str, top_k: int = 10, domain_id_override: str = None) -> List[Dict]:
        """
        메인 검색 메소드

        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
            domain_id_override: 도메인 ID 오버라이드 (""=전체, None=기본값 사용)

        Returns:
            검색 결과 리스트
        """
        # Thread-safe: 인스턴스 상태를 변경하지 않고 로컬 변수 사용
        if domain_id_override is not None:
            effective_domain_id = domain_id_override if domain_id_override else None
        else:
            effective_domain_id = self.domain_id
        self._effective_domain_id = effective_domain_id
        logger.info(f"[{self.domain_name}] Search: {query[:50]}...")

        try:
            # [1] 임베딩 생성 (OpenAI 3072-dim only)
            openai_emb = self._generate_openai_embedding(query)
            if openai_emb is None:
                logger.warning(f"Embedding generation failed, falling back to exact+fulltext only")
                exact = self._exact_match_search(query, limit=top_k)
                fulltext = self._fulltext_keyword_search(query, limit=top_k)
                merged = self._merge_results(exact, fulltext)
                return enrich_search_results(merged[:top_k])

            # [2] Hybrid 검색
            hybrid_results = self._hybrid_search(query, openai_emb, openai_emb, limit=top_k)

            if not hybrid_results:
                logger.warning(f"No results for: {query[:30]}...")
                return []

            # [3] RNE 그래프 확장 (상위 5개 결과 기반)
            rne_results = self._rne_graph_expansion(
                query,
                hybrid_results[:5],
                openai_emb
            )

            # [4] 결과 병합
            all_results = self._merge_results(hybrid_results, rne_results)

            # [4.5] MMR 다양성 재정렬 (법률별 독점 방지)
            all_results = self._mmr_diversity_rerank(
                all_results, openai_emb, top_k=top_k, lambda_param=0.7
            )

            # [4.6] 법령 체계 확장 (법률↔시행령↔시행규칙)
            hierarchy_results = self._law_hierarchy_expansion(all_results)
            if hierarchy_results:
                # 상위 5개 뒤에 삽입 → top_k 안에 포함되도록
                insert_pos = min(5, len(all_results))
                all_results[insert_pos:insert_pos] = hierarchy_results

            # [5] 결과 enrichment - law_name, law_type, article 추가
            enriched_results = enrich_search_results(all_results[:top_k])

            logger.info(f"[{self.domain_name}] Found {len(enriched_results)} results")

            return enriched_results

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return []

    # ========== CORE SEARCH METHODS ==========

    def _hybrid_search(
        self,
        query: str,
        node_emb: List[float],
        rel_emb: List[float],
        limit: int = 10
    ) -> List[Dict]:
        """
        Hybrid Search: Exact + Vector + Relationship

        Backend domain_agent.py Line 271-315 기반
        ✅ FIXED: Both use OpenAI 3072-dim embeddings
        """
        logger.info(f"[{self.domain_name}] Running hybrid search (Exact + Fulltext + Vector + Rel)...")

        # [1] Exact match (조항번호)
        exact_results = self._exact_match_search(query, limit=limit)

        # [2] Fulltext keyword search (CJK, content 본문)
        fulltext_results = self._fulltext_keyword_search(query, limit=limit)

        # [3] Vector search (OpenAI, 3072-dim)
        vector_results = self._vector_search(node_emb, limit=limit)

        # [4] Relationship search (OpenAI, 3072-dim)
        rel_results = self._search_relationships(rel_emb, limit=limit)

        # [5] Reciprocal Rank Fusion (4 signals)
        fused_results = self._reciprocal_rank_fusion([
            exact_results,
            fulltext_results,
            vector_results,
            rel_results
        ])

        # Return 2x limit for downstream MMR diversity reranking
        return fused_results[:limit * 2]

    def _exact_match_search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        정확 일치 검색 (조문 번호 추출)

        Backend domain_agent.py Line 166-219 기반
        ✅ FIXED: Use CONTAINS on full_id instead of article_number IN
        """
        # 조항 번호 패턴 추출 (제17조, 17조 등)
        article_pattern = re.search(r'제?(\d+)조', query)

        if not article_pattern:
            return []  # 조항 번호 없으면 빈 리스트 반환

        article_num = article_pattern.group(1)
        search_pattern = f'제{article_num}조'

        logger.info(f"[{self.domain_name}] Exact match pattern: {search_pattern}")

        # Neo4j 쿼리 - full_id CONTAINS 사용
        cypher_query = """
        MATCH (h:HANG)
        WHERE h.full_id CONTAINS $search_pattern
        """

        if self._effective_domain_id:
            cypher_query += """
          AND EXISTS((h)-[:BELONGS_TO_DOMAIN]->(:Domain {domain_id: $domain_id}))
            """

        cypher_query += """
        RETURN h.full_id as hang_id,
               h.content as content,
               h.unit_path as unit_path,
               1.0 as similarity
        LIMIT $limit
        """

        try:
            with self.neo4j_client.get_session() as session:
                results = session.run(cypher_query, {
                    'search_pattern': search_pattern,
                    'domain_id': self._effective_domain_id,
                    'limit': limit
                })

                exact_results = []
                for r in results:
                    exact_results.append({
                        'hang_id': r['hang_id'],
                        'content': r['content'],
                        'unit_path': r['unit_path'],
                        'similarity': r['similarity'],
                        'stage': 'exact_match'
                    })

            logger.info(f"[{self.domain_name}] Exact match: {len(exact_results)} results for {search_pattern}")
            return exact_results

        except Exception as e:
            logger.error(f"Exact match search error: {e}")
            return []

    def _fulltext_keyword_search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Fulltext 키워드 검색 (Neo4j CJK analyzer, Lucene 기반)

        P0 개선: content 본문에서 키워드 검색.
        "건폐율" → 건축법 제77조 직접 발견 (vector search에선 놓침)
        Index: hang_content_fulltext (CJK bi-gram analyzer)

        법률별 다양성 보장: 한 법률이 top-K를 독점하지 않도록
        4x 결과를 가져와서 법률당 max 3개로 cap.
        "용도지역" → 6개 법률 모두 포함 (국토계획법만 독점 방지)
        """
        # 조항번호 제거, 순수 키워드만 추출
        keywords = re.sub(r'제?\d+조\s*', '', query).strip()
        if not keywords:
            return []

        logger.info(f"[{self.domain_name}] Fulltext keyword: '{keywords}'")

        # 4x fetch for per-law diversity
        fetch_limit = limit * 4

        cypher_query = """
        CALL db.index.fulltext.queryNodes('hang_content_fulltext', $keywords)
        YIELD node, score
        """

        if self._effective_domain_id:
            cypher_query += """
            WHERE EXISTS((node)-[:BELONGS_TO_DOMAIN]->(:Domain {domain_id: $domain_id}))
            """

        cypher_query += """
        RETURN node.full_id as hang_id,
               node.content as content,
               node.unit_path as unit_path,
               score as similarity
        LIMIT $limit
        """

        try:
            with self.neo4j_client.get_session() as session:
                results = session.run(cypher_query, {
                    'keywords': keywords,
                    'limit': fetch_limit,
                    'domain_id': self._effective_domain_id
                })

                raw_results = []
                for r in results:
                    raw_results.append({
                        'hang_id': r['hang_id'],
                        'content': r['content'],
                        'unit_path': r['unit_path'],
                        'similarity': float(r['similarity']),
                        'stage': 'fulltext_keyword'
                    })

            # Per-law diversity cap: max 3 per law_name
            from law_utils import parse_hang_id
            law_counts = {}
            max_per_law = 3
            fulltext_results = []
            for r in raw_results:
                info = parse_hang_id(r['hang_id'])
                law = info['law_name'] or 'unknown'
                law_counts[law] = law_counts.get(law, 0) + 1
                if law_counts[law] <= max_per_law:
                    fulltext_results.append(r)
                if len(fulltext_results) >= limit:
                    break

            law_diversity = len(law_counts)
            logger.info(f"[{self.domain_name}] Fulltext keyword: {len(fulltext_results)} results ({law_diversity} laws, cap={max_per_law}/law)")
            return fulltext_results

        except Exception as e:
            logger.error(f"Fulltext keyword search error: {e}")
            return []

    def _vector_search(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """
        벡터 검색 (OpenAI, 3072-dim)

        Backend domain_agent.py Line 317-360 기반
        ✅ FIXED: Now uses OpenAI embeddings
        법률별 다양성: 4x fetch + 법률당 max 4개 cap
        """
        fetch_limit = limit * 4

        cypher_query = """
        CALL db.index.vector.queryNodes('hang_embedding_index', $limit, $embedding)
        YIELD node, score
        """

        if self._effective_domain_id:
            cypher_query += """
            WHERE EXISTS((node)-[:BELONGS_TO_DOMAIN]->(:Domain {domain_id: $domain_id}))
            """

        cypher_query += """
        RETURN node.full_id as hang_id,
               node.content as content,
               node.unit_path as unit_path,
               score as similarity
        """

        try:
            with self.neo4j_client.get_session() as session:
                results = session.run(cypher_query, {
                    'embedding': query_embedding,
                    'limit': fetch_limit,
                    'domain_id': self._effective_domain_id
                })

                raw_results = []
                for r in results:
                    raw_results.append({
                        'hang_id': r['hang_id'],
                        'content': r['content'],
                        'unit_path': r['unit_path'],
                        'similarity': r['similarity'],
                        'stage': 'vector_search'
                    })

            # Per-law diversity cap: max 4 per law_name
            from law_utils import parse_hang_id
            law_counts = {}
            max_per_law = 4
            vector_results = []
            for r in raw_results:
                info = parse_hang_id(r['hang_id'])
                law = info['law_name'] or 'unknown'
                law_counts[law] = law_counts.get(law, 0) + 1
                if law_counts[law] <= max_per_law:
                    vector_results.append(r)
                if len(vector_results) >= limit:
                    break

            law_diversity = len(law_counts)
            logger.info(f"[{self.domain_name}] Vector search: {len(vector_results)} results ({law_diversity} laws, cap={max_per_law}/law)")
            return vector_results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    def _search_relationships(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """
        관계 임베딩 검색 (CONTAINS 관계, OpenAI 3072-dim)

        Backend domain_agent.py Line 362-408 기반
        ✅ FIXED: Use db.index.vector.queryRelationships instead of node property
        """
        cypher_query = """
        CALL db.index.vector.queryRelationships(
            'contains_embedding',
            $limit_multiplier,
            $query_embedding
        ) YIELD relationship, score
        MATCH (from)-[relationship]->(to:HANG)
        WHERE score >= 0.65
        """

        if self._effective_domain_id:
            cypher_query += """
          AND EXISTS((to)-[:BELONGS_TO_DOMAIN]->(:Domain {domain_id: $domain_id}))
            """

        cypher_query += """
        RETURN
            to.full_id AS hang_id,
            to.content AS content,
            to.unit_path AS unit_path,
            score AS similarity
        ORDER BY similarity DESC
        LIMIT $limit
        """

        try:
            with self.neo4j_client.get_session() as session:
                results = session.run(cypher_query, {
                    'query_embedding': query_embedding,
                    'limit': limit,
                    'limit_multiplier': limit * 3,
                    'domain_id': self._effective_domain_id
                })

                rel_results = []
                for r in results:
                    rel_results.append({
                        'hang_id': r['hang_id'],
                        'content': r['content'],
                        'unit_path': r['unit_path'],
                        'similarity': float(r['similarity']),
                        'stage': 'relationship'
                    })

            logger.info(f"[{self.domain_name}] Relationship search: {len(rel_results)} results")
            return rel_results

        except Exception as e:
            logger.error(f"Relationship search error: {e}")
            return []

    def _rne_graph_expansion(
        self,
        query: str,
        initial_results: List[Dict],
        openai_embedding: List[float]
    ) -> List[Dict]:
        """
        RNE 그래프 확장

        Backend domain_agent.py Line 492-559 기반
        ✅ FIXED: Now uses OpenAI embeddings (3072-dim)

        TODO: SemanticRNE 클래스 사용 (현재는 간단한 버전)
        """
        if not initial_results:
            return []

        logger.info(f"[{self.domain_name}] RNE expansion from {len(initial_results)} seeds...")

        # 간단 버전: 초기 결과의 이웃 노드 찾기
        start_ids = [r['hang_id'] for r in initial_results[:3]]

        cypher_query = """
        MATCH (start:HANG)
        WHERE start.full_id IN $start_ids

        MATCH (start)<-[:CONTAINS]-(jo:JO)-[:CONTAINS]->(neighbor:HANG)
        WHERE neighbor.full_id <> start.full_id
          AND neighbor.embedding IS NOT NULL
        """

        if self._effective_domain_id:
            cypher_query += """
          AND EXISTS((neighbor)-[:BELONGS_TO_DOMAIN]->(:Domain {domain_id: $domain_id}))
            """

        cypher_query += """
        RETURN DISTINCT neighbor.full_id as hang_id,
                        neighbor.content as content,
                        neighbor.unit_path as unit_path,
                        neighbor.embedding as embedding
        LIMIT 50
        """

        try:
            with self.neo4j_client.get_session() as session:
                results = list(session.run(cypher_query, {
                    'start_ids': start_ids,
                    'domain_id': self._effective_domain_id
                }))

            # 코사인 유사도 계산 (OpenAI 3072-dim)
            query_vec = np.array(openai_embedding).reshape(1, -1)
            rne_results = []

            for r in results:
                emb = np.array(r['embedding']).reshape(1, -1)
                similarity = cosine_similarity(query_vec, emb)[0][0]

                if similarity >= self.rne_threshold:
                    rne_results.append({
                        'hang_id': r['hang_id'],
                        'content': r['content'],
                        'unit_path': r['unit_path'],
                        'similarity': float(similarity),
                        'stage': 'rne_expansion'
                    })

            logger.info(f"[{self.domain_name}] RNE expansion: {len(rne_results)} results (threshold: {self.rne_threshold})")
            return rne_results

        except Exception as e:
            logger.error(f"RNE expansion error: {e}")
            return []

    # ========== HELPER METHODS ==========

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        k: int = 60
    ) -> List[Dict]:
        """
        Reciprocal Rank Fusion (RRF)

        Backend domain_agent.py Line 221-269 기반
        """
        scores = {}

        for result_list in result_lists:
            for rank, result in enumerate(result_list, 1):
                hang_id = result['hang_id']

                if hang_id not in scores:
                    scores[hang_id] = {
                        'score': 0.0,
                        'result': result
                    }

                scores[hang_id]['score'] += 1.0 / (k + rank)

        # 점수 순 정렬
        ranked = sorted(scores.values(), key=lambda x: x['score'], reverse=True)

        return [item['result'] for item in ranked]

    def _merge_results(
        self,
        hybrid_results: List[Dict],
        rne_results: List[Dict]
    ) -> List[Dict]:
        """
        Hybrid + RNE 결과 병합

        Backend domain_agent.py Line 574-628 기반
        """
        seen = set()
        merged = []

        # Hybrid 결과 먼저
        for r in hybrid_results:
            hang_id = r['hang_id']
            if hang_id not in seen:
                seen.add(hang_id)
                merged.append(r)

        # RNE 결과 추가
        for r in rne_results:
            hang_id = r['hang_id']
            if hang_id not in seen:
                seen.add(hang_id)
                merged.append(r)

        return merged

    def _mmr_diversity_rerank(
        self,
        results: List[Dict],
        query_embedding: List[float],
        top_k: int = 10,
        lambda_param: float = 0.7
    ) -> List[Dict]:
        """
        MMR (Maximal Marginal Relevance) 다양성 재정렬

        Carbonell & Goldstein 1998 — 관련성과 다양성의 균형:
        MMR = argmax [λ·Sim(d,q) - (1-λ)·max Sim(d,d_j)]
        λ=1.0: 순수 관련성, λ=0.0: 순수 다양성, λ=0.7: 관련성 우선+다양성 보장

        효과: 같은 조의 여러 항이 top-k를 독점하는 것을 방지.
        "건폐율" → 국토계획법(시행령) 제84조 5개 대신, 다른 법률도 포함.
        """
        if len(results) <= top_k:
            return results

        # Neo4j에서 임베딩 일괄 조회
        hang_ids = [r['hang_id'] for r in results]
        embeddings = self._fetch_embeddings(hang_ids)

        if not embeddings:
            # 임베딩 조회 실패시 fallback: JO 단위 dedup
            return self._jo_level_dedup(results, top_k)

        query_vec = np.array(query_embedding).reshape(1, -1)

        # MMR iterative selection
        selected = []
        selected_indices = set()
        candidates = list(range(len(results)))

        for _ in range(min(top_k, len(results))):
            best_idx = None
            best_score = -float('inf')

            for idx in candidates:
                if idx in selected_indices:
                    continue

                hang_id = results[idx]['hang_id']
                emb = embeddings.get(hang_id)
                if emb is None:
                    # 임베딩 없는 결과는 원본 similarity 사용
                    relevance = results[idx].get('similarity', 0.5)
                else:
                    doc_vec = np.array(emb).reshape(1, -1)
                    relevance = float(cosine_similarity(query_vec, doc_vec)[0][0])

                # 이미 선택된 문서와의 최대 유사도
                max_sim_to_selected = 0.0
                if selected:
                    for sel_idx in selected_indices:
                        sel_id = results[sel_idx]['hang_id']
                        sel_emb = embeddings.get(sel_id)
                        if emb is not None and sel_emb is not None:
                            sim = float(cosine_similarity(
                                np.array(emb).reshape(1, -1),
                                np.array(sel_emb).reshape(1, -1)
                            )[0][0])
                            max_sim_to_selected = max(max_sim_to_selected, sim)

                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is None:
                break
            selected.append(results[best_idx])
            selected_indices.add(best_idx)

        logger.info(f"[{self.domain_name}] MMR rerank: {len(results)} -> {len(selected)} (λ={lambda_param})")
        return selected

    def _fetch_embeddings(self, hang_ids: List[str]) -> Dict[str, List[float]]:
        """HANG 노드들의 임베딩을 일괄 조회"""
        try:
            with self.neo4j_client.get_session() as session:
                records = session.run("""
                    MATCH (h:HANG)
                    WHERE h.full_id IN $ids AND h.embedding IS NOT NULL
                    RETURN h.full_id AS fid, h.embedding AS emb
                """, {'ids': hang_ids}).data()
            return {r['fid']: r['emb'] for r in records}
        except Exception as e:
            logger.error(f"Fetch embeddings error: {e}")
            return {}

    def _jo_level_dedup(self, results: List[Dict], top_k: int) -> List[Dict]:
        """JO(조) 단위 중복 제거 — 같은 조에서 최대 2개 항만 유지"""
        from law_utils import parse_hang_id
        jo_counts = {}  # "법명::제N조" -> count
        deduped = []
        for r in results:
            # 조 단위 키 추출: full_id에서 조까지만
            parts = r['hang_id'].split('::')
            jo_key = '::'.join(parts[:3]) if len(parts) >= 3 else r['hang_id']
            jo_counts[jo_key] = jo_counts.get(jo_key, 0) + 1
            if jo_counts[jo_key] <= 2:
                deduped.append(r)
            if len(deduped) >= top_k:
                break
        return deduped

    def _law_hierarchy_expansion(self, results: List[Dict]) -> List[Dict]:
        """
        법령 체계 확장: 법률→시행령→시행규칙 인용 기반 교차 검색

        한국법에서 시행령/시행규칙은 모법 조문을 인용함 (예: "법 제77조제1항에 따른").
        결과에서 법률 조문이 있으면 해당 법의 시행령/시행규칙에서 인용하는 조항을 찾아 추가.
        """
        if not results:
            return []

        from law_utils import parse_hang_id

        # 결과에서 (법명, 법타입, 조번호) 수집
        ALL_TYPES = {'법률', '시행령', '시행규칙'}
        law_articles = {}  # {법명: {법타입: set(조번호)}}
        seen_ids = {r['hang_id'] for r in results}

        for r in results:
            info = parse_hang_id(r['hang_id'])
            law_name = info['law_name']
            law_type = info['law_type']
            if not law_name or not law_type:
                continue

            # 조번호 추출
            article_match = re.search(r'제(\d+)조', r.get('unit_path', '') or r['hang_id'])
            if not article_match:
                continue

            article_num = article_match.group(1)
            law_articles.setdefault(law_name, {}).setdefault(law_type, set()).add(article_num)

        if not law_articles:
            return []

        # 각 법명별로 빠진 타입에서 인용 검색
        expansion_results = []
        for law_name, type_map in law_articles.items():
            present_types = set(type_map.keys())
            missing_types = ALL_TYPES - present_types
            if not missing_types:
                continue

            # 모든 present 조번호 수집
            all_article_nums = set()
            for nums in type_map.values():
                all_article_nums.update(nums)

            for missing_type in missing_types:
                prefix = f"{law_name}({missing_type})"
                for article_num in all_article_nums:
                    ref = f"제{article_num}조"
                    hits = self._search_hierarchy_citation(prefix, ref, seen_ids, limit=2)
                    expansion_results.extend(hits)
                    for h in hits:
                        seen_ids.add(h['hang_id'])

        logger.info(f"[{self.domain_name}] Hierarchy expansion: {len(expansion_results)} results")
        return expansion_results

    def _search_hierarchy_citation(
        self, prefix: str, ref: str, seen_ids: set, limit: int = 2
    ) -> List[Dict]:
        """prefix로 시작하는 HANG에서 ref를 content에 포함하는 노드 검색"""
        cypher = """
        MATCH (h:HANG)
        WHERE h.full_id STARTS WITH $prefix
          AND h.content CONTAINS $ref
        RETURN h.full_id AS hang_id, h.content AS content, h.unit_path AS unit_path
        LIMIT $limit
        """
        try:
            with self.neo4j_client.get_session() as session:
                records = list(session.run(cypher, {
                    'prefix': prefix, 'ref': ref, 'limit': limit
                }))
            results = []
            for r in records:
                if r['hang_id'] not in seen_ids:
                    results.append({
                        'hang_id': r['hang_id'],
                        'content': r['content'],
                        'unit_path': r['unit_path'],
                        'similarity': 0.75,
                        'stage': 'hierarchy_expansion'
                    })
            return results
        except Exception as e:
            logger.error(f"Hierarchy citation search error ({prefix}, {ref}): {e}")
            return []

    def _generate_openai_embedding(self, query: str) -> List[float]:
        """
        OpenAI 임베딩 생성 (3072-dim)

        Backend domain_agent.py Line 879-889 기반
        """
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return None
