---
name: build-standards-register
description: Reads a dump of client/project documents (contract, Employer's Requirements, planning documents, GI reports, FRA, drainage calculations, specifications, and similar) and produces a standards register -- every code/standard/guidance document actually cited in the documents, cross-referenced against this repo's own baseline of standards already expected per discipline, with anything unusual, unexpected, or out-of-place flagged for review. Use when the user provides a set of project documents and asks for a standards register, a code compliance check, or wants "odd"/non-standard/unusual referenced standards identified.
---

# Build standards register

Reads a set of project documents and produces a standards register: every
standard, code, or guidance document actually cited across them, checked
against what's normal for this portfolio, with anything unusual flagged for
a competent engineer to review -- not resolved automatically.

**The governing rule, same as every other skill in this repo: never guess.**
This register reports what the documents actually cite, not what a project
of this type would typically need. A standard doesn't belong in the
register because the discipline "should" reference it -- only because a
specific document actually names it. Equally, don't infer what a vague
reference ("the relevant British Standard") probably means -- record it as
stated, flagged as unidentified, rather than resolving it to a specific
code number yourself.

## Step 1 -- read the live baseline (always, every run)

This repo already declares the standards expected per discipline, spread
across `basis_of_design/civils.py`, `structural.py`, `electrical_lv.py`,
`electrical_hv.py`, and `mechanical_piping.py` -- each `BasisOfDesignSection`
carries a `standards: list[Standard]` (see `basis_of_design/core.py` for the
`Standard` model: `code`, `title`, `national_annex`, `notes`). Read all five
files fresh, every run -- this is the comparison baseline the rest of this
skill depends on, and it grows as more BoD sections get built out, so a
remembered list from a previous run (including any example in this file)
will be stale. A quick way to pull just the citations:

```bash
grep -hoE 'Standard\(code="[^"]+"' basis_of_design/*.py | sort -u
```

but read the actual `Standard(...)` entries in context (not just the grep
output) where you need `title`/`notes` for a specific code, and note which
*discipline file* each one came from -- a standard cited in a document
section that doesn't match the discipline it's normally associated with in
this baseline (e.g. a piping code appearing in an electrical specification)
is itself worth flagging, not just codes missing from the baseline entirely.

## Step 2 -- read every document, extract every citation

Use the `Read` tool -- it handles PDFs and images directly. Work through
the whole document set: contract, Employer's Requirements (ERs),
specifications, planning conditions/decision notices, GI reports, Flood
Risk Assessments (FRA), drainage calculations, and anything else supplied.
Extract every standard/code/guidance document actually named -- British
Standards (BS/BS EN/BS EN ISO), Eurocodes, ASME/API/ISO/IEEE/NFPA codes,
statutory instruments and regulations, CIRIA/HSG/DMRB-style guidance
documents, company or client-specific standards, anything cited by name or
number.

For each citation, record:
- **The exact code/reference as stated** -- don't normalise or "correct" a
  citation that looks like a typo or an old designation; record it as
  written and note the discrepancy separately (see Step 3) rather than
  silently fixing it.
- **Which document and where** -- document name/reference and a page,
  clause, or section number if the source makes that identifiable, so a
  reviewer can go straight to it.
- **What it's cited for**, if the document says (e.g. "designed in
  accordance with BS EN 1997-1" vs. a bare reference in a document list) --
  a citation with real context is more useful for classification than a
  bare code number in a reference list.

Skip generic/non-normative mentions that don't actually specify a
governing standard for the work (e.g. a document's own title block, a
copyright notice, an unrelated example in explanatory text).

## Step 3 -- classify each citation against the baseline

For each extracted citation, compare against Step 1's baseline and
classify:

- **Matches a baseline entry (same code)** -- "Expected", the standard
  category, and its discipline. No further flag needed.
- **Not in the baseline at all** -- "Not in portfolio baseline." This does
  NOT mean wrong or invalid -- it may be entirely legitimate and simply not
  something this portfolio's disciplines have needed to cite before (a
  project-specific or client-specific requirement, a discipline this
  portfolio hasn't built out yet, a genuinely project-specific standard).
  Flag it for a competent engineer to confirm relevance/correctness rather
  than presenting it as an error.
- **Cited in an unexpected discipline context** -- e.g. a mechanical piping
  code appearing in what's otherwise an electrical specification section.
  Flag for a second look; this is often either a genuine multi-discipline
  requirement or a copy-paste artefact from a template document, and only
  the engineer reviewing the actual context can tell which.
- **A superseded/withdrawn edition** -- ONLY flag this if you have real,
  specific confidence a cited edition/year has been superseded (e.g. the
  document cites a specific year of a standard you know has since been
  revised with a materially different current edition). If you're not
  genuinely sure, do not guess at supersession -- record the citation as
  stated and leave currency-checking to the engineer. A false "this is
  outdated" flag is exactly the kind of invented confidence this skill
  exists to avoid.
- **Ambiguous/unidentifiable reference** -- e.g. "the relevant Eurocode",
  "current British Standard", an abbreviation matching more than one
  plausible standard. Record it as stated, flagged as needing the
  engineer's own identification -- don't guess which specific standard was
  meant.

## Step 4 -- write the standards register

A markdown table, grouped by discipline (using the same discipline names as
`basis_of_design/`: Geotechnical, Structural, Civils, Electrical (LV),
Electrical (HV), Mechanical Piping) plus an "Unclassified / cross-
discipline" group for anything that doesn't clearly sit in one of those.
Columns:

| Standard/Code | Title (if stated) | Cited in | Status | Note |
|---|---|---|---|---|

- **Status** is one of: `Expected` / `Not in portfolio baseline` /
  `Unexpected discipline context` / `Possibly superseded` /
  `Unidentified reference`.
- **Note** carries the specific reason for anything other than `Expected`
  -- e.g. "not previously cited in this portfolio's Electrical (LV) BoD",
  or "cited in Section 4.2 of the Employer's Requirements, alongside piping
  standards, in what is otherwise a structural specification clause".

Save the register somewhere the user can find it -- ask where they'd like
it if not obvious, otherwise use the project's scratchpad location if one
is configured, or the current working directory with a clear name like
`standards_register.md`.

## Step 5 -- summarise what needs review

Above or alongside the full table, a short summary: total standards found,
how many matched the baseline cleanly, and an explicit, short list of
everything flagged (`Not in portfolio baseline` / `Unexpected discipline
context` / `Possibly superseded` / `Unidentified reference`) with a
one-line reason each -- this is the part a reviewer actually needs to act
on; the full table is the audit trail behind it.

## Scope

Any project document set is in scope -- this isn't limited by discipline
the way `fill-calc-inputs-from-drawings` is. Out of scope: judging whether
a cited standard is the *correct* one for the work (that's an engineering
review decision, not an extraction task), and resolving ambiguous/
unidentified references to a specific standard yourself -- both are Step 3
"flag, don't guess" cases, not things this skill decides on its own.
