# total-auto

Automation toolkit for running a portfolio-design / head-of-engineering-design role:
engineering calculations across disciplines, project portfolio tracking (cost, time,
buildability, constraints, risk, feasibility), and information flow (emails, meeting
minutes, actions, reminders).

This repo is being built incrementally. See `docs/ROADMAP.md` for the full vision and
what's built vs. planned.

## Status

**Milestone 1 (current):** Geotechnical bearing capacity calculator (Meyerhof method,
shallow foundations) — the first working calc module, built inside a small extensible
framework so future disciplines (structural, civil, etc.) and eventually the wider
portfolio/comms tooling slot in the same way.

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
├── app.py                          # Streamlit UI — lists and runs calc modules
├── core/
│   ├── calc_base.py                # Shared interfaces: CalcInput, CalcResult, registry
│   └── report.py                   # Turns a CalcResult into a review-ready markdown sheet
├── calcs/
│   └── geotechnical/
│       └── bearing_capacity.py     # Meyerhof shallow foundation bearing capacity
├── tests/
│   └── test_bearing_capacity.py    # Validates factors against standard textbook values
└── docs/
    └── ROADMAP.md                  # Full vision and build order
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
