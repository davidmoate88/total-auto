# portfolio/

Project portfolio tracking domain — status: **data model only, no logic yet**.

`models.py` defines the shape of a `Project` (cost, programme, constraints, risks,
buildability notes, contacts, feasibility status) and a `Portfolio` (a collection of
projects). This is deliberately just a validated data contract — no import/export,
no dashboard, no cost rollups or risk scoring.

## What's next (see docs/ROADMAP.md Milestone 3)

- Import from spreadsheet trackers (xlsx/csv) into `Portfolio`.
- Portfolio-level views/aggregations (total committed cost, open high-severity risks
  across all live projects, upcoming programme milestones).
- Integration point: `BuildabilityNote.related_calc_reference` is a placeholder for
  linking a project to a specific calc module report (e.g. a bearing resistance
  calculation for that project's foundations) — see docs/ARCHITECTURE.md.
- A Streamlit tab (or separate small app) for viewing/editing a `Portfolio`.
