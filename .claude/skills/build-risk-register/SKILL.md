---
name: build-risk-register
description: Reads a dump of client/project documents (contract, Employer's Requirements, planning documents, GI reports, FRA, drainage calculations, and similar) and produces a project risk register as a new .xlsx file matching a user-supplied template's exact column structure, dropdowns, and formulas -- seeded from a reusable library of standard BESS-project risks plus new project-specific risks found in the documents. Use when the user provides a set of project documents and a risk register template (or asks to build/update a risk register) and wants a populated register produced.
---

# Build risk register

Reads a set of project documents and a risk register template (an `.xlsx`
file, supplied by the user each run -- this skill does not invent its own
column format) and produces a new `.xlsx` risk register matching that
template exactly, seeded from a reusable library of standard risks plus
whatever new project-specific risks the documents themselves raise.

**The governing rule, same as every other skill in this repo, with one
explicit, bounded exception for this skill specifically:** a risk's
*existence* in the register must trace back to either (a) this skill's own
bundled risk library (`reference_risk_library.json`, see Step 1 -- itself
extracted from a real, previously-delivered project register, not invented)
or (b) something a specific project document actually states. Never invent
a risk from nothing. **Impact/Probability *scores*, however, are always
proposed, never asserted as settled** -- risk scoring is a team/workshop
judgement in real practice, not a drafting decision, so every score this
skill writes is explicitly flagged as a draft for review (Step 4), whether
it came from library precedent or from a document.

## Step 1 -- read the live template AND the bundled risk library

Two different sources, read differently:

- **The template** -- the user will supply an `.xlsx` file each run (their
  current master risk register, which may evolve over time). Read its
  *live* structure fresh, every run -- don't assume it matches the shape
  described below, which was true when this skill was written against one
  specific template:
  - The header row and every column's exact meaning (in the reference
    template this is row 20, columns A-M: `Risk` / `Main Risk Category` /
    `What's Affected Primary` / `What's Affected Secondary` / `Impact` /
    `Probability` / `Priority` (formula) / `Impact Explained` /
    `Mitigation Measures` / `Revised Probability` / `Revised Priority`
    (formula) / `Mitigated?` / a free-text comments column).
  - Every dropdown-constrained column's actual allowed values -- in the
    reference template these live on a second sheet (`Sheet2`): Main Risk
    Category, What's Affected (Primary/Secondary), and Mitigated? each pull
    from a named list there. Read the live list, don't assume the category
    set below is current or complete.
  - Which columns are formulas (don't overwrite the formula pattern -- read
    an existing populated row's formula, e.g. `=E{row}*F{row}` for
    Priority, and replicate that *pattern* at the new row number, exactly
    the "match its conventions" rule the `anthropic-skills:xlsx` skill
    itself states).
  - The next genuinely empty row to start writing at -- note that template
    files are often pre-built with formula cells (Priority/Revised
    Priority) already filled in far beyond the last row with actual risk
    content, ready for new data; the first row with an *empty* `Risk`
    (column A) cell is the one to use, not the first row with no formula.
  - Any pre-existing quirk in the file's own summary/dashboard formulas
    (e.g. a `COUNTIF` range that shifts by one row per line, a leftover
    fill-down error) -- note it, don't silently "fix" it; that's the
    template owner's call, and fixing it without being asked risks
    changing numbers the user already relies on.
- **`reference_risk_library.json`**, bundled in this skill's own directory
  -- a reusable starter library of standard BESS-project risks, extracted
  once from a real, previously-delivered project register (Newport BESS,
  May 2025) and classified into three tiers:
  - **`tier1_standard`** -- risks that recur on essentially any UK BESS
    project regardless of site specifics (CDM compliance, general
    construction/fire HSE, security, weather, grid connection compliance
    checks, battery warranty/storage conditions, and similar). Reuse these
    close to verbatim, adapting only entity names (contractor, DNO,
    supplier) to the new project if the source text names one specific to
    the original project.
  - **`tier2_pattern`** -- risks that are a recurring *type* on BESS
    projects, but whose original wording ties to the source project's own
    specifics (a named planning condition, a named DNO process, a named
    flood zone designation, a named supplier). Each entry carries an
    `adaptation_note` explaining what to re-derive from the *new* project's
    own documents -- use the pattern, not the specific wording.
  - **`tier3_dated`** -- time/event-specific risks (a pandemic, a specific
    geopolitical conflict) that were live concerns when the source register
    was built but are dated now. Exclude these by default; only include an
    equivalent, generalised version if the new project's own documents
    raise an active concern of that kind (e.g. a stated supply-chain
    disruption), and don't name the original specific event when you do.

  This library will go stale as it is -- if the user delivers more project
  registers over time, it's worth periodically re-extracting and
  re-classifying it (same process as this file's own construction), but
  that's a separate, occasional maintenance task, not something to redo on
  every run.

## Step 2 -- read every document

Use the `Read` tool -- it handles PDFs and images directly. Work through
the whole document set: contract, Employer's Requirements (ERs),
specifications, planning documents, GI reports, Flood Risk Assessments
(FRA), drainage calculations, and anything else supplied. This is the same
document set `build-standards-register`, `build-constraints-register`, and
`synthesize-foundation-levels-options` read -- if any of those have already
been run against this same document set, their output (constraints
register, standards register, foundation/levels synthesis, and its own
GI-derived flags) is a good cross-check for risks: a flagged constraint or
open item is very often also a risk register entry.

## Step 3 -- build the row set

For each row you're proposing to add:

1. **Start from the library where a real match exists.** Walk
   `tier1_standard` and `tier2_pattern` and ask, for each: does this
   project's situation genuinely match (a leasehold Superior Landlord
   clause only applies if the new project is actually leasehold; a
   non-firm connection risk only applies if the new project's own
   connection offer is non-firm)? Include `tier1_standard` matches with
   entity names adapted; include `tier2_pattern` matches with the
   *specifics* re-derived from what the new project's documents actually
   say, using the entry's own `adaptation_note` as the guide -- not the
   original wording.
2. **Add genuinely new risks the documents raise** that have no library
   precedent -- e.g. a specific ground contamination finding in the new
   project's own GI report, a specific unusual planning condition, a
   specific clause in the new project's contract. Each of these must be
   traceable to a specific document and location, same discipline as every
   other skill in this repo.
3. **Skip a library entry that doesn't apply** -- don't include a
   `tier1_standard` risk just because it's in the library if the new
   project's documents actively contradict it (e.g. don't include
   "Superior Landlord Consent" if the new project's documents show freehold
   ownership).

For every row, populate: Risk (short title), Main Risk Category (from the
template's own live dropdown list -- Step 1), What's Affected Primary/
Secondary (same), Impact Explained (the actual risk description -- for a
library-sourced row, adapted; for a document-sourced row, close to the
source wording), Mitigation Measures (library-sourced: adapted; document-
sourced: draft something reasonable from what the documents themselves
already propose as controls, e.g. a contract clause already assigning the
risk to a contractor -- don't invent a mitigation strategy the documents
give no basis for).

## Step 4 -- propose Impact/Probability, flagged as draft

For every row (library-sourced or new):

- **Library-sourced (`tier1_standard`/`tier2_pattern`)**: propose the
  library entry's own Impact/Probability as a starting point -- it's real
  precedent from a comparable project, not invented, but still just a
  starting point for a different project's own circumstances.
- **New, document-sourced**: propose a score using the same 1-5 scale the
  template uses, with your reasoning grounded in what the documents state
  about severity/likelihood where they say anything relevant -- otherwise
  a mid-range placeholder, clearly flagged as needing a first assessment
  rather than a refinement of one.
- **Every proposed score gets flagged**, using the template's own free-text
  comments column (in the reference template, "Clarke Energy Comments") --
  prefix with something like `[DRAFT -- Impact/Probability proposed by
  Claude, confirm at risk workshop]`, plus a one-line reason for a
  document-sourced score. This is a deliberate reuse of an existing column
  rather than adding a new one, matching the "match its conventions
  exactly" rule -- don't add columns the template doesn't have.

Leave `Revised Probability`/`Revised Priority`/`Mitigated?` blank for every
new row -- these describe the state *after* mitigation has actually been
implemented and assessed, which hasn't happened yet for a risk this run
just identified.

## Step 5 -- write the output file

Load the `anthropic-skills:xlsx` skill for the actual write mechanics
(openpyxl gotchas, formula-writing rules, the mandatory `recalc.py` pass)
-- don't reinvent that guidance here. In summary for this specific task:

- Work on a **copy** of the user's template file, never the original.
- Write new rows starting at the first genuinely empty `Risk` (column A)
  row identified in Step 1.
- Write `Priority`/`Revised Priority` as formula strings matching the
  existing pattern at that row number (e.g. `=E87*F87`), not computed
  values -- the sheet must recalculate if a score changes later.
- Match the existing rows' font/formatting by copying cell style from an
  adjacent populated row, not the library defaults.
- Run `recalc.py` before calling this done -- a clean recalc proves the new
  formulas evaluate, not that the content is right, but a failing recalc
  means something is definitely wrong.

Save the file somewhere the user can find it -- ask where they'd like it
if not obvious, otherwise use the project's scratchpad location if one is
configured, or the current working directory, with a clear name
distinguishing it from the original template (e.g.
`<project>_risk_register.xlsx`, never overwriting the source file).

## Step 6 -- write extraction/decision notes alongside the file

Same audit-trail idea as every other skill in this repo:

- **Every row added**, with its source: library tier 1/2 (name the
  original library entry) or a specific project document (name it and
  where).
- **Every library entry considered but excluded**, and why (didn't apply
  to this project's circumstances).
- **Every proposed Impact/Probability score**, restated plainly (not just
  buried in the comments column) so a reviewer can scan the list of what
  needs workshop confirmation without opening the spreadsheet.
- Anything from the source documents that reads like a risk but that you
  weren't confident enough to add as its own row (an ambiguous mention, a
  risk implied but not stated outright) -- flagged for the engineer to
  judge, not silently dropped.

## Step 7 -- tell the user what to do next

Point them at the output file and the notes. Be explicit that every
Impact/Probability score is a draft proposal, not a settled assessment --
the register needs a proper risk review/workshop before the scores (and
therefore the colour-coded Priority column) are relied on for real
prioritisation decisions.

## Scope

Any project document set is in scope. Out of scope: inventing the
template's column structure or dropdown values yourself (always read the
live file, per Step 1) -- and asserting a final, agreed Impact/Probability
score, which this skill deliberately never does (Step 4).
