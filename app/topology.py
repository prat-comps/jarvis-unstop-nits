"""
J.A.R.V.I.S. - Service topology / dependency model.

The topology is the "world knowledge" of the engine. It tells J.A.R.V.I.S.
which service depends on which, so that a fault can be propagated downstream
and used to score how plausible a candidate root cause is.

Scenario: a digital payment platform (matches the suggested challenge scenario).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Service:
    key: str
    name: str
    kind: str
    tier: str  # edge | application | data | infra
    criticality: int  # 1 (low) .. 5 (critical) - drives impact scoring
    depends_on: List[str] = field(default_factory=list)
    users_exposed: int = 0  # baseline daily active users touching this service


SERVICES: Dict[str, Service] = {
    s.key: s
    for s in [
        Service("waf", "Edge WAF / API Gateway", "gateway", "edge", 5, [], 420_000),
        Service("auth", "Auth Service", "application", "application", 5, ["waf", "session-store", "user-db"], 420_000),
        Service("session-store", "Session Store (Redis)", "cache", "data", 5, [], 420_000),
        Service("payment-api", "Payment API", "application", "application", 5, ["waf", "auth", "ledger-db", "psp-connector"], 310_000),
        Service("psp-connector", "PSP Connector", "integration", "application", 4, ["waf", "vendor-psp"], 310_000),
        Service("vendor-psp", "Vendor Payment Gateway (3rd party)", "external", "edge", 4, [], 310_000),
        Service("ledger-db", "Ledger DB (PostgreSQL)", "database", "data", 5, ["db-proxy"], 310_000),
        Service("user-db", "User DB (PostgreSQL)", "database", "data", 4, ["db-proxy"], 420_000),
        Service("db-proxy", "DB Connection Proxy (PgBouncer)", "infra", "infra", 5, ["db-host"], 420_000),
        Service("db-host", "Database Host (VM)", "infra", "infra", 5, [], 420_000),
        Service("notification", "Notification Service", "application", "application", 2, ["waf", "queue"], 120_000),
        Service("queue", "Message Queue (Kafka)", "infra", "infra", 3, [], 200_000),
        Service("checkout-ui", "Checkout Web UI", "frontend", "edge", 5, ["waf", "payment-api"], 300_000),
        Service("mobile-app", "Mobile Banking App", "frontend", "edge", 4, ["waf", "payment-api", "auth"], 380_000),
    ]
}


def dependents_of(service_key: str) -> List[str]:
    """Services that directly depend on the given service (downstream blast radius)."""
    return [s.key for s in SERVICES.values() if service_key in s.depends_on]


def blast_radius(service_key: str) -> List[str]:
    """Transitive set of services affected if `service_key` fails."""
    seen, stack = [], [service_key]
    while stack:
        cur = stack.pop()
        for dep in dependents_of(cur):
            if dep not in seen:
                seen.append(dep)
                stack.append(dep)
    return seen


def path_from_root(root: str, target: str) -> List[str]:
    """Shortest dependency path root -> target (root's failure travels this way)."""
    prev, queue, visited = {}, [root], {root}
    while queue:
        cur = queue.pop(0)
        if cur == target:
            path = [cur]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            return list(reversed(path))
        for dep in dependents_of(cur):
            if dep not in visited:
                visited.add(dep)
                prev[dep] = cur
                queue.append(dep)
    return []


def users_impacted(affected: List[str]) -> int:
    """Approximate distinct affected users = max exposure across affected edge surfaces."""
    exposure = [SERVICES[a].users_exposed for a in affected if a in SERVICES]
    return max(exposure) if exposure else 0


def topology_payload() -> dict:
    return {
        "nodes": [
            {
                "key": s.key,
                "name": s.name,
                "kind": s.kind,
                "tier": s.tier,
                "criticality": s.criticality,
                "users_exposed": s.users_exposed,
            }
            for s in SERVICES.values()
        ],
        "edges": [
            {"source": s.key, "target": dep} for s in SERVICES.values() for dep in s.depends_on
        ],
    }
