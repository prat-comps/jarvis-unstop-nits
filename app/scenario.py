"""
J.A.R.V.I.S. - Scenario simulator + log-file normaliser.

Produces a deterministic stream of events from three different source types
(metrics/APM, application logs, alert manager) so the correlation engine can be
demonstrated end-to-end without any real infrastructure:

  * `simulate()`       -> simulated live data burst
  * `parse_log_file()` -> normalises an uploaded CSV / JSON-lines / text log

Ground truth of the built-in incident:
  db-host disk IO saturation  ->  db-proxy connection pool exhaustion
    ->  ledger-db + user-db slow  ->  payment-api 5xx / timeouts
      ->  checkout-ui errors, mobile login failures, failed payments
"""

from __future__ import annotations

import csv
import io
import json
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

BASE = datetime(2025, 3, 14, 10, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------- helpers


def _ev(
    ts: datetime,
    source: str,
    service: str,
    etype: str,
    severity: str,
    message: str,
    value: float | None = None,
    baseline: float | None = None,
    unit: str = "",
    trace_id: str | None = None,
    ground_truth_root: bool = False,
) -> Dict[str, Any]:
    return {
        "ts": ts.isoformat(),
        "source": source,
        "service": service,
        "type": etype,
        "severity": severity,
        "message": message,
        "value": value,
        "baseline": baseline,
        "unit": unit,
        "trace_id": trace_id,
        "_root": ground_truth_root,  # kept only for evaluation, never used by the engine
    }


# ---------------------------------------------------------------- simulator


def simulate(seed: int = 7, include_noise: bool = True) -> Dict[str, Any]:
    rng = random.Random(seed)
    ev: List[Dict[str, Any]] = []

    def t(mins: float, secs: float = 0) -> datetime:
        return BASE + timedelta(minutes=mins, seconds=secs)

    # ---- 09:56-10:00  healthy warm-up (baseline noise, low severity)
    for i in range(18):
        svc = rng.choice(["payment-api", "auth", "checkout-ui", "ledger-db", "notification"])
        ev.append(
            _ev(
                t(-4 + i * 0.2, rng.randint(0, 59)),
                "prometheus",
                svc,
                "metric",
                "info",
                f"{svc} p99 latency within SLO",
                round(rng.uniform(110, 240), 1),
                200.0,
                "ms",
            )
        )

    # ---- 10:02  ROOT CAUSE: database host disk IO saturation
    for i, v in enumerate([71, 84, 93, 97, 99, 98, 96]):
        ev.append(
            _ev(
                t(2, i * 45),
                "prometheus",
                "db-host",
                "metric",
                "critical" if v > 95 else "warning",
                "disk io utilisation on db-host/data-volume critical",
                float(v),
                55.0,
                "%",
                ground_truth_root=True,
            )
        )
    ev.append(
        _ev(
            t(2, 30),
            "log",
            "db-host",
            "log",
            "error",
            "postgres: could not write to file pg_wal/0000000100000000000000A1: No space left on device (io stall)",
            ground_truth_root=True,
        )
    )
    for i, v in enumerate([0.42, 0.61, 0.78, 0.91, 0.87]):
        ev.append(
            _ev(
                t(2.5, i * 50),
                "prometheus",
                "db-host",
                "metric",
                "warning",
                "iowait percentage on db-host elevated",
                round(v * 100, 1),
                18.0,
                "%",
                ground_truth_root=True,
            )
        )

    # ---- 10:04  connection pool exhaustion at the DB proxy
    for i, v in enumerate([88, 96, 100, 100, 100]):
        ev.append(
            _ev(
                t(4, i * 40),
                "prometheus",
                "db-proxy",
                "metric",
                "critical" if v >= 99 else "warning",
                "pgbouncer client connection pool utilisation exhausted",
                float(v),
                60.0,
                "%",
            )
        )
    for i in range(4):
        ev.append(
            _ev(
                t(4.2, i * 55),
                "log",
                "db-proxy",
                "log",
                "error",
                "pool queue full: 214 clients waiting, server_login_retry exceeded",
                ground_truth_root=False,
            )
        )

    # ---- 10:06  data layer latency
    for svc, tn in (("ledger-db", 1400), ("user-db", 1150)):
        for i, v in enumerate([680, 1240, 2100, 2650, 2980, 2410]):
            ev.append(
                _ev(
                    t(6 + i * 0.6, rng.randint(0, 59)),
                    "prometheus",
                    svc,
                    "metric",
                    "critical" if v > 2000 else "warning",
                    f"{svc} query p99 latency degraded",
                    float(v + rng.randint(-60, 60)),
                    float(tn * 0.15),
                    "ms",
                )
            )
        ev.append(
            _ev(
                t(6.5, 12),
                "log",
                svc,
                "log",
                "error",
                f"{svc}: FATAL: remaining connection slots are reserved / statement timeout after 30s",
            )
        )

    # ---- 10:07  payment api failures (5xx, timeouts) - shared trace ids
    for i in range(11):
        tid = f"tr-9f{i:03d}"
        ev.append(
            _ev(
                t(7 + i * 0.35, rng.randint(0, 59)),
                "apm",
                "payment-api",
                "trace",
                "critical" if i % 3 else "error",
                "POST /v1/payments -> 503 upstream ledger timeout",
                round(rng.uniform(4200, 9100), 0),
                280.0,
                "ms",
                trace_id=tid,
            )
        )
    for i, v in enumerate([2.1, 6.4, 11.8, 17.2, 21.5, 19.3]):
        ev.append(
            _ev(
                t(7.2 + i * 0.6, rng.randint(0, 59)),
                "prometheus",
                "payment-api",
                "metric",
                "critical" if v > 10 else "warning",
                "payment-api 5xx error rate above threshold",
                round(v, 1),
                0.4,
                "%",
            )
        )
    ev.append(
        _ev(
            t(7.4, 5),
            "alertmanager",
            "payment-api",
            "alert",
            "critical",
            "HighErrorRate: payment-api 5xx > 10% for 5m",
        )
    )

    # ---- 10:08  auth / login failures (same underlying DB)
    for i, v in enumerate([3.9, 9.2, 15.7, 22.4, 26.1, 18.6]):
        ev.append(
            _ev(
                t(8 + i * 0.5, rng.randint(0, 59)),
                "prometheus",
                "auth",
                "metric",
                "critical" if v > 12 else "warning",
                "auth login failure rate elevated",
                round(v, 1),
                0.8,
                "%",
            )
        )
    for i in range(8):
        ev.append(
            _ev(
                t(8.1 + i * 0.4, rng.randint(0, 59)),
                "log",
                "auth",
                "log",
                "error",
                "Login failed: session write timed out (session-store unavailable) user=u_%04d" % (4100 + i),
            )
        )
    ev.append(
        _ev(
            t(8.3, 40),
            "alertmanager",
            "auth",
            "alert",
            "critical",
            "LoginFailureSpike: auth failure rate > 20% for 5m",
        )
    )

    # ---- 10:09  PSP connector + front-ends
    for i, v in enumerate([4.5, 12.8, 24.0, 31.5]):
        ev.append(
            _ev(
                t(9 + i * 0.5, rng.randint(0, 59)),
                "prometheus",
                "psp-connector",
                "metric",
                "critical" if v > 20 else "warning",
                "psp-connector vendor call timeout rate rising",
                round(v, 1),
                1.1,
                "%",
            )
        )
    for i in range(6):
        ev.append(
            _ev(
                t(9.2 + i * 0.4, rng.randint(0, 59)),
                "log",
                "checkout-ui",
                "log",
                "error",
                "checkout: payment step failed, showing 'Try again' to user (session=web_%03d)" % i,
            )
        )
    ev.append(
        _ev(
            t(9.4, 10),
            "apm",
            "checkout-ui",
            "trace",
            "error",
            "GET /checkout/confirm -> 502 from payment-api",
            round(rng.uniform(5000, 12000), 0),
            420.0,
            "ms",
        )
    )
    ev.append(
        _ev(
            t(9.6, 30),
            "alertmanager",
            "mobile-app",
            "alert",
            "error",
            "MobileAppLoginCrashRate: elevated relogin loop detected",
        )
    )

    # ---- unrelated noise, deliberately plausible (tests precision)
    if include_noise:
        ev.append(
            _ev(
                t(3.1, 11),
                "alertmanager",
                "notification",
                "alert",
                "warning",
                "QueueBacklog: notification topic lag 4.2k messages",
                4200.0,
                500.0,
                "msgs",
            )
        )
        ev.append(
            _ev(
                t(5.0, 44),
                "log",
                "notification",
                "log",
                "warning",
                "email provider returned 429, retrying with backoff",
            )
        )
        ev.append(
            _ev(
                t(5.6, 12),
                "prometheus",
                "waf",
                "metric",
                "warning",
                "waf blocked-request rate spike (bot traffic from 3 ASNs)",
                8.4,
                1.2,
                "%",
            )
        )
        ev.append(
            _ev(
                t(6.1, 33),
                "log",
                "vendor-psp",
                "log",
                "warning",
                "vendor webhook signature rotation notice received",
            )
        )

    ev.sort(key=lambda e: e["ts"])
    return {
        "scenario": "Digital payment platform partial outage",
        "window": {"start": BASE.isoformat(), "end": (BASE + timedelta(minutes=12)).isoformat()},
        "events": ev,
    }


# ---------------------------------------------------------------- file parsing

_LEVELS = {"fatal": "critical", "crit": "critical", "critical": "critical", "error": "error",
           "err": "error", "warn": "warning", "warning": "warning", "info": "info", "debug": "info"}
_SEV_HINT = [
    (re.compile(r"\b(fatal|panic|out of memory|no space left|crash)\b", re.I), "critical"),
    (re.compile(r"\b(connection refused|timed? ?out|exhaust|unavailable|failed)\b", re.I), "error"),
    (re.compile(r"\b(slow|degrad|retry|lag|spike|elevated)\b", re.I), "warning"),
]

_TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
]


def _parse_ts(raw: str) -> str | None:
    raw = (raw or "").strip().replace("Z", "")
    if not raw:
        return None
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(raw[:26], fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def _guess_severity(level: str | None, message: str) -> str:
    if level and level.strip().lower() in _LEVELS:
        return _LEVELS[level.strip().lower()]
    for rx, sev in _SEV_HINT:
        if rx.search(message):
            return sev
    return "info"


def _normalise_record(rec: Dict[str, Any], idx: int, fmt_hint: str = "file") -> Dict[str, Any] | None:
    low = {str(k).lower().strip(): v for k, v in rec.items()}
    ts = _parse_ts(str(low.get("timestamp") or low.get("time") or low.get("ts") or low.get("@timestamp") or ""))
    message = str(low.get("message") or low.get("msg") or low.get("log") or low.get("event") or "").strip()
    if not message:
        return None
    level = str(low.get("level") or low.get("severity") or low.get("loglevel") or "")
    service = str(
        low.get("service") or low.get("service_name") or low.get("app") or low.get("component")
        or low.get("host") or low.get("instance") or "unknown-service"
    ).strip()
    if service not in _known_services():
        # try to find a known service name inside the message
        for s in _known_services():
            if re.search(rf"\b{re.escape(s)}\b", message, re.I):
                service = s
                break
    value = low.get("value") or low.get("latency_ms") or low.get("error_rate") or low.get("metric_value")
    try:
        value = float(value) if value is not None and str(value).strip() != "" else None
    except (TypeError, ValueError):
        value = None
    return {
        "ts": ts or datetime.now(timezone.utc).isoformat(),
        "source": fmt_hint,
        "service": service,
        "type": "log" if value is None else "metric",
        "severity": _guess_severity(level, message),
        "message": message[:400],
        "value": value,
        "baseline": None,
        "unit": "",
        "trace_id": str(low.get("trace_id") or low.get("traceid") or "") or None,
    }


def _known_services() -> List[str]:
    from .topology import SERVICES

    return list(SERVICES.keys())


_PLAIN_RX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
    r"(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\s+"
    r"(?P<service>[\w.\-]+)\s+(?:\[[^\]]*\]\s+)?(?P<msg>.*)$",
    re.I,
)


def parse_log_file(filename: str, raw: bytes) -> Dict[str, Any]:
    """Accept CSV, JSON-lines, a JSON array, or plain text logs."""
    text = raw.decode("utf-8", errors="replace")
    name = (filename or "").lower()
    events: List[Dict[str, Any]] = []
    fmt = "upload"

    if name.endswith(".csv") or (text.lstrip().startswith(("timestamp,", "time,", "ts,"))):
        fmt = "csv"
        for i, rec in enumerate(csv.DictReader(io.StringIO(text))):
            e = _normalise_record(rec, i, "csv")
            if e:
                events.append(e)
    else:
        stripped = text.lstrip()
        if stripped.startswith("["):
            fmt = "json"
            try:
                for i, rec in enumerate(json.loads(stripped)):
                    e = _normalise_record(rec, i, "json")
                    if e:
                        events.append(e)
            except json.JSONDecodeError:
                pass
        if not events:
            # JSON-lines
            parsed = 0
            for i, line in enumerate(text.splitlines()):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{"):
                    try:
                        e = _normalise_record(json.loads(line), i, "jsonl")
                        if e:
                            events.append(e)
                            parsed += 1
                            continue
                    except json.JSONDecodeError:
                        pass
                m = _PLAIN_RX.match(line)
                if m:
                    events.append(
                        {
                            "ts": _parse_ts(m.group("ts")) or datetime.now(timezone.utc).isoformat(),
                            "source": "text",
                            "service": m.group("service").split(".")[0],
                            "type": "log",
                            "severity": _guess_severity(m.group("level"), m.group("msg")),
                            "message": m.group("msg")[:400],
                            "value": None,
                            "baseline": None,
                            "unit": "",
                            "trace_id": None,
                        }
                    )
            if parsed:
                fmt = "jsonl"

    events.sort(key=lambda e: e["ts"])
    return {"format": fmt, "count": len(events), "events": events}
