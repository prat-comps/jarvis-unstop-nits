"""J.A.R.V.I.S. - FastAPI application: ingest, correlate, report, dashboard."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import engine, scenario
from .topology import topology_payload

STATIC = Path(__file__).parent / "static"
STATE: dict = {"raw": [], "result": None, "label": "no data"}

app = FastAPI(title="J.A.R.V.I.S.", description="Justified Analysis, Reasoning & Visualization of Incident Systems", version="1.0.0")


# ------------------------------------------------------------------ models
class EventIn(BaseModel):
    ts: str
    service: str
    message: str
    severity: str = "info"
    source: str = "api"
    type: str = "log"
    value: float | None = None
    baseline: float | None = None
    unit: str = ""
    trace_id: str | None = None


class EventBatch(BaseModel):
    events: list[EventIn]
    label: str | None = None


# ------------------------------------------------------------------ lifecycle
@app.on_event("startup")
def _boot() -> None:
    """Seed with the deterministic challenge scenario so the dashboard is never empty."""
    data = scenario.simulate()
    STATE["raw"] = data["events"]
    STATE["result"] = engine.analyse(data["events"])
    STATE["label"] = "seeded: payment platform incident"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


# ------------------------------------------------------------------ ingest
@app.post("/api/ingest/events")
def ingest_events(batch: EventBatch) -> JSONResponse:
    events = [e.model_dump() for e in batch.events]
    STATE["raw"] = (STATE["raw"] + events)[-5000:]
    STATE["label"] = batch.label or "api stream"
    STATE["result"] = engine.analyse(STATE["raw"])
    return JSONResponse({"ok": True, "accepted": len(events), "summary": STATE["result"]["summary"]})


@app.post("/api/ingest/simulate")
def ingest_simulate(include_noise: bool = True, append: bool = False) -> JSONResponse:
    data = scenario.simulate(include_noise=include_noise)
    STATE["raw"] = (STATE["raw"] + data["events"])[-5000:] if append else data["events"]
    STATE["label"] = "simulated live stream"
    STATE["result"] = engine.analyse(STATE["raw"])
    return JSONResponse({"ok": True, "accepted": len(data["events"]), "summary": STATE["result"]["summary"]})


@app.post("/api/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)) -> JSONResponse:
    raw = await file.read()
    if len(raw) > 8_000_000:
        raise HTTPException(413, "file too large (max 8 MB)")
    parsed = scenario.parse_log_file(file.filename or "upload", raw)
    if not parsed["events"]:
        raise HTTPException(400, "no parseable events found - expected CSV, JSON/JSONL or text logs")
    STATE["raw"] = parsed["events"]
    STATE["label"] = f"upload: {file.filename} ({parsed['format']})"
    STATE["result"] = engine.analyse(STATE["raw"])
    return JSONResponse({"ok": True, "format": parsed["format"], "accepted": parsed["count"], "summary": STATE["result"]["summary"]})


# ------------------------------------------------------------------ read
@app.get("/api/state")
def get_state() -> JSONResponse:
    return JSONResponse(
        {
            "label": STATE["label"],
            "topology": topology_payload(),
            "result": STATE["result"],
            "events_total": len(STATE["raw"]),
        }
    )


@app.get("/api/incidents")
def get_incidents() -> JSONResponse:
    return JSONResponse(STATE["result"]["incidents"])


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str) -> JSONResponse:
    for inc in STATE["result"]["incidents"]:
        if inc["id"] == incident_id:
            return JSONResponse(inc)
    raise HTTPException(404, "incident not found")


@app.get("/api/incidents/{incident_id}/report")
def get_report(incident_id: str) -> JSONResponse:
    """Machine-readable incident report (the 'expected outcome' artefact)."""
    for inc in STATE["result"]["incidents"]:
        if inc["id"] == incident_id:
            return JSONResponse(
                {
                    "report_id": inc["id"],
                    "generated_at": inc["start"],
                    "title": inc["title"],
                    "severity": inc["severity"],
                    "confidence": inc["confidence"],
                    "summary": inc["narrative"],
                    "root_cause": {
                        "service": inc["root_cause"]["service"],
                        "name": inc["root_cause"]["name"],
                        "score": inc["root_cause"]["score"],
                        "evidence": inc["root_cause"]["signals"],
                    },
                    "alternatives": [
                        {"service": c["service"], "score": c["score"], "why_rejected": f"earliest event {c['earliest']}, covers {c['covers_pct']}%"}
                        for c in inc["candidates"][1:]
                    ],
                    "impact": inc["impact"],
                    "timeline": inc["timeline"],
                    "recommendations": inc["recommendations"],
                    "recovery_playbook": inc["recovery_playbook"],
                }
            )
    raise HTTPException(404, "incident not found")


@app.get("/api/sample")
def sample_log():
    """A messy CSV log in the shape real teams upload - for demoing the parser."""
    import csv
    import io

    from fastapi.responses import Response

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["timestamp", "level", "service", "message", "value"])
    rows = [
        ["2025-03-14 10:02:14", "ERROR", "db-host", "postgres: could not write to file pg_wal: No space left on device", ""],
        ["2025-03-14 10:02:41", "WARN", "db-host", "iowait percentage elevated on data volume", "88"],
        ["2025-03-14 10:04:02", "ERROR", "db-proxy", "pool queue full: 214 clients waiting", ""],
        ["2025-03-14 10:04:55", "ERROR", "db-proxy", "server_login_retry exceeded, connection refused", ""],
        ["2025-03-14 10:06:10", "WARN", "ledger-db", "query p99 latency degraded", "2100"],
        ["2025-03-14 10:06:38", "ERROR", "ledger-db", "FATAL: remaining connection slots are reserved", ""],
        ["2025-03-14 10:07:12", "ERROR", "payment-api", "POST /v1/payments -> 503 upstream ledger timeout", "7400"],
        ["2025-03-14 10:07:44", "CRITICAL", "payment-api", "payment 5xx error rate above threshold", "17.2"],
        ["2025-03-14 10:08:05", "ERROR", "auth", "Login failed: session write timed out (session-store unavailable)", ""],
        ["2025-03-14 10:08:33", "WARN", "auth", "login failure rate elevated", "22.4"],
        ["2025-03-14 10:09:20", "ERROR", "checkout-ui", "payment step failed, showing Try again to user", ""],
        ["2025-03-14 10:09:58", "WARN", "psp-connector", "psp-connector timeout rate rising", "24.0"],
        ["2025-03-14 10:03:10", "WARN", "notification", "email provider returned 429, retrying with backoff", ""],
        ["2025-03-14 10:05:44", "INFO", "waf", "blocked-request rate within normal range", "1.1"],
    ]
    w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=jarvis_sample_events.csv"})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "events": len(STATE["raw"]), "incidents": len(STATE["result"]["incidents"])}


app.mount("/static", StaticFiles(directory=STATIC), name="static")
