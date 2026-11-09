# J.A.R.V.I.S.

**Justified Analysis, Reasoning & Visualization of Incident Systems**

A working prototype for Problem Statement 1 (Software Track) — an incident intelligence
platform that collects events from many sources, correlates them into a single incident,
identifies the most likely root cause, explains the impact, and recommends fixes.

> The problem statement's own scenario is implemented end to end: a digital payment platform
> where login failures, slow APIs and failed payments all trace back to **one** failing
> database host. J.A.R.V.I.S. finds that connection in under 200 ms and states why.

---

## Quick start

```bash
cd jarvis
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```


## What it does

| Stage | What happens |
|---|---|
| 1 · Ingest & normalise | Push API, deterministic stream simulator, or file upload (CSV / JSON / JSONL / text). All sources mapped to one canonical event. |
| 2 · Score | Per-event anomaly from metric deviation vs baseline + severity; failure patterns classified from the message. |
| 3 · Correlate | Union-Find over four weighted link rules (time 0.30 · topology 0.35 · trace 0.25 · pattern 0.10), guarded so time proximity alone can never merge two different services. |
| 4 · Root cause | Five-signal ranking (earliness, severity, topology fit, anomaly, amplification) with thin-evidence and upstream-dominance penalties. Alternatives are kept and justified. |
| 5 · Impact | Blast radius from the dependency graph, per-service impact scores, exposed users, and a revenue estimate whose formula is printed on screen. |
| 6 · Recommend | Runbook actions matched on root service + failure mode, tagged by phase with effort, ETA and risk, plus a recovery playbook. |

---

## Result on the built-in challenge scenario

| | |
|---|---|
| Events ingested | **103** from 4 sources (metrics, logs, APM traces, alert manager) |
| Alerts a responder would see without correlation | **12**, across 8 services |
| Incidents after correlation | **1** — INC-112, critical, 93.8% confidence |
| Root cause | **Database Host (VM)** — disk IO saturation, score **0.975 / 1.000** |
| Ground truth | matches exactly; true root cause ranks 1st of all candidates |
| Noise suppressed | **12** healthy/baseline events, listed with the reason |
| Impact | 8 services · ~420,000 users · 1,830 payment operations · ₹76,860 exposure |

Causal chain recovered: `db-host → db-proxy → ledger-db → payment-api → checkout-ui`, with
`auth` and `user-db` on parallel branches — 4 hops, reconstructed from timestamps and topology
alone.

---

## Dashboard

Seven linked views, all driven by the same incident object:

- **Overview** — root cause, confidence ring, evidence-grounded narrative, noise summary
- **Topology** — layered SVG dependency graph, blast radius, click any node to inspect its events
- **Timeline** — per-service swimlanes with one tick per event, plus a propagation table with hop distances
- **Root Cause** — full candidate ranking with every score component visible, and rejected alternatives explained
- **Impact** — affected services, business impact with the arithmetic shown, coincidence list kept separate
- **Recommendations** — phase-tagged action plan and recovery playbook
- **Events** — searchable, filterable raw stream showing the anomaly score behind every number

Demo controls: *Simulate live burst*, *Append burst*, *Upload logs*, *Download sample log*,
*Reset to scenario*, *Export report* (JSON).

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/state` | Everything the UI needs in one call |
| GET | `/api/incidents` | List of correlated incidents |
| GET | `/api/incidents/{id}` | Full incident (root causes, impact, timeline, recommendations) |
| GET | `/api/incidents/{id}/report` | Machine-readable incident report (export) |
| POST | `/api/ingest/events` | Push structured events |
| POST | `/api/ingest/simulate` | Generate the challenge burst (`?append=true` to extend) |
| POST | `/api/ingest/upload` | Upload a CSV / JSON / JSONL / text log file |
| GET | `/api/sample` | Download a sample CSV log |
| GET | `/api/health` | Liveness and counters |
| GET | `/docs` | Interactive OpenAPI documentation |


## Project layout

```
jarvis/
  app/
    main.py         FastAPI app — ingest, analyse, report, dashboard routes
    engine.py       six-stage engine: normalise, score, cluster, rank, impact, recommend
    topology.py     service registry, dependency graph, blast radius, BFS paths
    scenario.py     deterministic simulator + CSV/JSON/JSONL/text log parser
    static/
      index.html    the entire dashboard (inline CSS + JS + SVG)
  samples/
    jarvis_sample_events.csv
  docs/             architecture diagram and dashboard screenshots
  requirements.txt
```

---

