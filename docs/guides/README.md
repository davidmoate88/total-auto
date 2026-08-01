# Working guides

This folder is different from the rest of `docs/`. `ARCHITECTURE.md` and
`ROADMAP.md` explain how the *software* is put together and what's been
built; `HANDOFF.md` is for picking the build back up in Claude Code. None of
those tell you how to actually sit down and use this tool to do the job —
work through a real project's basis of design, discipline by discipline,
without missing something or waiting on the wrong thing.

That's what this folder is for. Each guide is written for two readers at
once: **you**, running a real project through this and wanting the fastest
practical path through it, and **a colleague or junior engineer** picking
this up who also needs to understand *why* it's built this way, not just
which command to run. Where those two needs pull in different directions,
the guide explains the reasoning briefly rather than skipping it — a
one-line "why" is cheap and saves the junior reader from either blindly
trusting an illustrative value or blindly distrusting a genuinely
standard one.

## What order to actually read these in

This isn't arbitrary — it's the literal output of `integration/graph.py`,
which derives it from the `Interface` entries the disciplines already
declare (see `docs/ARCHITECTURE.md`'s "Process flow" section for the full
derivation). Don't reinvent a sequencing opinion on a real project; use this
one, and use `integration.process_state` to check it against where you
actually are.

1. **[`00_geotechnical.md`](00_geotechnical.md)** — always first. Nothing in
   this repo depends on anything else here depending on it; it's the one
   true starting point, and it's also the only discipline with a real,
   working calculation behind it rather than a basis-of-design skeleton.
2. **[`01_structural.md`](01_structural.md)** — depends only on
   geotechnical (plus an external temporary works contractor). Nothing
   loops back into it. Sequence it right after geotechnical and develop it
   largely on its own from there.
3. **[`02_civils.md`](02_civils.md)**, **[`02_electrical_lv.md`](02_electrical_lv.md)**,
   **[`02_electrical_hv.md`](02_electrical_hv.md)**, **[`02_mechanical_piping.md`](02_mechanical_piping.md)**
   — all share the "02" prefix on purpose: these four are a genuine
   mutually-dependent cluster (utilities coordination, hazardous area
   classification, the LV/HV transformer boundary, and buried pipe routing
   all reference each other and loop back round). There is no valid strict
   order among them. Read all four before starting any of them, then work
   the four concurrently, using the open items register (below) to see
   what's actually blocking what at any given moment — not a fixed
   hand-off sequence.

## The two tools that keep this from becoming five disconnected documents

- **The open items register** (`integration/open_items.py`,
  `python3 -m integration.open_items`) — every "to be confirmed from X"
  scattered across all five disciplines' criteria and assumptions, in one
  list (53 as of the last detail pass). This is your actual to-do list once
  you start a real project — work through it, not through re-reading every
  section looking for gaps.
- **The combined master document** (`integration/master_document.py`,
  `python3 -m integration.master_document`) — the process-flow narrative,
  the dependency diagram, the open items register, and all five
  disciplines' full output, stitched into one document. Regenerate this
  whenever you want the single current-state view of a project rather than
  five separate discipline documents.

## A note on the illustrative values

Every discipline guide repeats this because it matters every time, not just
once: the design criteria populated in each `basis_of_design/<discipline>.py`
module (freeboard, deflection limits, hydrotest factors, and so on) are
starting points from common practice, not verified project- or
client-specific figures, and not independently checked against the current
purchased standard texts in this environment. Treat the skeleton as a
credible checklist to confirm and override per project — see each guide's
"Adapting the skeleton for a real project" section for how that actually
works in code.
