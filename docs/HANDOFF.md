# Handoff — continuing this project in Claude Code

This project was built in a Cowork session with no network path to GitHub (the
sandbox couldn't reach github.com at all, even for public repos) and no
connected desktop bridge, so it was never pushed to the real `total-auto`
GitHub repo directly. Everything is committed to a local git repo instead,
delivered as a zip + git bundle. This doc is what a fresh Claude Code session
(or you) needs to pick this up with full context.

## Getting the code and history onto your machine

You were sent two files:

- `total-auto.zip` — the working tree only (no git history), useful for a quick
  look or if you just want the files.
- `total-auto.bundle` — a full git bundle, which **does** carry the complete
  commit history. This is the one to actually use for continuing development.

To restore the real repo from the bundle:

```bash
git clone total-auto.bundle total-auto
cd total-auto
git log --oneline   # should show the full commit history, not a single squashed commit
```

## Pushing to the real GitHub repo

The target is `https://github.com/davidmoate88/total-auto` (currently private).

```bash
cd total-auto
git remote add origin git@github.com:davidmoate88/total-auto.git   # or https://... with a token
git push -u origin main
```

If the GitHub repo already has content (e.g. you initialised it with a README
via the GitHub UI), pull first and reconcile:

```bash
git fetch origin
git merge origin/main --allow-unrelated-histories   # or rebase, your call
git push -u origin main
```

## What's actually built vs. scaffolded

Read `docs/ARCHITECTURE.md` for the full map. Short version:

- **Fully built and verified**: `calcs/geotechnical/` — EN 1997-1 Annex D
  bearing resistance (UK NA, DA1) plus the ground model interpreter (SPT/CPT/lab
  data → characteristic design parameters). Every formula was manually verified
  against known reference values via ad-hoc Python scripts (see the commit
  history and `tests/` — the test files exist but couldn't actually be *run*
  in this sandbox; see below).
- **Data model / interface only, no logic**: `portfolio/`, `comms/meeting_minutes/`,
  `comms/email_triage/`. These define the shape of the data (pydantic models)
  and, for the comms modules, a stub function with the intended signature that
  raises `NotImplementedError`. Nothing here is fake — it's an honest
  placeholder for genuinely unbuilt logic.
- **Placeholder only**: `calcs/structural/`, `calcs/civil/` — just a README
  describing the pattern to follow (copy `calcs/geotechnical/bearing_capacity.py`'s
  shape) and the governing code to target.

## Important limitation to know about before you start

**Neither `pytest` nor `streamlit` could be installed in the Cowork sandbox**
(no network egress to PyPI). This means:

- The test files in `tests/` are real, meaningful tests — but they were never
  actually executed with pytest. Every piece of logic they test was instead
  verified with hand-written Python scripts producing the same assertions
  (visible in this session's tool-call history, not committed to the repo).
  **First thing to do in Claude Code: `pip install -r requirements.txt && pytest -v`**
  and fix anything that doesn't pass — there's a real chance of a small
  mismatch between the test file and the manual verification given they were
  written somewhat independently.
- `app.py` (the Streamlit UI) has never been run or visually checked. The
  non-Streamlit logic it calls is fully tested; the UI wiring itself (form
  layout, session state hand-off between the two tabs) is unverified. **Second
  thing to do: `streamlit run app.py` and click through both tabs.**

## Known open items (also in docs/ROADMAP.md)

- The Eurocode 7 Annex D formulae (especially the Ngamma bearing capacity
  factor) were implemented from geotechnical literature/training knowledge, not
  by reading the purchased BS EN 1997-1 standard text directly. Flagged
  prominently in `calcs/geotechnical/bearing_capacity.py`'s docstring — get a
  chartered engineer to check this against the current standard before it's
  used for anything real.
- `text_input.py`'s parser is a lenient structured-paste parser (depth/N-value
  lines etc.), not a free-text/NLP report reader. If you want genuine free-form
  report excerpts handled, that's better done by having an LLM read the excerpt
  and translate it into the paste format, rather than extending the regex parser.

## Suggested next steps, roughly in order

1. Run the test suite for real; fix whatever the sandbox couldn't verify.
2. Run the Streamlit app; fix any UI issues.
3. Get the Annex D formulae checked against the actual standard text.
4. Pick the next calc module (structural is the natural next discipline) or
   start putting logic behind `portfolio/` (spreadsheet import is the most
   valuable first step per docs/ROADMAP.md Milestone 3).
