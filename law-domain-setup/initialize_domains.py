"""
Law Structure-Based Domain Initialization (Multi-Law)

Classifies HANG nodes from 10 laws into 5 domains.
Rule order matters: specific rules BEFORE general (catch-all).

Usage:
    python agent/law-domain-setup/initialize_domains.py
"""

import sys
from pathlib import Path

# Add law-domain-agents/shared to path for neo4j_client
agent_root = Path(__file__).parent.parent
sys.path.insert(0, str(agent_root / "law-domain-agents" / "shared"))

from neo4j_client import get_neo4j_client
from datetime import datetime


# 국토계획법 full_id prefix (PDF pipeline uses slightly different name)
KUKTO_PREFIXES = (
    "국토의 계획 및 이용에 관한 법률",  # PDF pipeline
    "국토의_계획_및_이용에_관한_법률",   # possible variant
)

# Laws that go into land_use_regulation domain
LAND_USE_LAWS = ("농지법", "산지관리법", "자연공원법", "수도법")


# Domain definitions (matches FastAPI DomainManager slug_map)
DOMAINS = [
    {
        "domain_id": "zoning_regulation",
        "domain_name": "용도지역 및 건축규제",
        "description": "국토계획법 제4장 용도지역·지구·구역 + 건폐율·용적률 관련 규정",
    },
    {
        "domain_id": "urban_planning",
        "domain_name": "도시계획",
        "description": "국토계획법 도시·군관리계획, 도시계획시설 (제3장, 제6장 등)",
    },
    {
        "domain_id": "building_standards",
        "domain_name": "건축기준",
        "description": "건축법 전반 (법률·시행령·시행규칙): 건축허가, 구조, 설비 등",
    },
    {
        "domain_id": "land_use_regulation",
        "domain_name": "토지이용규제",
        "description": "농지법, 산지관리법, 자연공원법, 수도법 — 토지 전용·이용 규제",
    },
    {
        "domain_id": "national_land_planning",
        "domain_name": "국토계획 총론",
        "description": "국토계획법 나머지 조항 (총칙, 보칙, 벌칙 등)",
    },
]


def _is_kukto(full_id: str) -> bool:
    """Check if HANG belongs to 국토계획법 (any type: 법률/시행령/시행규칙)."""
    return any(full_id.startswith(p) for p in KUKTO_PREFIXES)


def classify_hang(full_id: str) -> str:
    """
    Classify HANG node to domain based on full_id.

    Rule priority (specific → general):
    1. 건축법* → building_standards
    2. 농지법/산지관리법/자연공원법/수도법 → land_use_regulation
    3. 국토계획법 제4장 → zoning_regulation
    4. 국토계획법 제3장/제6장 → urban_planning
    5. 국토계획법 나머지 → national_land_planning
    """
    # 1. 건축법 (법률/시행령/시행규칙)
    if full_id.startswith("건축법"):
        return "building_standards"

    # 2. 토지이용 관련 개별법
    for law in LAND_USE_LAWS:
        if full_id.startswith(law):
            return "land_use_regulation"

    # 3-5. 국토계획법 세분류
    if _is_kukto(full_id):
        # 제4장: 용도지역·지구·구역
        if "::제4장::" in full_id:
            return "zoning_regulation"
        # 제3장: 광역도시계획, 제6장: 도시계획시설
        if "::제3장::" in full_id or "::제6장::" in full_id:
            return "urban_planning"
        # 나머지 국토계획법
        return "national_land_planning"

    # Fallback: national_land_planning
    return "national_land_planning"


def main():
    print("=" * 80)
    print("Multi-Law Domain Initialization (10 laws → 5 domains)")
    print("=" * 80)

    # Neo4j connection
    print("\n[1/5] Connecting to Neo4j...")
    client = get_neo4j_client()
    session = client.get_session()

    # Delete existing Domain nodes (clean start)
    print("[2/5] Deleting existing Domain nodes...")
    session.run("MATCH (d:Domain) DETACH DELETE d")
    print("  > Existing domains deleted")

    # Load all HANG nodes
    print("[3/5] Loading HANG nodes...")
    query = "MATCH (h:HANG) RETURN h.full_id as full_id"
    results = session.run(query)
    hang_nodes = [r["full_id"] for r in results]
    print(f"  > Loaded {len(hang_nodes)} HANG nodes")

    # Classify HANG nodes by domain
    print("[4/5] Classifying HANG nodes by domain...")
    domain_assignments = {d["domain_id"]: [] for d in DOMAINS}

    for full_id in hang_nodes:
        domain_id = classify_hang(full_id)
        domain_assignments[domain_id].append(full_id)

    # Print distribution statistics
    print("\n  Domain distribution:")
    for domain in DOMAINS:
        count = len(domain_assignments[domain["domain_id"]])
        print(f"    - {domain['domain_name']} ({domain['domain_id']}): {count} nodes")

    # Create Domain nodes and relationships
    print("\n[5/5] Creating Domain nodes and relationships...")
    created_at = datetime.now().isoformat()

    for domain in DOMAINS:
        domain_id = domain["domain_id"]
        hang_ids = domain_assignments[domain_id]

        if not hang_ids:
            print(f"  ! WARNING: {domain['domain_name']}: 0 nodes, skipping")
            continue

        session.run("""
        CREATE (d:Domain {
            domain_id: $domain_id,
            domain_name: $domain_name,
            description: $description,
            node_count: $node_count,
            created_at: $created_at,
            updated_at: $updated_at
        })
        """, {
            "domain_id": domain_id,
            "domain_name": domain["domain_name"],
            "description": domain["description"],
            "node_count": len(hang_ids),
            "created_at": created_at,
            "updated_at": created_at,
        })

        session.run("""
        UNWIND $hang_ids as hang_id
        MATCH (h:HANG {full_id: hang_id})
        MATCH (d:Domain {domain_id: $domain_id})
        CREATE (h)-[:BELONGS_TO_DOMAIN]->(d)
        """, {"hang_ids": hang_ids, "domain_id": domain_id})

        print(f"  > OK: {domain['domain_name']}: {len(hang_ids)} nodes")

    session.close()

    # Verification
    print("\n" + "=" * 80)
    print("Verification")
    print("=" * 80)

    session = client.get_session()

    domain_count = session.run("MATCH (d:Domain) RETURN count(d) as c").single()["c"]
    rel_count = session.run("MATCH ()-[r:BELONGS_TO_DOMAIN]->() RETURN count(r) as c").single()["c"]

    print(f"\n  Domain nodes: {domain_count}")
    print(f"  BELONGS_TO_DOMAIN rels: {rel_count}")
    print(f"\n  Per domain:")

    details = session.run("""
    MATCH (h:HANG)-[:BELONGS_TO_DOMAIN]->(d:Domain)
    RETURN d.domain_id as id, d.domain_name as name, count(h) as size
    ORDER BY size DESC
    """)
    for d in details:
        print(f"    - {d['name']} ({d['id']}): {d['size']} nodes")

    session.close()

    print("\n" + "=" * 80)
    print("SUCCESS! Restart FastAPI server to pick up new domains.")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
