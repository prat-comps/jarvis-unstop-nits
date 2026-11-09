"""
J.A.R.V.I.S. - Correlation, root-cause, impact, timeline & recommendation engine.

Deterministic and fully explainable: every number the dashboard shows can be
traced back to a rule. Six stages:

  1. NORMALISE   attach a service node to each event, drop unusable records
  2. SCORE       per-event anomaly score (metric deviation / severity / pattern)
  3. CLUSTER     union-find over link rules (time, topology, trace, service, pattern)
  4. ROOT CAUSE  candidate ranking over topology-aware causality signals
  5. IMPACT      blast radius, criticality, user exposure, lost-path estimate
  6. RECOMMEND   ranked runbook actions attached to the root cause
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import topology as topo

# ------------------------------------------------------------------ weights

W_TIME = 0.30
W_TOPO = 0.35
W_TRACE = 0.25
W_PATTERN = 0.10

# Root candidate score weights
RC_EARLINESS = 0.30
RC_SEVERITY = 0.20
RC_TOPOLOGY = 0.25
RC_ANOMALY = 0.15
RC_AMPLIFICATION = 0.10

SEV_WEIGHT = {"info": 0.05, "warning": 0.45, "error": 0.75, "critical": 1.0}

# Correlation window: events within this distance may be linked
CORRELATION_WINDOW_MIN = 4.0

# Per-service runbooks (deterministic, matched by service kind + pattern)
RUNBOOKS: Dict[str, List[Dict[str, str]]] = {
    "db-host": [
        {"action": "Free disk space on db-host/data-volume", "detail": "Delete rotated WAL archives / old backups and extend the volume (LVM online extend). Target < 70% utilisation.", "effort": "Low", "eta": "10 min", "risk": "Low"},
        {"action": "Move WAL to a dedicated low-latency NVMe volume", "detail": "Separate pg_wal from data files to stop IO contention between checkpoints and reads.", "effort": "Medium", "eta": "45 min", "risk": "Medium"},
        {"action": "Repoint ledger-db to the read replica / failover", "detail": "Controlled failover of ledger-db and user-db to the standby with healthy storage.", "effort": "Medium", "eta": "15 min", "risk": "Medium"},
        {"action": "Add disk-utilisation and iowait alerting at 80%", "detail": "Prevent recurrence: paginate at 80% utilisation and 25% sustained iowait.", "effort": "Low", "eta": "20 min", "risk": "Low"},
    ],
    "db-proxy": [
        {"action": "Raise pgBouncer pool_size and set server_idle_timeout", "detail": "Increase pool from 50 to 120 in transaction mode; add per-service pool_limits so ledger-db cannot starve user-db.", "effort": "Low", "eta": "10 min", "risk": "Low"},
        {"action": "Apply per-service connection quotas", "detail": "Cap auth and payment-api each at a fair share of the pool so one workload cannot exhaust it.", "effort": "Low", "eta": "15 min", "risk": "Low"},
        {"action": "Enable statement timeouts < 5s for interactive queries", "detail": "Fail fast instead of queuing, so clients back off instead of piling up.", "effort": "Low", "eta": "20 min", "risk": "Medium"},
    ],
    "vendor-psp": [
        {"action": "Enable circuit breaker on psp-connector", "detail": "Trip after 20 failures / 30s, serve cached status and queue retries with idempotency keys.", "effort": "Low", "eta": "20 min", "risk": "Low"},
    ],
    "auth": [
        {"action": "Cache negative session lookups + retry with jitter", "detail": "Reduce DB dependency for login: short-lived signed session tokens, exponential backoff with jitter on session-store.", "effort": "Medium", "eta": "2 h", "risk": "Medium"},
    ],
    "payment-api": [
        {"action": "Add bounded retry + bulkhead to ledger calls", "detail": "Max 2 retries with jitter, separate thread pool per dependency so one slow dependency cannot exhaust the API.", "effort": "Medium", "eta": "3 h", "risk": "Medium"},
    ],
    "generic": [
        {"action": "Page the owning team with the correlation report", "detail": "Attach the incident timeline and candidate root causes so responders start with context instead of 40 separate alerts.", "effort": "Low", "eta": "5 min", "risk": "Low"},
        {"action": "Suppress downstream duplicate alerts", "detail": "Mute dependent-service alerts while the root-cause service is unhealthy to reduce alert fatigue.", "effort": "Low", "eta": "10 min", "risk": "Low"},
    ],
}

RECOVERY_PLAYBOOK = [
    "Verify the root-cause metric has returned to baseline before closing downstream incidents.",
    "Backfill the failed payments from the retry queue (idempotency keys prevent double charge).",
    "Re-run the correlation engine over the incident window and store the report as a post-incident artefact.",
    "Add the discovered dependency edge to the topology map if it was missing.",
]


# ------------------------------------------------------------------ helpers


def _dt(iso: str) -> datetime:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone()


def _sev(e: Dict[str, Any]) -> float:
    return SEV_WEIGHT.get(str(e.get("severity", "info")).lower(), 0.2)


def _num(x: Any) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


EVIDENCE_PATTERNS = [
    ("disk_io", r"no space left|disk|iowait|io stall|write to file"),
    ("pool_exhaustion", r"pool|connection slots|too many connections|queue full"),
    ("latency", r"latency|slow|timeout|timed out|p99"),
    ("dependency_error", r"503|502|upstream|downstream|unavailable|refused"),
    ("auth_failure", r"login|auth|session|credential|token"),
    ("payment_failure", r"payment|transaction|checkout|charge|declin"),
    ("rate_limit", r"429|rate limit|throttl"),
]


def classify_pattern(message: str) -> List[str]:
    import re

    return [name for name, rx in EVIDENCE_PATTERNS if re.search(rx, message or "", re.I)]


def is_signal(e: Dict[str, Any]) -> bool:
    """An event worth correlating - anything below is treated as healthy baseline."""
    return str(e.get("severity", "info")).lower() in ("warning", "error", "critical") or (
        (_num(e.get("value")) is not None and (_num(e.get("baseline")) or 0) > 0
         and (_num(e["value"]) / _num(e["baseline"])) >= 1.6)
    )


def anomaly_score(e: Dict[str, Any]) -> Tuple[float, Optional[str]]:
    """0..1 anomaly score with a human-readable reason."""
    sev = _sev(e)
    val, base = _num(e.get("value")), _num(e.get("baseline"))
    if val is not None and base is not None and base > 0:
        ratio = val / base
        # 1x -> 0.0, 5x or more -> 1.0 (log-ish, gentle at low ratios)
        dev = max(0.0, min(1.0, (ratio - 1.0) / 4.0)) if base > 0 else 0.0
        score = round(0.6 * dev + 0.4 * sev, 3)
        reason = f"metric {val:g}{e.get('unit') or ''} is {ratio:.1f}x baseline {base:g}"
        return score, reason
    return round(sev, 3), None


# ------------------------------------------------------------------ stage 1+2


def normalise(raw_events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for i, e in enumerate(raw_events):
        svc = str(e.get("service") or "unknown-service").strip()
        if svc not in topo.SERVICES:
            # unknown service -> keep, but mark it so topology rules stay honest
            svc_key = svc
        else:
            svc_key = svc
        score, reason = anomaly_score(e)
        patterns = classify_pattern(str(e.get("message", "")))
        out.append(
            {
                "id": f"E{i + 1:04d}",
                "ts": _dt(e.get("ts")),
                "ts_iso": _dt(e.get("ts")).isoformat(),
                "source": e.get("source") or "unknown",
                "service": svc_key,
                "known_service": svc_key in topo.SERVICES,
                "type": e.get("type") or "log",
                "severity": str(e.get("severity") or "info").lower(),
                "message": str(e.get("message") or "")[:400],
                "value": _num(e.get("value")),
                "baseline": _num(e.get("baseline")),
                "unit": e.get("unit") or "",
                "trace_id": e.get("trace_id") or None,
                "anomaly": score,
                "anomaly_reason": reason,
                "patterns": patterns,
                "noise": not is_signal(e),
            }
        )
    out.sort(key=lambda x: x["ts"])
    return out


# ------------------------------------------------------------------ stage 3: clustering

class _UF:
    def __init__(self, ids: List[str]):
        self.p = {i: i for i in ids}

    def find(self, a: str) -> str:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def _related(sa: str, sb: str) -> Tuple[bool, float]:
    """Topology relationship strength between two services."""
    if sa == sb:
        return True, 1.0
    if sa not in topo.SERVICES or sb not in topo.SERVICES:
        return False, 0.0
    if sb in topo.blast_radius(sa) or sa in topo.blast_radius(sb):
        return True, 0.8
    # shared dependency (siblings)
    deps_a, deps_b = set(topo.SERVICES[sa].depends_on), set(topo.SERVICES[sb].depends_on)
    if deps_a & deps_b:
        return True, 0.45
    return False, 0.0


def correlation_strength(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    dt_min = abs((a["ts"] - b["ts"]).total_seconds()) / 60.0
    s_time = max(0.0, 1.0 - dt_min / CORRELATION_WINDOW_MIN)
    _rel, s_topo = _related(a["service"], b["service"])
    s_trace = 1.0 if (a["trace_id"] and a["trace_id"] == b["trace_id"]) else 0.0
    shared = set(a["patterns"]) & set(b["patterns"])
    s_pat = 1.0 if shared else 0.0
    return round(W_TIME * s_time + W_TOPO * s_topo + W_TRACE * s_trace + W_PATTERN * s_pat, 3)


def cluster(events: List[Dict[str, Any]], min_strength: float = 0.34) -> List[Dict[str, Any]]:
    uf = _UF([e["id"] for e in events])
    links = []
    seen_dt: Dict[str, datetime] = {}
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            a, b = events[i], events[j]
            gap = abs((a["ts"] - b["ts"]).total_seconds()) / 60.0
            if gap > CORRELATION_WINDOW_MIN:
                continue
            s = correlation_strength(a, b)
            # temporal proximity alone is never enough to merge two services:
            # require at least one semantic signal (same service, topology link,
            # shared trace or shared failure pattern).
            if a["noise"] and b["noise"]:
                continue
            if a["service"] != b["service"]:
                _rel, s_topo = _related(a["service"], b["service"])
                shared_pat = bool(set(a["patterns"]) & set(b["patterns"]))
                same_trace = bool(a["trace_id"] and a["trace_id"] == b["trace_id"])
                strong = s_topo >= 0.8  # direct dependency or shared blast radius
                sibling = s_topo == 0.45  # share a dependency - weaker evidence
                serious = max(_sev(a), _sev(b)) >= 0.75  # at least one error/critical
                semantic = strong or same_trace or (sibling and shared_pat and serious)
                if not semantic:
                    continue
            if s >= min_strength:
                uf.union(a["id"], b["id"])
                links.append({"a": a["id"], "b": b["id"], "strength": s, "gap_min": round(gap, 2)})

    groups: Dict[str, List[Dict[str, Any]]] = {}
    for e in events:
        groups.setdefault(uf.find(e["id"]), []).append(e)

    clusters = []
    for k, (_, members) in enumerate(sorted(groups.items(), key=lambda kv: min(x["ts"] for x in kv[1]))):
        members.sort(key=lambda x: x["ts"])
        ids = {m["id"] for m in members}
        cid = f"INC-{100 + k}"
        clusters.append(
            {
                "id": cid,
                "events": members,
                "event_ids": [m["id"] for m in members],
                "services": sorted({m["service"] for m in members}),
                "sources": sorted({m["source"] for m in members}),
                "start": members[0]["ts"],
                "end": members[-1]["ts"],
                "links": [l for l in links if l["a"] in ids and l["b"] in ids],
            }
        )
    # Merge clusters that later turn out to share a root candidate (topology-linked)
    return clusters


# ------------------------------------------------------------------ stage 3b: noise suppression


def _is_self_contained_cluster(members: List[Dict[str, Any]]) -> bool:
    """True when a cluster never touches a critical path, so it is noise."""
    critical = [m for m in members if topo.SERVICES.get(m["service"], None) and topo.SERVICES[m["service"]].criticality >= 4]
    return len({m["service"] for m in critical}) < 2


def summarise_noise(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "id": "NOISE",
        "event_ids": [m["id"] for m in members],
        "event_count": len(members),
        "services": sorted({m["service"] for m in members}),
        "sources": sorted({m["source"] for m in members}),
        "reason": "Isolated low-severity signals with no topology link to a critical-path incident "
        "and no shared trace or failure pattern - suppressed to prevent alert fatigue.",
        "headline": max(members, key=lambda m: _sev(m))["message"][:160],
        "events": [serialise_event(m) for m in members],
    }


# ------------------------------------------------------------------ stage 4: root cause


def rank_root_causes(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    members = c["events"]
    t0, t1 = c["start"], c["end"]
    span = max(1.0, (t1 - t0).total_seconds())
    freq: Dict[str, int] = {}
    for m in members:
        freq[m["service"]] = freq.get(m["service"], 0) + 1

    candidates = []
    for svc, n in freq.items():
        evs = [m for m in members if m["service"] == svc]
        if svc not in topo.SERVICES:
            continue
        # how much of the incident does this service explain downstream?
        radius = set(topo.blast_radius(svc))
        explained = [s for s in freq if s == svc or s in radius]
        covers = sum(freq[s] for s in explained) / max(1, len(members))

        earliest = min(e["ts"] for e in evs)
        earliness = 1.0 - ((earliest - t0).total_seconds() / span)  # first to fire ~1.0
        sev = sum(_sev(e) for e in evs) / len(evs)
        anomaly = max(e["anomaly"] for e in evs)
        # topology fitness: a root should explain many *other* services
        topo_fit = min(1.0, len([s for s in explained if s != svc]) / 3.0)
        # amplification: how far the fault travelled (depends on being upstream)
        amp = min(1.0, len(radius) / 6.0)
        # metric-carrying root signals beat pure log noise
        metric_bonus = 0.08 if any(e["type"] == "metric" and e["anomaly"] > 0.5 for e in evs) else 0.0
        # penalise services that only appear late and affect nobody
        score = (
            RC_EARLINESS * earliness
            + RC_SEVERITY * sev
            + RC_TOPOLOGY * topo_fit
            + RC_ANOMALY * anomaly
            + RC_AMPLIFICATION * amp
            + metric_bonus
        )
        # weak-evidence penalty: a root cause must show repeated or metric-backed
        # evidence, not a single stray warning at the top of the graph
        if n < 3:
            score -= 0.10 * (3 - n) / 2.0
        # upstream-most tie-break: fewer/no dependents above it in this cluster
        upstream = 0
        for other in freq:
            if other != svc and other in topo.SERVICES and svc in topo.blast_radius(other):
                upstream += 1
        score -= 0.05 * upstream
        candidates.append(
            {
                "service": svc,
                "name": topo.SERVICES[svc].name,
                "kind": topo.SERVICES[svc].kind,
                "score": round(max(0.0, min(1.0, score)), 3),
                "events": n,
                "covers_pct": round(covers * 100, 1),
                "earliest": earliest.isoformat(),
                "earliness": round(earliness, 3),
                "severity": round(sev, 3),
                "anomaly": round(anomaly, 3),
                "topology_fit": round(topo_fit, 3),
                "amplification": round(amp, 3),
                "explains": sorted([s for s in explained if s != svc]),
                "signals": [
                    {"event": e["id"], "message": e["message"], "value": e["value"], "unit": e["unit"], "ts": e["ts_iso"], "anomaly_reason": e["anomaly_reason"]}
                    for e in sorted(evs, key=lambda x: -x["anomaly"])[:3]
                ],
            }
        )

    candidates.sort(key=lambda c: (-c["score"], c["earliest"]))
    for i, cand in enumerate(candidates):
        cand["rank"] = i + 1
    return candidates


def explain_chain(root: str, affected: Iterable[str]) -> List[Dict[str, Any]]:
    """Causal propagation path from root to each affected service."""
    chain = []
    for a in affected:
        path = topo.path_from_root(root, a)
        if path:
            chain.append({"to": a, "path": path, "hops": len(path) - 1})
    return chain


# ------------------------------------------------------------------ stage 5: impact


def impact_analysis(c: Dict[str, Any], root: str) -> Dict[str, Any]:
    radius = topo.blast_radius(root)
    observed_all = [s for s in c["services"] if s in topo.SERVICES]
    # "affected" = fired a real signal (warning+) inside the incident window
    observed = sorted({e["service"] for e in c["events"] if not e["noise"] and e["service"] in topo.SERVICES})
    affected = sorted(set(radius) | {root})
    coincidental = sorted(set(observed_all) - set(affected))
    scored = []
    for s in affected:
        svc = topo.SERVICES[s]
        involved = s in observed
        n_ev = sum(1 for e in c["events"] if e["service"] == s)
        # 70 pts from business criticality + up to 30 pts from how loudly it failed
        score = 70.0 * (svc.criticality / 5.0) + (min(30.0, n_ev * 2.5) if involved else 0.0)
        scored.append(
            {
                "service": s,
                "name": svc.name,
                "tier": svc.tier,
                "criticality": svc.criticality,
                "observed_events": n_ev,
                "directly_observed": involved,
                "impact_score": round(min(100.0, score), 1),
                "user_facing": svc.tier in ("edge", "application"),
            }
        )
    scored.sort(key=lambda x: -x["impact_score"])

    users = topo.users_impacted(affected)
    # failed-transaction estimate - fully explainable:
    #   ops/min = users x 2.5 transactions/day / 1440
    #   failed  = ops/min x duration x observed failure rate
    duration_min = max(1.0, (c["end"] - c["start"]).total_seconds() / 60.0)
    rates = [
        _num(e["value"]) or 0
        for e in c["events"]
        if e["unit"] == "%" and ("error" in e["message"].lower() or "failure" in e["message"].lower())
    ]
    failure_rate = min(max(rates or [6.0]), 40.0) / 100.0
    ops_per_min = users * 2.5 / 1440
    lost_ops = int(round(ops_per_min * duration_min * failure_rate))
    loss = round(lost_ops * 42.0, 0)  # avg order value proxy, Rs 42
    formula = (
        f"{users:,} users x 2.5 txn/day ÷ 1440 = {ops_per_min:.0f} ops/min; "
        f"x {duration_min:.0f} min x {failure_rate*100:.0f}% failure rate = {lost_ops:,} failed ops"
    )

    bl = [
        {"level": "Users", "detail": f"~{users:,} users on customer-facing surfaces exposed"},
        {"level": "Business", "detail": f"~{lost_ops:,} payment operations at risk over {duration_min:.0f} min"},
        {"level": "Revenue", "detail": f"estimated exposure ₹{loss:,.0f} (proxy ₹42/op)"},
        {"level": "Reputation", "detail": f"{len([s for s in affected if topo.SERVICES[s].tier in ('edge','application')])} customer-facing services degraded"},
    ]
    return {
        "affected_services": scored,
        "coincidental_services": [
            {"service": s, "name": topo.SERVICES[s].name,
             "reason": "fired inside the window but has no dependency path from the root cause - treated as coincidence, not impact"}
            for s in coincidental
        ],
        "affected_count": len(scored),
        "users_exposed": users,
        "failed_operations_estimate": lost_ops,
        "revenue_exposure_inr": loss,
        "estimate_formula": formula,
        "duration_minutes": round(duration_min, 1),
        "blast_radius": radius,
        "business_lines": bl,
    }


# ------------------------------------------------------------------ stage 6: recommendations


def recommendations(root: str, root_events: List[Dict[str, Any]], c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic runbook selection: the root cause's playbook, widened to the
    first hop when the root cause's failure mode shows up downstream."""
    msgs = " ".join(e["message"].lower() for e in root_events)
    plan: List[tuple[str, Dict[str, str]]] = []  # (owning service, playbook entry)

    if "no space left" in msgs or "disk" in msgs or "iowait" in msgs:
        plan += [("db-host", p) for p in RUNBOOKS["db-host"]]
        plan += [("db-proxy", p) for p in RUNBOOKS["db-proxy"][:2]]
    elif "pool" in msgs or "connection slots" in msgs:
        plan += [("db-proxy", p) for p in RUNBOOKS["db-proxy"]]
    else:
        plan += [(root, p) for p in RUNBOOKS.get(root, RUNBOOKS["generic"])]

    reasons = {
        "db-host": "Primary fix: this is the ranked root cause - its metric deviation began the incident.",
        "db-proxy": "Secondary fix: the root cause surfaced here as connection-pool exhaustion, which is what took the databases and APIs down.",
        root: "Primary fix: targeted at the ranked root cause.",
    }

    out = []
    for svc, p in plan:
        i = len(out) + 1
        out.append(
            {
                "step": i,
                "phase": "mitigate" if i <= 2 else "stabilise" if i <= 3 else "prevent",
                "action": p["action"],
                "detail": p["detail"],
                "effort": p["effort"],
                "eta": p["eta"],
                "risk": p["risk"],
                "target": svc,
                "why": reasons.get(svc, f"Applies to {topo.SERVICES.get(svc, svc).name if svc in topo.SERVICES else svc}."),
            }
        )
    for p in RUNBOOKS["generic"]:
        out.append(
            {
                "step": len(out) + 1,
                "phase": "coordinate",
                "action": p["action"],
                "detail": p["detail"],
                "effort": p["effort"],
                "eta": p["eta"],
                "risk": p["risk"],
                "target": "incident",
                "why": "Reduces alert fatigue and gives responders one shared picture while the root cause is being fixed.",
            }
        )
    return out


# ------------------------------------------------------------------ narrative


def narrative(c: Dict[str, Any], root: Dict[str, Any], impact: Dict[str, Any], cands: List[Dict[str, Any]]) -> str:
    svc = topo.SERVICES[root["service"]]
    second = cands[1] if len(cands) > 1 else None
    t_start = c["start"].strftime("%H:%M:%S")
    t_end = c["end"].strftime("%H:%M:%S")
    lines = [
        f"Between {t_start} and {t_end} UTC, {len(c['events'])} events from {len(c['sources'])} sources "
        f"({', '.join(c['sources'])}) formed one incident affecting {impact['affected_count']} services.",
        f"The most likely root cause is **{svc.name}** (`{root['service']}`) - it fired first "
        f"({root['earliest'][11:19]} UTC), carries the strongest anomaly "
        f"({root['anomaly']:.2f}) and its dependency position explains "
        f"{root['covers_pct']}% of all events in the cluster.",
    ]
    if root["signals"]:
        s = root["signals"][0]
        lines.append(f"Primary evidence: \"{s['message']}\" ({s['anomaly_reason'] or 'severity-based signal'}).")
    chain = explain_chain(root["service"], [s["service"] for s in impact["affected_services"]])
    hops = [ch for ch in chain if ch["hops"] > 0]
    if hops:
        # show the two deepest propagation paths - the clearest evidence of spread
        hops.sort(key=lambda h: -h["hops"])
        shown = []
        for h in hops[:2]:
            shown.append(" → ".join(topo.SERVICES[n].name for n in h["path"]))
        lines.append(
            "Propagation follows the dependency graph: " + "; ".join(shown)
            + f". {len(hops)} services lie downstream of the root cause."
        )
    if second:
        lines.append(
            f"Rejected alternative: {second['name']} scored {second['score']:.2f} vs {root['score']:.2f} - it looks downstream "
            f"(its first event is {second['earliest'][11:19]}) and only explains {second['covers_pct']}% of the incident."
        )
    lines.append(
        f"Impact: ~{impact['users_exposed']:,} exposed users, {impact['failed_operations_estimate']:,} payment operations at risk, "
        f"estimated exposure ₹{impact['revenue_exposure_inr']:,.0f}."
    )
    return " ".join(lines)


# ------------------------------------------------------------------ serialisation


def serialise_event(e: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-safe event: datetime `ts` becomes an ISO string the UI can parse."""
    out = {k: v for k, v in e.items() if k != "ts"}
    out["ts"] = e["ts_iso"]
    return out


# ------------------------------------------------------------------ orchestrator


def analyse(raw_events: List[Dict[str, Any]], min_cluster_size: int = 3) -> Dict[str, Any]:
    events = normalise(raw_events)
    if not events:
        return {"events": [], "incidents": [], "summary": {"events": 0, "incidents": 0}}

    clusters = cluster(events)
    incidents = []
    noise_pool: List[Dict[str, Any]] = []
    for c in clusters:
        # Correlate on signals only: healthy baseline events are context, not incident facts.
        signals = [e for e in c["events"] if not e["noise"]]
        dropped = [e for e in c["events"] if e["noise"]]
        if len(signals) < min_cluster_size:
            noise_pool.extend(signals)
            noise_pool.extend(dropped)
            continue
        c = {**c, "events": signals, "services": sorted({e["service"] for e in signals}),
             "sources": sorted({e["source"] for e in signals}), "start": signals[0]["ts"], "end": signals[-1]["ts"],
             "baseline_context": len(dropped)}
        cands = rank_root_causes(c)
        top = cands[0] if cands else None
        is_primary = (
            len(c["services"]) >= 3
            and top is not None
            and top["score"] >= 0.55
            and len(topo.blast_radius(top["service"])) >= 2
            and not _is_self_contained_cluster(c["events"])
        )
        if not is_primary:
            noise_pool.extend(c["events"])
            noise_pool.extend(e for e in dropped if e not in noise_pool)
            continue
        root = top
        impact = impact_analysis(c, root["service"])
        recs = recommendations(root["service"], [e for e in c["events"] if e["service"] == root["service"]], c)
        score = root["score"]
        severity = "critical" if score >= 0.62 or impact["users_exposed"] >= 300_000 else "high" if score >= 0.5 else "medium"
        incidents.append(
            {
                "id": c["id"],
                "title": f"{topo.SERVICES[root['service']].name} degradation propagating to {len(impact['affected_services'])} services",
                "severity": severity,
                "confidence": round(min(0.99, 0.45 + 0.5 * score), 3),
                "status": "investigating",
                "start": c["start"].isoformat(),
                "end": c["end"].isoformat(),
                "duration_minutes": round((c["end"] - c["start"]).total_seconds() / 60, 1),
                "event_count": len(c["events"]),
                "sources": c["sources"],
                "services": c["services"],
                "root_cause": root,
                "candidates": cands[:4],
                "impact": impact,
                "chain": explain_chain(root["service"], [a["service"] for a in impact["affected_services"]]),
                "timeline": build_timeline(c, root),
                "recommendations": recs,
                "recovery_playbook": RECOVERY_PLAYBOOK,
                "narrative": "",
                "events": [serialise_event(e) for e in c["events"]],
                "links": c["links"],
            }
        )
        incidents[-1]["narrative"] = narrative(c, root, impact, cands)

    incidents.sort(key=lambda i: (-{"critical": 3, "high": 2, "medium": 1}.get(i["severity"], 0), i["start"]))
    correlated_events = sum(i["event_count"] for i in incidents)
    noise_groups = [summarise_noise(noise_pool)] if noise_pool else []
    suppressed = len(noise_pool)
    return {
        "events": [serialise_event(e) for e in events],
        "incidents": incidents,
        "suppressed": noise_groups,
        "summary": {
            "events": len(events),
            "incidents": len(incidents),
            "correlated_events": correlated_events,
            "noise_events": suppressed,
            "noise_groups": len(noise_groups),
            "critical": sum(1 for i in incidents if i["severity"] == "critical"),
            "services_touched": len({e["service"] for e in events}),
            "sources": sorted({e["source"] for e in events}),
            "time_range": {"start": events[0]["ts_iso"], "end": events[-1]["ts_iso"]},
        },
    }


def build_timeline(c: Dict[str, Any], root: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ordered incident story: first the root signal, then propagation per service."""
    first_seen: Dict[str, datetime] = {}
    for e in c["events"]:
        first_seen.setdefault(e["service"], e["ts"])
    t0 = c["start"]
    steps = []
    for i, (svc, ts) in enumerate(sorted(first_seen.items(), key=lambda kv: kv[1]), 1):
        evs = [e for e in c["events"] if e["service"] == svc]
        path = topo.path_from_root(root["service"], svc)
        steps.append(
            {
                "step": i,
                "ts": ts.isoformat(),
                "offset_min": round((ts - t0).total_seconds() / 60, 1),
                "service": svc,
                "service_name": topo.SERVICES[svc].name if svc in topo.SERVICES else svc,
                "role": "ROOT CAUSE" if svc == root["service"] else ("propagated" if path else "coincidental"),
                "hops_from_root": max(0, len(path) - 1) if path else None,
                "events": len(evs),
                "peak_severity": max((e["severity"] for e in evs), key=lambda s: SEV_WEIGHT.get(s, 0)),
                "headline": max(evs, key=lambda e: e["anomaly"])["message"][:180],
            }
        )
    return steps
