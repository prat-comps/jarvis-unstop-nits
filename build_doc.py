"""Generates the J.A.R.V.I.S. solution document (.docx) for Problem Statement 1."""

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x0B, 0x1B, 0x2E)
CYAN = RGBColor(0x0E, 0x74, 0x90)
TEAL = RGBColor(0x08, 0x91, 0xB2)
GREY = RGBColor(0x4A, 0x5A, 0x70)
RED = RGBColor(0xA3, 0x12, 0x25)
AMBER = RGBColor(0x92, 0x40, 0x0E)
BODY = RGBColor(0x1C, 0x24, 0x30)

D = Document()

# ---------------------------------------------------------------- page setup
sec = D.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(1.9)
sec.left_margin, sec.right_margin = Cm(2.2), Cm(2.2)

st = D.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
st.font.color.rgb = BODY
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.13


def shade(cell, hex_fill):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hex_fill)
    cell._tc.get_or_add_tcPr().append(el)


def cell_text(cell, text, bold=False, size=9.5, color=BODY, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    if align:
        p.alignment = align
    r = p.add_run(str(text))
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return p


import os
MEASURE = os.environ.get("JARVIS_MEASURE") == "1"


def h1(text, num=None):
    p = D.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    if num:
        r0 = p.add_run(f"{num}  ")
        r0.font.size = Pt(17)
        r0.font.bold = True
        r0.font.color.rgb = TEAL
    r = p.add_run(("⟦%s⟧" % num if MEASURE else "") + text)
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = NAVY
    # rule under heading
    pPr = p._p.get_or_add_pPr()
    bd = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single")
    bot.set(qn("w:sz"), "8")
    bot.set(qn("w:space"), "3")
    bot.set(qn("w:color"), "0E7490")
    bd.append(bot)
    pPr.append(bd)
    return p


def h2(text):
    p = D.add_paragraph()
    p.paragraph_format.space_before = Pt(11)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.size = Pt(12.5)
    r.font.bold = True
    r.font.color.rgb = CYAN
    return p


def h3(text):
    p = D.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = NAVY
    return p


def para(text, size=10.5, italic=False, color=BODY, after=6, before=0, align=None):
    p = D.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.italic = italic
    r.font.color.rgb = color
    return p


def rich(parts, size=10.5, after=6, before=0, style=None):
    """parts = list of (text, {bold, italic, mono, color})"""
    p = D.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    for text, opt in parts:
        r = p.add_run(text)
        r.font.size = Pt(opt.get("size", size))
        r.bold = opt.get("bold", False)
        r.italic = opt.get("italic", False)
        r.font.color.rgb = opt.get("color", BODY)
        if opt.get("mono"):
            r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    return p


def bullet(text, level=0, bold_lead=None):
    p = D.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(0.6 + 0.5 * level)
    p.paragraph_format.space_after = Pt(3)
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        r.font.size = Pt(10.5)
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    return p


def numbered(text, bold_lead=None):
    p = D.add_paragraph(style="List Number")
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(3)
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
        r.font.size = Pt(10.5)
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    return p


def code_block(lines, fill="0F1B2B"):
    """Monospace block. Uses explicit line breaks in a single paragraph so every
    renderer (Word, LibreOffice, HTML converters) keeps the line structure."""
    t = D.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0)
    shade(c, fill)
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    for i, ln in enumerate(lines):
        if i:
            p.add_run().add_break()
        r = p.add_run(ln.replace(" ", "\u00a0"))
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(0xC9, 0xE4, 0xF0)
    D.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def callout(title, text, accent="0E7490", fill="EAF6FA"):
    t = D.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0)
    shade(c, fill)
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title + "  ")
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string(accent)
    r2 = p.add_run(text)
    r2.font.size = Pt(10)
    D.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def table(headers, rows, widths=None, header_fill="0B1B2E", font=9.0, zebra="F2F6FA"):
    t = D.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, htxt in enumerate(headers):
        c = t.rows[0].cells[i]
        shade(c, header_fill)
        cell_text(c, htxt, bold=True, size=font, color=RGBColor(0xFF, 0xFF, 0xFF))
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, val in enumerate(row):
            cell_text(cells[ci], val, size=font)
            if zebra and ri % 2 == 1:
                shade(cells[ci], zebra)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    D.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def figure(path, caption, width=16.2):
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Cm(width))
    c = D.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_after = Pt(10)
    r = c.add_run(caption)
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = GREY


def page_break():
    p = D.add_paragraph()
    if MEASURE:
        r = p.add_run("⟦PB⟧")
        r.font.size = Pt(1)
    p.add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------- footer
def add_page_field(paragraph):
    run = paragraph.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1); run._r.append(it); run._r.append(f2)
    run.font.size = Pt(8)
    run.font.color.rgb = GREY


foot = D.sections[0].footer.paragraphs[0]
foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = foot.add_run("J.A.R.V.I.S.  ·  Solution Document  ·  Problem Statement 1 (Software Track)  ·  page ")
fr.font.size = Pt(8)
fr.font.color.rgb = GREY
add_page_field(foot)


# ================================================================ COVER
cover = D.add_table(rows=1, cols=1)
cov = cover.cell(0, 0)
shade(cov, "0B1B2E")
cov.text = ""
p = cov.paragraphs[0]
p.paragraph_format.space_before = Pt(90)
p.paragraph_format.space_after = Pt(0)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("HACKATHON  ·  SOFTWARE TRACK  ·  PROBLEM STATEMENT 1")
r.font.size = Pt(9)
r.font.color.rgb = RGBColor(0x67, 0xE8, 0xF9)
r.bold = True

p = cov.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(26)
p.paragraph_format.space_after = Pt(0)
r = p.add_run("J.A.R.V.I.S.")
r.font.size = Pt(46)
r.bold = True
r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

p = cov.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(30)
r = p.add_run("Justified Analysis, Reasoning & Visualization\nof Incident Systems")
r.font.size = Pt(13)
r.font.color.rgb = RGBColor(0x9F, 0xC4, 0xDD)

p = cov.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("PROPOSED SOLUTION")
r.font.size = Pt(15)
r.bold = True
r.font.color.rgb = RGBColor(0x22, 0xD3, 0xEE)

p = cov.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6)
r = p.add_run("An AI-assisted incident correlation, root-cause and impact analysis platform\nfor multi-service digital payment platforms")
r.font.size = Pt(10.5)
r.font.color.rgb = RGBColor(0xC7, 0xD6, 0xE4)

p = cov.add_paragraph()
p.paragraph_format.space_before = Pt(54)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Intelligent Systems  •  AI  •  Distributed Systems")
r.font.size = Pt(9.5)
r.font.color.rgb = RGBColor(0x67, 0xE8, 0xF9)

p = cov.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(70)
r = p.add_run("Working prototype included — 7-view interactive dashboard, 6-stage correlation engine,\n11 REST endpoints, deterministic and fully explainable")
r.font.size = Pt(8.5)
r.italic = True
r.font.color.rgb = RGBColor(0x7E, 0x93, 0xAD)

page_break()

# ================================================================ CONTENTS
h1("Contents")
toc = [
    ("1", "Executive summary", "4"),
    ("2", "Problem understanding", "5"),
    ("3", "Solution overview — what J.A.R.V.I.S. is", "6"),
    ("4", "System architecture", "7"),
    ("5", "Feature-by-feature fulfilment of the seven required functionalities", "8"),
    ("6", "Data layer — sources, ingestion and the canonical event", "10"),
    ("7", "Correlation engine — how separate alerts become one incident", "11"),
    ("8", "Root-cause detection — the ranking model", "13"),
    ("9", "Impact analysis — who and what is affected", "15"),
    ("10", "Incident timeline — how it started and spread", "16"),
    ("11", "Smart recommendations — from diagnosis to action", "17"),
    ("12", "The dashboard — a guided walkthrough", "18"),
    ("13", "End-to-end demonstration on the challenge scenario", "21"),
    ("14", "Technology stack", "23"),
    ("15", "Evaluation — accuracy, precision and performance", "24"),
    ("16", "Scalability and future roadmap", "25"),
    ("17", "Why this solution stands out", "26"),
    ("A", "Appendix A — API reference", "27"),
    ("B", "Appendix B — supported input formats and how to run", "28"),
    ("C", "Appendix C — judge Q&A preparation", "29"),
]
import json as _json
PAGES = {}
if os.environ.get("JARVIS_PAGES"):
    PAGES = _json.load(open(os.environ["JARVIS_PAGES"]))
for num, title, pg in toc:
    pg = str(PAGES.get(num, pg))
    p = D.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(1.3))
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.2), WD_ALIGN_PARAGRAPH.RIGHT)
    r = p.add_run(f"{num}")
    r.bold = True
    r.font.color.rgb = TEAL
    r.font.size = Pt(10.5)
    p.add_run("\t")
    r2 = p.add_run(title)
    r2.font.size = Pt(10.5)
    p.add_run("\t")
    r3 = p.add_run(pg)
    r3.font.size = Pt(9.5)
    r3.font.color.rgb = GREY

page_break()

# ================================================================ 1 EXEC SUMMARY
h1("Executive summary", "1")

para("Modern payment platforms run dozens of interdependent services. When one of them breaks, the "
     "outage does not announce itself once — it announces itself thirty times, as separate alerts that "
     "nobody connects. A saturated database disk shows up as a slow API, then as failed logins, then as "
     "abandoned checkouts, then as a revenue drop. Each alert is technically true and operationally "
     "useless on its own.")

para("J.A.R.V.I.S. is the layer that turns that alert storm into a single, explained story. It ingests "
     "events from metrics, logs and alert managers; finds which of them belong to the same incident; "
     "identifies the most likely root cause and ranks the alternatives; shows what the incident is "
     "touching in terms of services, users and money; reconstructs the timeline of how the fault spread; "
     "and recommends concrete remediation steps with effort, ETA and risk attached.")

h2("What is delivered")
table(
    ["Deliverable", "Detail"],
    [
        ["Working prototype", "Python + FastAPI backend with a 6-stage correlation engine and a 7-view interactive dashboard that runs entirely offline and deterministically."],
        ["Multiple data sources", "Live push API, built-in stream simulator, and an upload parser that accepts CSV, JSON, JSONL, or plain-text logs from any system."],
        ["Correlation", "Weighted union-find clustering over time proximity, dependency topology, shared trace IDs and shared failure patterns."],
        ["Root-cause detection", "Transparent 5-signal ranking model (earliness, severity, topology fit, anomaly strength, amplification) with rejected alternatives shown and justified."],
        ["Impact analysis", "Blast radius from the dependency graph, per-service impact scores, exposed users, and a revenue estimate with the formula printed on screen."],
        ["Incident report", "Auto-generated narrative plus a machine-readable JSON report at a single API endpoint."],
    ],
    widths=[3.6, 12.6],
)

h2("Headline result on the challenge scenario")
table(
    ["Metric", "Result"],
    [
        ["Events ingested", "103 events from 4 independent sources (metrics, logs, APM traces, alert manager)"],
        ["Separate alerts to responders before", "12 service-level alerts, each looking like an independent problem"],
        ["Incidents after correlation", "1 — a single incident with an identified root cause"],
        ["Noise suppressed", "12 baseline/healthy events, correctly excluded instead of being paged"],
        ["Root cause identified", "Database Host (VM) — disk IO saturation, score 0.975 / 1.000"],
        ["Correctness", "Matches the injected ground truth exactly; the true root cause ranks 1st of all candidates"],
        ["Confidence", "93.8% derived from the root-cause score"],
        ["Impact computed", "8 services, ~420,000 exposed users, 1,830 payment operations at risk, ₹76,860 exposure"],
        ["Time to a single explained diagnosis", "Under 200 milliseconds of compute on the full event set"],
    ],
    widths=[5.2, 11.0],
)

callout("Core principle:", "every number the system displays traces back to a named, inspectable rule. There is "
        "no black box between an alert and a recommended action, which is exactly what an on-call engineer needs at 3 a.m.",
        accent="0E7490")

page_break()

# ================================================================ 2 PROBLEM
h1("Problem understanding", "2")

h2("2.1  What the problem statement asks for")
para("The statement describes a digital payment platform that starts showing login failures, slow API "
     "responses and failed transactions at the same time. Each signal arrives through a different tool, "
     "each is treated as its own ticket, and responders spend the most expensive minutes of an outage "
     "triaging symptoms instead of fixing the cause.")

rich([
    ("The explicit challenge: ", {"bold": True}),
    ("build a system that collects events from different sources, finds connections between them, tracks "
     "how incidents develop, identifies the most likely root cause, explains the impact, and suggests ways "
     "to fix it.", {}),
])

h2("2.2  Why existing monitoring does not solve it")
table(
    ["Limitation of conventional monitoring", "Consequence during an incident", "How J.A.R.V.I.S. answers it"],
    [
        ["Threshold alerts fire per service, in isolation", "A single disk fault produces 12+ pages across 12 services", "Correlation merges them into one incident with one root cause"],
        ["No model of service dependencies", "The slowest service gets investigated first, not the earliest broken one", "Topology-aware ranking rewards services that are early and upstream"],
        ["Dashboards show state, not causality", "Responders know something is red but not why", "Every candidate is scored, ranked and the rejected ones are explained"],
        ["Alert fatigue from baseline noise", "Genuine signals get lost among healthy-metric pings", "A signal gate and noise-suppression stage mute non-causal events"],
        ["Impact is guessed verbally on the bridge call", "No reliable answer to \"how bad is this, in users and money?\"", "Blast radius, exposed users and a formula-backed revenue estimate"],
        ["Post-incident knowledge is lost", "The same root cause returns next quarter", "Reports are exportable artefacts with a prevention section"],
    ],
    widths=[5.0, 5.6, 5.6],
)

h2("2.3  Who the users are")
bullet("the engineer woken at 3 a.m. who needs one screen saying \"here is the cause, here is what it broke, here is what to do\".", bold_lead="On-call SRE / platform engineer — ")
bullet("needs to know within minutes whether customer logins, payments and revenue are affected, and in what magnitude.", bold_lead="Engineering manager / incident commander — ")
bullet("needs a defensible, timestamped record of what happened and what was fixed.", bold_lead="Post-incident review — ")
bullet("needs the JSON report in their own tooling without re-deriving anything.", bold_lead="Automation / downstream systems — ")

h2("2.4  Success criteria we set for ourselves")
numbered("one incident, not N alerts — the system must collapse a multi-service outage into a single diagnosed incident.")
numbered("the true root cause must rank first, and the runner-up must be explained rather than silently dropped.")
numbered("no false merges — unrelated alerts in the same time window must stay out of the incident.")
numbered("the diagnosis must be reproducible: same input, same output, every single demo run.")
numbered("the output must be actionable — a ranked list of steps, not a probability score alone.")

page_break()

# ================================================================ 3 SOLUTION OVERVIEW
h1("Solution overview — what J.A.R.V.I.S. is", "3")

para("J.A.R.V.I.S. is a six-stage pipeline wrapped in an operator dashboard. Each stage is deliberately "
     "small, testable, and produces an artefact the next stage can explain.")

table(
    ["Stage", "Name", "What it does", "Output artefact"],
    [
        ["1", "Ingest & normalise", "Accepts events from API, simulator or uploaded files; maps every source into one canonical schema; attaches a known service node where possible.", "Canonical event stream"],
        ["2", "Score", "Computes an anomaly score per event from metric deviation and severity; classifies the failure pattern from the message.", "Scored events + patterns"],
        ["3", "Cluster", "Union-Find over four weighted link rules, guarded so that time proximity alone can never merge two different services.", "Candidate incidents"],
        ["4", "Root cause", "Ranks candidate services with five normalised signals plus topology-derived coverage; keeps the alternatives.", "Ranked root causes"],
        ["5", "Impact", "Walks the dependency graph from the root cause, scores each affected service, estimates users and revenue exposure.", "Blast radius + impact"],
        ["6", "Recommend", "Selects runbook actions by root-cause service and observed failure mode; adds coordination steps; builds a recovery playbook.", "Ranked action plan"],
    ],
    widths=[1.3, 3.0, 7.4, 4.5],
)

h2("3.1  The design decisions that matter")
h3("Explainable by construction, not by explanation layer")
para("A common approach is to run a black-box model and then ask a language model to rationalise its "
     "output. That produces confident-sounding text with no guarantee of truth. J.A.R.V.I.S. inverts it: "
     "the scoring rules are the system, and the narrative is generated directly from the stored score "
     "components. If the dashboard says \"explains 90.6% of events\", that number is a field in the report, "
     "computed from the same data the interface is rendering.")

h3("Deterministic core, so the demo survives the demo")
para("Random seeds, model drift and temperature all have a habit of misbehaving in front of judges. The "
     "core engine is arithmetic over a fixed topology and a fixed event set. The same scenario produces "
     "byte-identical scores on every run, on any machine, with no network access. An optional ML layer can "
     "be added later — the interim design leaves a clean seam for it — but the demo does not depend on it.")

h3("Topology is first-class data, not an afterthought")
para("The single most useful fact in incident response is which service depends on which. J.A.R.V.I.S. "
     "carries a fourteen-service dependency graph with tiers, criticality and user exposure. That graph is "
     "what turns a list of alerts into a causal chain, and it is the reason the system can state "
     "\"db-host → db-proxy → ledger-db → payment-api → checkout-ui\" instead of \"these things all look bad\".")

h3("Noise is a first-class output")
para("Suppression is shown, not hidden. The dashboard reports exactly how many events were excluded and "
     "why, because an on-call engineer who suspects the system swallowed a real signal must be able to "
     "audit that decision in one click.")

page_break()

# ================================================================ 4 ARCHITECTURE
h1("System architecture", "4")

figure("/home/user/jarvis/docs/architecture.png", "Figure 1 — J.A.R.V.I.S. six-stage architecture, from four independent data sources to an explained incident report.")

h2("4.1  Component responsibilities")
table(
    ["Component", "Responsibility", "Key properties"],
    [
        ["Ingestion adapters", "Accept push events, simulator bursts, or uploaded log files", "One parser handles CSV / JSON / JSONL / plain text; unknown services are parsed, never dropped"],
        ["Normaliser", "Map heterogeneous records onto one canonical event", "Timestamps in six formats; severity inferred from level or message pattern when absent"],
        ["Topology registry", "Declare services, dependencies, tier, criticality and user exposure", "14 services in the payment scenario; editable data, not code"],
        ["Correlation engine", "Group events into incidents", "Union-Find, O(n²) within the time window, exact and order-independent"],
        ["Root-cause ranker", "Score and order candidate services", "Five weighted signals; every component stored for audit"],
        ["Impact analyser", "Compute blast radius and business exposure", "BFS over dependents; transparent arithmetic printed in the report"],
        ["Timeline builder", "Order the spread of the incident", "First-seen per service, with hop distance from the root"],
        ["Recommendation engine", "Select remediation steps", "Runbook matched on service + failure-mode keywords; effort/ETA/risk per step"],
        ["Report generator", "Produce the human narrative and machine JSON", "Single endpoint, stable schema, exportable from the dashboard"],
    ],
    widths=[3.4, 5.4, 7.4],
)

h2("4.2  Request flow")
code_block([
    "POST /api/ingest/upload  (multipart file)",
    "   └─ parse_log_file()  ->  canonical events[]",
    "        └─ engine.analyse(events)",
    "             1. normalise()        attach service, score anomaly, classify patterns",
    "             2. cluster()          union-find over weighted link rules",
    "             3. rank_root_causes() score every candidate service in the cluster",
    "             4. impact_analysis()  blast radius + users + revenue",
    "             5. recommendations()  runbook for root service and failure mode",
    "             6. narrative()        evidence-grounded explanation",
    "        └─ state stored in memory; GET /api/state returns everything the UI needs",
    "GET  /api/incidents/{id}/report ->  JSON incident report (export)",
])

page_break()

# ================================================================ 5 FEATURES
h1("Feature-by-feature fulfilment of the seven required functionalities", "5")

para("The problem statement lists seven required capabilities. Each is implemented, exposed in the "
     "interface, and backed by an API response field that can be inspected live.")

# 5.1
h2("5.1  Multiple data sources")
rich([("Requirement: ", {"bold": True}), ("collect events from APIs, uploaded log files and simulated live data.", {})])
bullet("POST /api/ingest/events accepts a batch of structured events from any agent or webhook.", bold_lead="API — ")
bullet("the upload button accepts CSV, JSON array, JSON-lines and plain-text logs; timestamps in six formats; severity inferred from level fields or from message keywords when a file has no severity column.", bold_lead="Uploaded log files — ")
bullet("a deterministic twelve-minute outage burst with four source types (prometheus, log, apm, alertmanager), including four deliberately plausible unrelated alerts to test precision.", bold_lead="Simulated live data — ")
bullet("the demo ships a sample CSV that mirrors a real, messy export, so the parser can be shown working on a file the judges have not seen before.", bold_lead="Sample — ")

# 5.2
h2("5.2  Event correlation")
rich([("Requirement: ", {"bold": True}), ("find connections between different events using timestamps, common services and activity patterns.", {})])
para("Two events are linked when their weighted connection strength reaches 0.34, where the strength is:")
code_block([
    "strength(a,b) = 0.30 x time_proximity      (1.0 at Δt=0, 0.0 at Δt>=4 min)",
    "              + 0.35 x topology_affinity   (same service 1.0 | dependency/shared blast radius 0.8",
    "                                            | shared dependency 0.45 | unrelated 0.0)",
    "              + 0.25 x shared_trace_id     (1.0 when both events carry the same trace id)",
    "              + 0.10 x shared_pattern      (1.0 when both match the same failure signature)",
])
rich([("The semantic guard: ", {"bold": True}),
      ("time proximity is never sufficient on its own. For two different services to be merged, raw time "
       "overlap must be accompanied by a real relationship — a direct dependency, a shared dependency with "
       "an error-level signal on at least one side, a shared trace ID, or a shared failure pattern. This "
       "single rule is what stops the system from turning every busy five-minute window into a "
       "mega-incident, and it is the difference between a demo that works and one that embarrasses itself "
       "on a noisy data set.", {})])
figure("/home/user/jarvis/docs/dash_overview.png", "Figure 2 — Overview: one incident, one ranked root cause, a 93.8% confidence ring, the correlation evidence and the count of events correctly suppressed as noise.", width=16.0)

# 5.3
h2("5.3  Root cause detection")
rich([("Requirement: ", {"bold": True}), ("identify the most likely reason behind an incident.", {})])
para("Each service that appears in the incident is scored on five normalised signals; the weights, the "
     "resulting scores and the rejected alternatives are all visible in the interface and in the report. "
     "The full model is derived in section 8. On the challenge scenario:")
table(
    ["Rank", "Candidate service", "Score", "Events", "Explains", "Verdict"],
    [
        ["1", "Database Host (VM) — db-host", "0.975", "13", "90.6%", "ROOT CAUSE (matches ground truth)"],
        ["2", "DB Connection Proxy — db-proxy", "0.803", "9", "75.3%", "Rejected: fires 2 min later, downstream"],
        ["3", "User DB — user-db", "0.761", "7", "56.5%", "Rejected: fires 4.7 min later, covers half the incident"],
        ["4", "Ledger DB — ledger-db", "0.757", "7", "38.8%", "Rejected: fires 4.3 min later, covers a third"],
    ],
    widths=[1.2, 5.4, 1.6, 1.4, 1.8, 4.8],
)

# 5.4
h2("5.4  Impact analysis")
rich([("Requirement: ", {"bold": True}), ("show which services, applications and users are affected.", {})])
para("Impact is computed from the dependency graph rather than from the alert list, so it can name services "
     "that never emitted a single log line but are still on the failing path. On the demonstration "
     "incident: 8 affected services, ~420,000 exposed users, 1,830 payment operations at risk and "
     "₹76,860 of revenue exposure — with the arithmetic shown on screen (section 9).")

# 5.5
h2("5.5  Incident timeline")
rich([("Requirement: ", {"bold": True}), ("display how an incident started and spread across different services.", {})])
para("A per-service swimlane chart with one tick per correlated event, ordered by first appearance, plus a "
     "propagation table that labels every service as ROOT CAUSE, propagated (with hop distance from the "
     "root) or coincidental. The demonstration incident reads as a clean six-step causal chain over "
     "9.6 minutes.")

# 5.6
h2("5.6  Smart recommendations")
rich([("Requirement: ", {"bold": True}), ("suggest possible solutions based on the identified problem.", {})])
para("Recommendations are selected deterministically from a runbook library keyed on the root-cause service "
     "and the observed failure mode, then classified by phase (mitigate / stabilise / prevent / "
     "coordinate), with effort, ETA and risk per step — and each step states why it was chosen. For the "
     "database-host case the plan opens with freeing disk space and moving WAL to a dedicated volume, "
     "followed by the pool-sizing fix at the proxy that the fault exposed.")

# 5.7
h2("5.7  Interactive dashboard")
rich([("Requirement: ", {"bold": True}), ("display related incidents, their severity, connections and investigation results.", {})])
para("Seven linked views — Overview, Topology, Timeline, Root Cause, Impact, Recommendations, Events — all "
     "driven by the same incident object, with a searchable event stream and a one-click JSON report "
     "export. Section 12 walks through each view. No chart-library dependency, no external asset: the "
     "whole interface is a single self-contained page that renders offline.")

page_break()

# ================================================================ 6 DATA LAYER
h1("Data layer — sources, ingestion and the canonical event", "6")

h2("6.1  Why a canonical event")
para("Metrics, logs and alerts disagree about almost everything: field names, timestamp formats, whether "
     "severity is a number or a string, whether a value exists at all. Correlation needs one shape. Every "
     "adapter therefore converges on a single record: timestamp, source, service, severity, message, "
     "numeric value, baseline, unit and trace id. Anything extra that the original record carried is "
     "preserved in the raw event for audit.")

code_block([
    "{",
    '  "ts":         "2025-03-14T10:02:45+00:00",   // ISO-8601, always UTC',
    '  "source":     "prometheus",                    // prometheus | log | apm | alertmanager | csv | json',
    '  "service":    "db-host",                       // matched to the topology registry when possible',
    '  "type":       "metric",                        // metric | log | alert | trace',
    '  "severity":   "warning",                       // info | warning | error | critical',
    '  "message":    "iowait percentage on db-host elevated",',
    '  "value":      91.0,                            // optional numeric observation',
    '  "baseline":   18.0,                            // optional healthy baseline -> enables deviation scoring',
    '  "unit":       "%",',
    '  "trace_id":   null                             // optional correlation handle',
    "}",
])

h2("6.2  Ingestion paths")
table(
    ["Path", "Endpoint", "Typical use"],
    [
        ["Push API", "POST /api/ingest/events", "A real agent or webhook forwards events; usable as the integration point for any monitoring stack"],
        ["Simulated stream", "POST /api/ingest/simulate", "Deterministic burst with four source types; optional append mode to grow a live stream on stage"],
        ["File upload", "POST /api/ingest/upload", "CSV, JSON, JSONL or plain text; the parser reports how many records it accepted"],
        ["Seed", "on startup", "The challenge scenario is loaded automatically, so the dashboard is never empty when a judge opens it"],
    ],
    widths=[3.0, 4.6, 8.6],
)

h2("6.3  Parsing real-world messiness")
para("Uploaded logs are rarely clean. The parser therefore handles: six timestamp formats including "
     "space-separated and fractional seconds; log levels spelled as WARN/WARNING/CRIT/FATAL; records with "
     "no severity at all, where severity is inferred from message keywords (\"no space left\" → critical, "
     "\"connection refused / timeout / exhausted\" → error, \"slow / degraded / retry / spike\" → warning); "
     "and records where the service is not a field but appears inside the message, in which case the parser "
     "matches it against the known topology. Unknown services are still ingested and still correlated — "
     "they simply score zero on topology affinity, which is the honest outcome.")

h2("6.4  The signal gate, and why healthy events are not facts")
para("A monitoring stream contains far more healthy observations than failures. Treating a normal p99 "
     "latency sample as an incident fact guarantees false positives. J.A.R.V.I.S. therefore gates "
     "correlation on signals: an event participates in clustering only if its severity is warning or above, "
     "or if its value deviates at least 1.6× from the declared baseline. Healthy events are still ingested "
     "and still visible in the event stream as context — they simply cannot cause a merge. In the "
     "demonstration run this gate correctly excluded 12 of 103 events.")

page_break()

# ================================================================ 7 CORRELATION
h1("Correlation engine — how separate alerts become one incident", "7")

h2("7.1  The problem in one sentence")
para("Correlation is a clustering problem with a hostile distance metric: two events are related if they "
     "are close in time or close in the dependency graph or share a trace or share a failure signature — "
     "but being close in time alone proves nothing.")

h2("7.2  The four link signals")
table(
    ["Signal", "Weight", "Measured how", "Why it earns its weight"],
    [
        ["Time proximity", "0.30", "Linear decay to zero at a 4-minute window", "Related symptoms appear together, but time alone is the weakest possible evidence and cannot merge services on its own"],
        ["Topology affinity", "0.35", "1.0 same service · 0.8 dependency or shared blast radius · 0.45 shared dependency · 0.0 unrelated", "A fault in a dependency is *expected* to break its dependents; this is the strongest structural evidence available"],
        ["Shared trace ID", "0.25", "Exact match of a distributed trace identifier", "The same request failing in two services is not a coincidence — it is one request"],
        ["Shared failure pattern", "0.10", "Both messages match the same signature (disk_io, pool_exhaustion, latency, dependency_error, auth_failure, payment_failure, rate_limit)", "Identical failure modes suggest a common mechanism"],
    ],
    widths=[3.0, 1.3, 6.1, 5.8],
)

h2("7.3  Clustering with a semantic guard")
para("Events are grouped with a union-find structure: every pair inside the time window is scored, and a "
     "pair is merged when its strength reaches the threshold and the semantic guard is satisfied. "
     "Union-find is the right structure here because correlation is transitive — if A links to B and B "
     "links to C, all three belong to the same incident — and it gives exact, order-independent results in "
     "a single pass.")

code_block([
    "for each pair (a, b) with |a.ts - b.ts| <= 4 min:",
    "    if a and b are both non-signals:              skip          # healthy vs healthy",
    "    if a.service != b.service:",
    "        strong  = topology_affinity >= 0.8         # direct dependency or shared blast radius",
    "        sibling = topology_affinity == 0.45        # share a dependency",
    "        serious = max(severity(a), severity(b)) >= error",
    "        if not (strong or same_trace or (sibling and same_pattern and serious)):",
    "            skip                                   # time alone never merges two services",
    "    if strength(a, b) >= 0.34:",
    "        union(a, b)",
])

h2("7.4  Noise suppression, shown rather than hidden")
para("After clustering, a cluster is promoted to an incident only if it spans at least three services, its "
     "best root candidate scores at least 0.55, that candidate has at least two downstream dependents, and "
     "the cluster is not self-contained among low-criticality services. Everything else is reported as "
     "suppressed — with the count, the services involved, the reason and an example event. In the "
     "demonstration run, a notifications backlog and a WAF bot-traffic spike occurred inside the same "
     "window and were correctly kept out of the incident.")

callout("Why this matters for a demo:", "a naive correlator merges on time and produces a single giant "
        "\"incident\" that includes unrelated alerts. That looks impressive for ten seconds and falls apart "
        "the moment a judge asks why the notification service is in a database outage.",
        accent="92400E", fill="FFF6E8")

h2("7.5  What the correlation produced")
table(
    ["Cluster", "Services", "Events", "Outcome"],
    [
        ["Payment platform degradation", "db-host, db-proxy, ledger-db, user-db, payment-api, auth, checkout-ui, mobile-app", "85", "Promoted to incident INC-112, critical, 93.8% confidence"],
        ["Notification / WAF noise", "notification, waf, vendor-psp, psp-connector (isolated)", "12", "Suppressed — no topological link to a critical path"],
    ],
    widths=[4.2, 6.4, 1.6, 4.0],
)

page_break()

# ================================================================ 8 ROOT CAUSE
h1("Root-cause detection — the ranking model", "8")

para("Choosing the root cause is not the same as choosing the loudest service. A payment API screaming "
     "thousands of 5xx errors is usually a symptom; the quiet database host that first showed elevated "
     "disk wait is usually the cause. The ranker therefore rewards five properties that a genuine root "
     "cause tends to have, and penalises two patterns that false positives exhibit.")

h2("8.1  The five signals")
table(
    ["Signal", "Weight", "Definition", "Rationale"],
    [
        ["Earliness", "0.30", "1 − (first_event − cluster_start) / cluster_span", "Causes precede effects. The first service to degrade is the strongest temporal candidate"],
        ["Severity", "0.20", "Mean severity weight of its events (info 0.05 … critical 1.0)", "A service that only emitted warnings is less likely to be an outage origin"],
        ["Topology fit", "0.25", "min(1, downstream services explained / 3)", "A root cause must be able to explain the spread; a leaf service explains nothing"],
        ["Anomaly strength", "0.15", "Max per-event anomaly score", "Metric deviation against a declared baseline is harder evidence than an error message"],
        ["Amplification", "0.10", "min(1, blast radius size / 6)", "A fault with a wide blast radius better matches an incident that touched many services"],
    ],
    widths=[2.8, 1.3, 6.0, 6.1],
)

h2("8.2  The two penalties")
bullet("a service with a single unusual event cannot win on earliness alone. The score is reduced by 0.10 × (3 − n)/2 for fewer than three events, which is what stopped a lone WAF warning from ranking near the root cause in an earlier iteration.", bold_lead="Thin evidence — ")
bullet("for every service in the cluster that could itself be the ancestor of this candidate, 0.05 is subtracted. The most upstream explainer wins ties.", bold_lead="Upstream dominance — ")

h2("8.3  The formula, and the result")
code_block([
    "score = 0.30 x earliness      + 0.20 x severity",
    "      + 0.25 x topology_fit   + 0.15 x anomaly",
    "      + 0.10 x amplification  + 0.08 (if a metric event exceeds anomaly 0.5)",
    "      - 0.10 x (3 - event_count)/2   [only when event_count < 3]",
    "      - 0.05 x upstream_count",
])
para("On the challenge scenario the winner scores 0.975 with earliness 1.00, severity 0.64, topology fit "
     "1.00, anomaly 0.78 and amplification 1.00 — first to fire, structurally upstream, and able to explain "
     "90.6% of every event in the incident. The second-ranked candidate explains 75.3% and fires two "
     "minutes later; the interface says so explicitly, because an on-call engineer who disagrees with the "
     "system needs to see what the system considered.")

figure("/home/user/jarvis/docs/dash_rootcause.png", "Figure 3 — Root cause view: candidate ranking with every score component exposed, the primary evidence for the winner, and an explicit justification for each rejected alternative.")

h2("8.4  Confidence, and why it is not a probability")
para("Incident confidence is reported as 0.45 + 0.5 × root_score, capped at 0.99, which maps a clean "
     "winner to the high nineties and a contested cluster to the sixties. It is honestly labelled "
     "confidence rather than probability: the system is not estimating the chance that it is right, it is "
     "expressing how decisively one candidate dominates the alternatives on the available evidence. "
     "Presenting it as a calibrated probability would be a claim the model cannot support.")

page_break()

# ================================================================ 9 IMPACT
h1("Impact analysis — who and what is affected", "9")

h2("9.1  Blast radius from the graph, not from the alerts")
para("Impact is computed by walking the dependency graph outward from the root cause and taking the union "
     "of that reachable set with the services that actually emitted signals. This matters because some "
     "affected services never log anything useful: a checkout page that simply shows \"try again\" to the "
     "user produces no error line, but it is firmly inside the blast radius and firmly inside the business "
     "impact.")

h2("9.2  Per-service impact score")
code_block([
    "impact_score = 70 x (criticality / 5) + min(30, correlated_events x 2.5)    # directly observed",
    "impact_score = 70 x (criticality / 5)                                     # in blast radius only",
])
para("Business criticality dominates, because a degraded authentication service matters more than a busy "
     "notification queue regardless of event volume; observed event count adds the evidence of how loudly "
     "it actually failed.")

table(
    ["Service", "Tier", "Criticality", "Events", "Impact"],
    [
        ["Auth Service", "application", "5 / 5", "15", "100.0"],
        ["Database Host (VM) — root cause", "infra", "5 / 5", "13", "100.0"],
        ["Payment API", "application", "5 / 5", "18", "100.0"],
        ["DB Connection Proxy (PgBouncer)", "infra", "5 / 5", "9", "92.5"],
        ["Checkout Web UI", "edge", "5 / 5", "7", "87.5"],
        ["Ledger DB (PostgreSQL)", "data", "5 / 5", "7", "87.5"],
        ["User DB (PostgreSQL)", "data", "4 / 5", "7", "73.5"],
        ["Mobile Banking App", "edge", "4 / 5", "1", "58.5"],
    ],
    widths=[6.0, 2.6, 2.2, 1.8, 2.0],
)

h2("9.3  Business impact with the formula on screen")
para("Estimates in an incident review must be defensible. J.A.R.V.I.S. therefore computes exposure from "
     "four stated inputs and prints the arithmetic in the interface:")
code_block([
    "ops_per_minute = users_exposed x 2.5 transactions/day / 1440",
    "failed_ops     = ops_per_minute x incident_duration x observed_failure_rate",
    "revenue        = failed_ops x average_order_value (proxy: Rs 42)",

    "challenge scenario:",
    "  420,000 x 2.5 / 1440            = 729 ops/min",
    "  729 x 9.6 min x 26% failure    = 1,830 failed operations",
    "  1,830 x Rs 42                  = Rs 76,860 exposure",
])
para("A judge or a manager can challenge any single input — the transaction rate, the failure rate, the "
     "order value — and the number moves transparently. That is a deliberate contrast to a model that "
     "outputs a single unexplained figure.")

h2("9.4  Impact versus coincidence")
para("Services that fired inside the window but have no dependency path from the root cause are listed "
     "separately as coincidental, with the reason stated. In this run the notification service, the WAF, "
     "the PSP connector and the third-party vendor gateway fall into that category: they were noisy at the "
     "wrong moment, but nothing connects them to a disk fault on the database host. Naming them explicitly "
     "prevents the classic post-incident mistake of adding a phantom cause to the review document.")

figure("/home/user/jarvis/docs/dash_impact.png", "Figure 4 — Impact view: affected services ranked by impact score, business impact with a transparent estimate, and the coincidence list kept deliberately separate.")

page_break()

# ================================================================ 10 TIMELINE
h1("Incident timeline — how it started and spread", "10")

para("The timeline answers the question every post-incident review opens with: what broke first, and how "
     "did the failure travel? Two artefacts are produced from the same data — a swimlane chart for humans "
     "and an ordered propagation table for reports.")

h2("10.1  Reconstructed propagation on the challenge scenario")
table(
    ["#", "Offset", "Service", "Role", "Hops", "Events", "Headline signal"],
    [
        ["1", "+0.0 min", "Database Host (VM)", "ROOT CAUSE", "0", "13", "iowait on db-host elevated; WAL write failing — no space left on device"],
        ["2", "+2.0 min", "DB Connection Proxy", "propagated", "1", "9", "pgbouncer client connection pool exhausted; 214 clients waiting"],
        ["3", "+4.3 min", "Ledger DB", "propagated", "2", "7", "query p99 latency degraded"],
        ["4", "+4.7 min", "User DB", "propagated", "2", "7", "query p99 latency degraded"],
        ["5", "+5.3 min", "Payment API", "propagated", "3", "18", "5xx error rate above 10% — upstream ledger timeout"],
        ["6", "+6.8 min", "Auth Service", "propagated", "3", "15", "login failure rate above 20%"],
        ["7", "+7.5 min", "Checkout Web UI", "propagated", "4", "7", "checkout step returned 502 from payment-api"],
        ["8", "+8.1 min", "Mobile Banking App", "propagated", "4", "1", "elevated relogin loop detected"],
    ],
    widths=[0.8, 1.5, 3.4, 1.9, 1.1, 1.2, 6.3],
)

para("Read as a story: a disk on the database host filled and began stalling writes, the connection pool "
     "in front of that host exhausted two minutes later, both databases slowed at four minutes, the payment "
     "API and authentication service failed at five and seven minutes, and the customer-facing surfaces "
     "degraded last. Twelve separate alerts; one causal chain.")

figure("/home/user/jarvis/docs/dash_timeline.png", "Figure 5 — Timeline view: per-service swimlanes with one tick per correlated event, and the propagation table labelling each service by role and hop distance from the root cause.")

h2("10.2  Why hops matter")
para("Hop distance converts a chronological list into a causal one. A service at hop 4 from the root cause "
     "is not an alternative suspect — it is a customer-facing consequence. During the demo this is the "
     "single most persuasive visual: the bars do not scatter randomly, they cascade left to right and "
     "outward from one lane.")

page_break()

# ================================================================ 11 RECOMMENDATIONS
h1("Smart recommendations — from diagnosis to action", "11")

para("A diagnosis that ends at \"the database host is the problem\" leaves the hardest work undone. The "
     "recommendation engine converts the root cause and its observed failure mode into an ordered plan, and "
     "it is deliberately constrained: it recommends only actions that exist in a curated runbook library, "
     "because an invented remediation is worse than no remediation during an outage.")

h2("11.1  How a plan is selected")
numbered("match the root-cause service against the runbook library (keyed by service: db-host, db-proxy, auth, payment-api, vendor-psp).")
numbered("widen by failure mode — when the root cause's own messages show disk or IO pressure, the plan adds the pool-sizing steps at the proxy that the fault exposed downstream, since fixing only the disk leaves the fleet vulnerable to the same cascade next time.")
numbered("classify every step into a phase: mitigate (stop the bleeding), stabilise (restore service), prevent (stop recurrence), coordinate (run the incident well).")
numbered("attach effort, ETA, risk and a one-line justification to each step, so the plan can be executed by someone who did not write it.")
numbered("append a recovery and verification playbook — verify the root metric returned to baseline, backfill failed payments from the retry queue, re-run correlation over the window, and store the report as a post-incident artefact.")

h2("11.2  The plan produced for the challenge scenario")
table(
    ["#", "Phase", "Action", "Target", "Effort", "ETA", "Risk"],
    [
        ["1", "mitigate", "Free disk space on the db-host data volume; extend it online", "db-host", "Low", "10 min", "Low"],
        ["2", "mitigate", "Move WAL to a dedicated low-latency NVMe volume to stop IO contention", "db-host", "Medium", "45 min", "Medium"],
        ["3", "stabilise", "Repoint ledger-db to the read replica / controlled failover", "db-host", "Medium", "15 min", "Medium"],
        ["4", "prevent", "Add disk-utilisation and iowait alerting at 80% / 25%", "db-host", "Low", "20 min", "Low"],
        ["5", "prevent", "Raise pgBouncer pool_size and set server_idle_timeout", "db-proxy", "Low", "10 min", "Low"],
        ["6", "prevent", "Apply per-service connection quotas so one workload cannot starve the pool", "db-proxy", "Low", "15 min", "Low"],
        ["7", "coordinate", "Page the owning team with the correlation report attached", "incident", "Low", "5 min", "Low"],
        ["8", "coordinate", "Suppress downstream duplicate alerts while the root cause is unhealthy", "incident", "Low", "10 min", "Low"],
    ],
    widths=[0.8, 1.9, 7.0, 1.8, 1.3, 1.3, 1.1],
)

h2("11.3  Why the first two steps are the right first two steps")
para("Freeing disk space stops the pain immediately and is low-risk. Moving the write-ahead log to a "
     "separate volume is the actual structural fix, because the underlying cause is IO contention between "
     "checkpoint writes and reads on a single volume — not merely that the disk was full. Steps 5 and 6 "
     "address the amplifier: the proxy had no per-service quota, so one saturated backend could exhaust "
     "the pool for every caller. That is precisely the kind of compounding weakness a single-alert view "
     "never surfaces, and it is the reason the recommendation engine reads the whole incident rather than "
     "just the top-scoring event.")

page_break()

# ================================================================ 12 DASHBOARD
h1("The dashboard — a guided walkthrough", "12")

para("The interface is one self-contained page: no build step, no chart library, no external asset, and it "
     "renders identically offline. Every view reads from the same incident object, so switching tabs never "
     "changes the underlying story.")

h2("12.1  Overview")
para("Top-left of the main panel is the answer: the ranked root cause, its score, and the share of the "
     "incident it explains. Beside it, a confidence ring. Below, a generated narrative that names the "
     "evidence, the propagation paths and the rejected alternative — in that order, because that is the "
     "order a responder asks the questions. On the right, the noise panel states exactly how many events "
     "were set aside and why.")

h2("12.2  Topology")
para("A layered dependency graph rendered as SVG, oriented so that a fault flows left to right. The root "
     "cause is marked with a pulsing node and a red inbound edge; propagated services are amber; "
     "coincidental and healthy services are grey and cyan, with dashed edges where no part of the incident "
     "travelled. Clicking any node lists the events that service emitted inside the incident window — which "
     "turns the graph from a picture into an investigation tool.")

h2("12.3  Timeline")
para("A swimlane chart with one tick per correlated event, coloured by severity, ordered by first "
     "appearance, annotated with hop distance from the root. Beneath it, the propagation table described in "
     "section 10.")

h2("12.4  Root Cause")
para("Two panels of evidence. The left ranks every candidate with its full score breakdown — earliness, "
     "severity, topology fit, anomaly and amplification — so a sceptical judge can recompute any score by "
     "hand. The right shows the top three signals emitted by the winning service, with the metric ratio "
     "against baseline. Below, a rejected-alternatives table with a plain-language reason for every "
     "rejection.")

h2("12.5  Impact")
para("Affected services with tier, criticality, event count and impact score; business impact tiles for "
     "users, failed operations, revenue and duration; the estimate formula printed verbatim; and a separate "
     "coincidence table.")

h2("12.6  Recommendations")
para("Phase-tagged action cards with effort, ETA, risk, target and a justification line, followed by the "
     "recovery and verification playbook.")

h2("12.7  Events")
para("The full correlated event stream with search across message, service and trace id, plus severity and "
     "source filters. Each row shows the value, the baseline ratio and the computed anomaly score — the raw "
     "material behind every number in the other six views. This tab exists because a diagnosis you cannot "
     "audit is a diagnosis you cannot trust.")

h2("12.8  Demo controls")
table(
    ["Control", "What happens", "Why it is on stage"],
    [
        ["Simulate live burst", "Regenerates the twelve-minute, four-source outage", "Shows ingestion, correlation and diagnosis end to end in one click"],
        ["Append burst", "Adds another burst to the existing stream", "Demonstrates streaming behaviour and growing clusters"],
        ["Upload logs", "Parses a CSV / JSON / JSONL / text file and re-analyses", "Proves the system is not hard-coded to the built-in scenario — bring your own file"],
        ["Download sample log", "Saves a messy sample CSV", "Lets a judge hand the file back through the uploader, on the spot"],
        ["Reset to scenario", "Restores the seeded demonstration", "Recovers instantly from a mis-click"],
        ["Export report", "Downloads the JSON incident report", "Shows the machine-readable artefact for downstream tooling"],
    ],
    widths=[3.4, 6.6, 6.2],
)

page_break()

# ================================================================ 13 DEMO
h1("End-to-end demonstration on the challenge scenario", "13")

para("This section is written as an executable demo script: the exact sequence, the numbers to say out loud, "
     "and what each step proves.")

h2("13.1  The script")
table(
    ["Step", "Action on screen", "What to say", "What it proves"],
    [
        ["1", "Open the dashboard", "\"103 events arrived from four independent sources in twelve minutes.\"", "Multi-source ingestion, seeded and ready"],
        ["2", "Point at the header chips", "\"Four sources, 103 events, one incident, 12 events suppressed.\"", "Correlation happened before the human looked"],
        ["3", "Overview tab", "\"Not twelve problems. One root cause: the database host. 93.8% confidence.\"", "Collapse of N alerts into 1 incident"],
        ["4", "Scroll the narrative", "\"Disk IO saturation at 10:02 → pool exhaustion at 10:04 → database latency at 10:06 → payment and login failures at 10:07.\"", "Causal chain, not a chronological list"],
        ["5", "Topology tab", "\"Click the root cause — 13 events, all about disk and IO. Click the payment API — downstream, hop 3.\"", "Topology-driven reasoning, interactive"],
        ["6", "Timeline tab", "\"Left to right, nothing scatters: the fault travelled along the dependency edges.\"", "Spread is explained, not just plotted"],
        ["7", "Root Cause tab", "\"Score 0.975. Second place explains 75% and fires two minutes later — here is why it lost.\"", "Transparent ranking with rejected alternatives"],
        ["8", "Impact tab", "\"8 services, 420,000 users, 1,830 failed payments, ₹76,860 — and here is the arithmetic.\"", "Quantified business impact"],
        ["9", "Recommendations tab", "\"Free disk space first, then move WAL off the data volume, then fix the pool quota that turned one slow disk into a platform outage.\"", "Diagnosis converted into an ordered plan"],
        ["10", "Events tab, filter to critical", "\"Every number elsewhere traces back to these rows.\"", "Auditability"],
        ["11", "Upload → sample CSV", "\"Same answer from a messy CSV you just handed me.\"", "Not hard-coded to the built-in scenario"],
        ["12", "Export report", "\"And the whole diagnosis is a JSON artefact for the ticketing system.\"", "Integration-ready output"],
    ],
    widths=[0.9, 3.6, 7.4, 4.3],
)

h2("13.2  The before-and-after that sells it")
table(
    ["", "Without J.A.R.V.I.S.", "With J.A.R.V.I.S."],
    [
        ["Alerts an engineer must triage", "12, across 8 services, in 4 tools", "1 incident"],
        ["Hypotheses to test manually", "\"Is it the payment gateway? the auth service? the proxy?\"", "1 ranked cause and 3 named alternatives"],
        ["First correct action", "After correlation by hand, typically 15–40 minutes", "Available at 10:02, in milliseconds"],
        ["Impact statement to management", "Verbal estimate on the bridge call", "8 services, 420,000 users, ₹76,860 exposure"],
        ["Unrelated alerts in the same window", "Investigated as if relevant", "Named and excluded, with reasons"],
        ["Post-incident artefact", "Reconstructed from memory", "Timestamped JSON report with prevention steps"],
    ],
    widths=[4.6, 6.0, 5.6],
)

page_break()

# ================================================================ 14 STACK
h1("Technology stack", "14")

table(
    ["Layer", "Choice", "Why this and not the heavier alternative"],
    [
        ["Backend", "Python 3 + FastAPI", "Readable engine code the judges can follow live; automatic OpenAPI docs; typed request models with Pydantic"],
        ["Engine", "Pure Python standard library", "No NumPy, no pandas, no model weights — installs in seconds, runs offline, fully deterministic"],
        ["Clustering", "Union-Find (disjoint set)", "Exact and order-independent for a transitive relation; no tuning, no convergence risk"],
        ["Topology", "Declarative registry, BFS traversal", "The dependency graph is data an engineer can edit, not logic buried in code"],
        ["Frontend", "Single HTML page, vanilla JS, inline SVG", "Zero build step, zero CDN dependency, renders in the sandboxed preview and on a venue with no Wi-Fi"],
        ["Transport", "REST + JSON", "Every panel is reproducible with curl; the same API is the integration surface for real tooling"],
        ["Input parsing", "csv + json + regex from the standard library", "Handles CSV, JSON, JSONL and plain text without an extra dependency"],
    ],
    widths=[2.4, 4.4, 9.4],
)

h2("14.1  What was deliberately not used")
bullet("\"we use a graph database\" is not a differentiator when the graph has fourteen nodes. An in-memory adjacency list with BFS is faster to read, faster to run and easier to defend.", bold_lead="No graph database — ")
bullet("the demo must survive a venue with no internet. A CDN-loaded chart library is a single point of failure on stage.", bold_lead="No chart libraries — ")
bullet("a frozen checkpoint would be honest only if the training data were shown. A deterministic rule engine needs no such defence.", bold_lead="No pre-trained model in the core path — ")

h2("14.2  Where a model genuinely helps later")
para("A machine-learning layer is the right next step for two specific jobs: learning per-service baselines "
     "from history so the anomaly score is seasonal rather than absolute, and learning recurrence so the "
     "system can say \"this combination occurred eleven times and was always disk pressure.\" Both are "
     "additive. Neither requires changing the architecture, because the score components are already "
     "separated and stored per event and per candidate.")

page_break()

# ================================================================ 15 EVALUATION
h1("Evaluation — accuracy, precision and performance", "15")

h2("15.1  Ground-truth check")
para("The built-in scenario carries a hidden ground-truth marker on the events that represent the injected "
     "fault. The engine never reads that marker; it exists only to score the engine's output afterwards. "
     "On the demonstration run the engine independently ranked the injected fault source first.")

table(
    ["Check", "Expected", "Actual", "Result"],
    [
        ["True root cause ranked 1st", "db-host", "db-host (0.975 of 1.000)", "Pass"],
        ["True root cause identified as earliest", "db-host at 10:02", "db-host at 10:02, earliness 1.00", "Pass"],
        ["Propagation path correct", "db-host → db-proxy → ledger-db → payment-api → checkout-ui", "exact match, 4 hops", "Pass"],
        ["Unrelated alerts excluded", "notification, waf, vendor-psp, psp-connector", "all four classified coincidental", "Pass"],
        ["Healthy events not treated as signals", "12 baseline events", "12 suppressed, listed with reason", "Pass"],
        ["Incidents produced", "1", "1 (INC-112, critical)", "Pass"],
        ["Determinism", "identical on re-run", "identical scores over repeated runs", "Pass"],
    ],
    widths=[5.4, 4.8, 4.0, 2.0],
)

h2("15.2  Precision under deliberate noise")
para("Three of the four unrelated alerts were planted to be plausible rather than obviously wrong: a "
     "notification queue backlog warning, a WAF blocked-request spike and a vendor webhook rotation notice. "
     "The backlog arrived 1.3 minutes after the root cause fired — inside the correlation window, and "
     "temporally closer than three of the genuine downstream services. It was still excluded, because it "
     "has no dependency path from the database host and no shared trace. That is the property under test: "
     "time proximity is not treated as proof of causality.")

h2("15.3  Performance")
table(
    ["Measure", "Observed", "Notes"],
    [
        ["Events processed", "103 events, 8 services, 4 sources", "Single burst"],
        ["Full analysis latency", "under 200 ms", "Normalise → score → cluster → rank → impact → recommend → narrative"],
        ["Pair comparisons", "≈5,000 candidate pairs before the time filter", "Time-window filter removes the majority"],
        ["Complexity", "O(n²) inside the window, O(n) memory", "Fine to a few thousand events per window; the natural next step is time-bucketing to O(n·k)"],
        ["External dependencies at runtime", "none", "No network call, no database, no model"],
    ],
    widths=[4.6, 5.4, 6.2],
)

h2("15.4  Honest limitations")
bullet("correlation is only as good as the topology it is given. An unknown dependency edge weakens the causal explanation; the system degrades to severity-plus-timing rather than failing.", bold_lead="Topology dependency — ")
bullet("the runbook library is curated for the payment scenario. Extending it to another domain means adding entries, not changing the engine.", bold_lead="Runbook coverage — ")
bullet("the narrative is authored from evidence fields rather than generated by a language model. That is a deliberate trade of expressiveness for guaranteed accuracy, and a language-model layer can be added on top of the stored evidence later.", bold_lead="Narrative surface — ")

page_break()

# ================================================================ 16 ROADMAP
h1("Scalability and future roadmap", "16")

h2("16.1  Scaling the engine")
table(
    ["Bottleneck at 10×–100× volume", "Mitigation"],
    [
        ["Pairwise comparison inside the window", "Bucket events into fixed time slices and compare only adjacent buckets, reducing cost to O(n·k) with a small constant"],
        ["In-memory state", "Move events to a time-series store (ClickHouse or TimescaleDB) and keep only the active window in memory"],
        ["Re-clustering the whole stream on every ingest", "Incremental clustering: assign a new event to an existing cluster when a link fires, and merge clusters lazily"],
        ["Single-process API", "Stateless analysis workers behind a queue; incidents in a shared store; horizontal scale per source"],
        ["Topology drift", "Derive the dependency graph automatically from traces (service A appears as a span parent of B), and diff it against the declared registry"],
    ],
    widths=[6.4, 9.8],
)

h2("16.2  Feature roadmap, in the order it would actually deliver value")
table(
    ["Priority", "Feature", "Value"],
    [
        ["1", "Live connectors (Prometheus, Loki, PagerDuty, OpenTelemetry)", "Removes the file-upload step and makes the system deployable on day one"],
        ["2", "Learned per-service baselines (seasonality, weekday/weekend)", "Makes anomaly scores honest instead of threshold-based"],
        ["3", "Recurrence memory — \"this signature has occurred 11 times, always disk pressure\"", "Turns diagnosis into institutional knowledge"],
        ["4", "ServiceNow / Jira integration with auto-created incident tickets carrying the report", "Removes manual transcription during an outage"],
        ["5", "Predictive warning from leading indicators before user impact", "Moves the platform from reactive to anticipatory"],
        ["6", "Language-model narrative on top of the stored evidence fields", "More fluent summaries with no loss of grounding"],
        ["7", "Multi-tenant topology registry per business unit", "One deployment across an organisation"],
    ],
    widths=[1.8, 7.4, 7.0],
)

h2("16.3  Business value")
bullet("one incident instead of twelve, so the first five minutes of an outage go to fixing rather than triaging.", bold_lead="Faster MTTR — ")
bullet("the platform can state that 420,000 users and ₹76,860 were exposed within seconds of detection, instead of estimating it on a bridge call.", bold_lead="Quantified impact — ")
bullet("unrelated alerts are excluded with reasons, so responders stop investigating the notification backlog during a database outage.", bold_lead="Less alert fatigue — ")
bullet("every diagnosis is a timestamped artefact with prevention steps, which is what turns a review into a permanent fix.", bold_lead="Compounding knowledge — ")

page_break()

# ================================================================ 17 WHY
h1("Why this solution stands out", "17")

h2("17.1  Against the marking criteria")
table(
    ["Criterion", "How this solution answers it"],
    [
        ["Problem clarity", "The statement's own scenario is implemented exactly, with a stated success criterion for each of the seven required features"],
        ["Technical depth", "A real multi-signal correlation model with a documented semantic guard, a five-signal root-cause ranker with explicit penalties, and a topology-driven impact analysis"],
        ["Working prototype", "Runs offline in one command; 7 dashboard views, 11 REST endpoints, four input formats, JSON report export"],
        ["Explainability", "Every displayed number maps to a named formula; rejected alternatives are justified, not hidden; suppressed noise is counted and auditable"],
        ["Real-world usability", "Produces the artefacts an on-call rotation actually uses: one incident, one diagnosis, one ranked plan, one exportable report"],
        ["Scalability", "Bottlenecks named with concrete mitigations; roadmap ordered by value rather than by novelty"],
    ],
    widths=[3.6, 12.6],
)

h2("17.2  The three things worth remembering")
h3("It collapses the alert storm without merging everything")
para("The semantic guard — time proximity can never merge two services on its own — is the single design "
     "decision that separates a credible correlator from an impressive-looking one. It is also directly "
     "demonstrable: the notification backlog arrives inside the window and is still excluded.")

h3("It shows its work")
para("Score components, metric ratios against baseline, hop distances, rejected alternatives and the "
     "revenue arithmetic are all on screen. An on-call engineer who disagrees can see exactly where to "
     "disagree, which is what earns trust in a diagnostic tool.")

h3("It converts diagnosis into an ordered plan")
para("The output is not a probability. It is a ranked list of actions with effort, ETA and risk, plus the "
     "two structural fixes — separate the write-ahead log, put a quota on the connection pool — that "
     "prevent the same cascade from recurring. That is the difference between monitoring and incident "
     "intelligence.")

page_break()

# ================================================================ APPENDIX A
h1("Appendix A — API reference", "A")

table(
    ["Method", "Endpoint", "Purpose", "Returns"],
    [
        ["GET", "/", "Dashboard", "Single-page application"],
        ["GET", "/api/state", "Everything the UI needs in one call", "Topology, incidents, events, summary"],
        ["GET", "/api/incidents", "List of correlated incidents", "Incident array with severity and confidence"],
        ["GET", "/api/incidents/{id}", "One incident in full", "Root causes, impact, timeline, recommendations, events"],
        ["GET", "/api/incidents/{id}/report", "The incident report artefact", "Machine-readable JSON report (see below)"],
        ["POST", "/api/ingest/events", "Push structured events", "Accepted count, updated summary"],
        ["POST", "/api/ingest/simulate", "Generate the challenge burst", "Accepted count, updated summary"],
        ["POST", "/api/ingest/upload", "Upload a log file", "Parsed format, accepted count, updated summary"],
        ["GET", "/api/sample", "Download a sample CSV log", "text/csv attachment"],
        ["GET", "/api/health", "Liveness and counters", "Event and incident counts"],
        ["GET", "/docs", "Interactive OpenAPI documentation", "Swagger UI"],
    ],
    widths=[1.4, 4.2, 5.0, 5.6],
)

h2("A.1  Report schema")
code_block([
    "GET /api/incidents/INC-112/report",
    "{",
    '  "report_id":    "INC-112",',
    '  "generated_at": "2025-03-14T10:02:00+00:00",',
    '  "title":        "Database Host (VM) degradation propagating to 8 services",',
    '  "severity":     "critical",',
    '  "confidence":   0.938,',
    '  "summary":      "Between 10:02:00 and 10:11:37 UTC, 85 events from 4 sources ...",',
    '  "root_cause":   { "service": "db-host", "score": 0.975, "evidence": [ ... ] },',
    '  "alternatives": [ { "service": "db-proxy", "score": 0.803, "why_rejected": "..." } ],',
    '  "impact":       { "users_exposed": 420000, "revenue_exposure_inr": 76860, ... },',
    '  "timeline":     [ ... ],',
    '  "recommendations": [ ... ],',
    '  "recovery_playbook": [ ... ]',
    "}",
])

page_break()
# ================================================================ APPENDIX B
h1("Appendix B — supported input formats and how to run", "B")

h2("B.1  Running the prototype")
code_block([
    "cd jarvis",
    "pip install -r requirements.txt          # fastapi, uvicorn, python-multipart",
    "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
    "",
    "# then open http://localhost:8000",
])

h2("B.2  Accepted upload formats")
table(
    ["Format", "Example", "Notes"],
    [
        ["CSV", "timestamp,level,service,message,value", "Header names are matched case-insensitively; value column optional"],
        ["JSON array", "[ {\"timestamp\": \"...\", \"service\": \"...\", \"message\": \"...\"} ]", "Any of timestamp/time/ts/@timestamp, message/msg/log, level/severity are accepted"],
        ["JSON lines", "{\"ts\":\"...\", ...} per line", "Standard for exported log streams"],
        ["Plain text", "2025-03-14 10:02:14 ERROR db-host postgres: could not write to file ...", "Timestamp, level, service and message parsed by pattern; severity inferred when missing"],
    ],
    widths=[2.6, 7.4, 6.2],
)

h2("B.3  Project layout")
code_block([
    "jarvis/",
    "  app/",
    "    main.py         FastAPI app: ingest, analyse, report, dashboard routes",
    "    engine.py       six-stage engine: normalise, score, cluster, rank, impact, recommend",
    "    topology.py     service registry, dependency graph, blast radius, BFS paths",
    "    scenario.py     deterministic simulator + CSV/JSON/JSONL/text log parser",
    "    static/",
    "      index.html    the entire dashboard (inline CSS + JS + SVG)",
    "  samples/",
    "    jarvis_sample_events.csv",
    "  docs/             architecture diagram, screenshots, this document",
    "  requirements.txt",
])

page_break()
# ================================================================ APPENDIX C
h1("Appendix C — judge Q&A preparation", "C")

qa = [
    ("Why rule-based rather than machine learning?",
     "Because the failure mode of an unexplained model in incident response is worse than the failure mode "
     "of a simple rule: an on-call engineer cannot act on a number they cannot audit. The rule engine is "
     "also deterministic, which means the demonstration is honest — the same input always produces the same "
     "diagnosis. The architecture separates per-signal scores precisely so a learned layer can be added "
     "later without rewriting anything."),
    ("Isn't the topology hard-coded?",
     "The topology is declared data, not logic. It lives in one registry file with fourteen entries for the "
     "payment scenario and is the same artefact a real deployment would load from a service catalogue. "
     "Uploading logs from services not in the registry still works — they simply score zero on topology "
     "affinity, and the system falls back to timing, traces and patterns."),
    ("How do you know the root cause is right?",
     "Three independent checks. It ranks first on the model; it is the earliest signal in the incident "
     "(earliness 1.00); and it is structurally upstream of everything else, explaining 90.6% of the events. "
     "The scenario also carries hidden ground-truth markers that the engine never reads, and the output "
     "matches them exactly."),
    ("What if two services are equally likely?",
     "The system does not fabricate a single answer. Candidates are ranked with their full score "
     "breakdown, and confidence drops — a contested cluster reports in the sixties rather than the "
     "nineties. Both candidates are shown with the evidence for each, because presenting two credible "
     "hypotheses is more useful than hiding one."),
    ("Does it work with our data?",
     "That is what the upload button is for. Bring a CSV, JSON, JSONL or plain-text log export; the parser "
     "handles six timestamp formats and infers severity when the file has no severity column. There is "
     "also a sample file in the repository so the parser can be tested on stage in ten seconds."),
    ("How does this scale beyond a demo?",
     "The current bottlenecks are named and each has a concrete mitigation: time-bucketing to reduce "
     "pairwise comparison, incremental clustering instead of re-clustering per ingest, a time-series store "
     "for history, and stateless workers behind a queue. The ranking model itself is O(candidates), which "
     "stays small no matter how many events arrive."),
    ("What is genuinely novel here?",
     "Three things that monitoring tools commonly get wrong: the semantic guard that stops time proximity "
     "from merging unrelated services, the explicit rejection reasoning that tells a responder why the "
     "runner-up lost, and coherence between impact and recommendation — the plan addresses the amplifier "
     "(the connection pool) as well as the root cause, because the incident showed that one slow disk "
     "becoming a platform outage required both."),
]
for q, a in qa:
    h3("Q.  " + q)
    para(a, after=8)

# ---------------------------------------------------------------- save
out = os.environ.get("JARVIS_OUT", "/home/user/JARVIS_Solution_Problem_Statement_1.docx")
D.save(out)
print("saved")
