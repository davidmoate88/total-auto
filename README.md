# total-auto

Automation toolkit for running a portfolio-design / head-of-engineering-design role:
engineering calculations across disciplines, project portfolio tracking (cost, time,
buildability, constraints, risk, feasibility), and information flow (emails, meeting
minutes, actions, reminders).

This repo is being built incrementally. See `docs/ARCHITECTURE.md` for the domain map
(what's built vs. scaffolded), `docs/ROADMAP.md` for the full vision and build order,
and **`docs/HANDOFF.md` first if you're picking this up in Claude Code** — it has the
exact steps and open items from where this was left off.

## Status

**Milestone 1 (current):** Geotechnical spread foundation bearing resistance,
to **EN 1997-1 (Eurocode 7) Annex D, UK National Annex, Design Approach 1** — built
inside a small extensible framework so future disciplines (structural, civil, etc.)
and eventually the wider portfolio/comms tooling slot in the same way. In front of it
sits a **ground model interpreter**: paste SPT/CPT/lab site investigation data per
soil stratum and it derives characteristic design parameters (phi', cu, unit weight)
using established correlations, then hands them straight to the bearing resistance calc.

**All calculations in this repo are intended to be Eurocode-compliant.** Read the
caveat in `calcs/geotechnical/bearing_capacity.py`'s module docstring before relying
on any of this for a real design — the formulae and partial factors were built from
standard geotechnical literature/training knowledge, not by reading the purchased
BS EN 1997-1 standard text directly, and should be checked against the current
standard and National Annex before use.

**Milestone 1a (current):** working discipline-by-discipline through a "basis of
design" (BoD) — the document stating scope, standards, criteria, and interfaces for
a discipline, distinct from a `calcs/` module that performs one specific calculation.
Civils and structural are both built as 9-section skeletons
(`basis_of_design/civils.py`, `basis_of_design/structural.py` — the latter scoped to
industrial access steelwork: platforms, walkways, stairs, ladders, handrails, spanning
both the structural Eurocodes and the machinery/access safety standards). LV
electrical, HV electrical, and mechanical piping are next, in that agreed order. See
`docs/examples/` for a generated look at each discipline's current output.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the web UI
streamlit run app.py

# Run the calc engine directly (no UI)
python3 -m calcs.geotechnical.bearing_capacity

# Run tests
pytest
```

## Project layout

```
total-auto/
├── app.py                          # Streamlit UI — ground model interpreter + bearing calc
├── core/
│   ├── calc_base.py                # Shared interfaces: CalcInput, CalcResult, registry
│   └── report.py                   # Turns a CalcResult into a review-ready markdown sheet
├── calcs/
│   ├── registry.py                 # Central list of registered calc modules
│   ├── geotechnical/                # BUILT — see below
│   │   ├── bearing_capacity.py     # EN 1997-1 Annex D bearing resistance, UK NA DA1
│   │   └── interpretation/
│   │       ├── models.py           # SPT/CPT/lab test/stratum/site data models
│   │       ├── correlations.py     # SPT/CPT -> phi'/cu empirical correlations
│   │       ├── ground_model.py     # Pools data per stratum -> characteristic design params
│   │       └── text_input.py       # Lenient line-based paste parser (not free-form NLP)
│   ├── structural/                  # PLACEHOLDER — README + pattern only, no modules yet
│   └── civil/                       # PLACEHOLDER — README + pattern only, no modules yet
├── basis_of_design/                  # Discipline basis-of-design shape + skeletons
│   ├── core.py                     # Shared BasisOfDesignSection shape
│   ├── render.py                   # Renders any discipline's sections to markdown
│   ├── civils.py                   # BUILT — 9-section civils skeleton
│   └── structural.py               # BUILT — 9-section skeleton, scoped to industrial access steelwork
├── portfolio/                       # DATA MODEL ONLY — Project/Portfolio contract, no logic
├── comms/
│   ├── meeting_minutes/             # DATA MODEL + interface stub (extract_minutes())
│   └── email_triage/                # DATA MODEL + interface stub (triage_inbox())
├── tests/
│   ├── test_bearing_capacity.py    # Validates EC7 Annex D factors/DA1 partial factors
│   ├── test_correlations.py        # Validates SPT/CPT correlation functions
│   ├── test_ground_model.py        # Validates multi-layer overburden + parameter pooling
│   └── test_text_input.py          # Validates the paste-format parser
└── docs/
    ├── ARCHITECTURE.md             # Domain map, design principles, integration points
    ├── ROADMAP.md                  # Full vision and build order
    └── HANDOFF.md                  # Start here if continuing in Claude Code
```

## Design principles

- **One calc = one self-contained module.** Each calc module exposes a pydantic input
  model, a `calculate()` function, and a result model with every intermediate term kept
  (not just the final answer) — because engineering output needs to be checkable, not
  just correct.
- **Every result can produce a review sheet.** `core/report.py` turns any calc result
  into a markdown calculation sheet (inputs, method, working, result, references) —
  the same shape a checker/approver would expect on a real project.
- **The UI is a thin layer.** `app.py` just discovers registered calc modules and
  renders a form + result for whichever one is selected. Adding a new discipline means
  adding a new module + registering it — the app and report generator don't change.

## Continuing this project

This was started in a Cowork session without direct access to the `total-auto` GitHub
repo (private repo, no network path from that sandbox). To continue in Claude Code:

1. Get this code onto your machine — either pull it via the Claude desktop app's
   device bridge from this session, or have it delivered as files/zip.
2. `git remote add origin git@github.com:davidmoate88/total-auto.git`
3. If the GitHub repo is empty: `git push -u origin main`.
   If it already has content: pull first and merge/rebase this history in.
4. From there, everything works as an ordinary local git repo — Claude Code, your own
   editor, or a future Cowork session can all keep working on it.
