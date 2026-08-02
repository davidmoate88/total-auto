---
name: fill-calc-inputs-from-drawings
description: Reads engineering source documents (GA drawings, SLDs, load/cable/equipment schedules, or other project data) and produces a JSON file that prefills total-auto's electrical LV/HV calc modules via the app's "Import extracted data" sidebar feature. Use when the user provides drawings/schedules and wants them turned into calc inputs, or asks to "fill in" / "populate" the calculators from a document.
---

# Fill calc inputs from drawings

Reads a GA, SLD, load schedule, cable schedule, or similar source document
and produces a JSON file that prefills total-auto's Streamlit app forms
(via the sidebar "Import extracted data (JSON)" feature in `app.py`) —
scoped to the Electrical (LV) and Electrical (HV) calc modules for now
(see "Scope" below).

**The single rule that matters more than any other in this skill: never
guess.** Every calc module in this repo follows a "flag, don't guess"
discipline — when a value is genuinely uncertain, it's a required direct
input the module refuses to derive, rather than a plausible-looking number
that could be silently wrong. This skill extends that discipline to the
*extraction* step: a value you cannot read with real confidence from the
source document must be **left out of the output JSON entirely**, not
filled with your best guess, not set to `null`, not estimated from a
"typical" figure. An omitted field just means the engineer fills it in
manually in the app, exactly as if this skill had never run for that
field — that's a safe, expected outcome. A wrong number silently prefilled
into a form looks authoritative and is worse than an empty field, because
the reviewer has no reason to double-check it. If you are not sure whether
you're confident enough, you are not confident enough — leave it out.

## Step 1 — get the current schema (always, every run)

Field names, types, and defaults can change as the app evolves. Never rely
on a remembered field list, including any example shown later in this
file — it may be stale by the time you read it. Get the live schema
before doing anything else:

```bash
python3 -m calcs.schema_export --discipline "Electrical (LV)" --discipline "Electrical (HV)"
```

(Run from the repo root, inside the project's virtualenv — see
`docs/HANDOFF.md`/`README.md`'s "Getting started" if the environment isn't
already active.) This prints one JSON object per module, each with a
`fields` map giving every input field's `type`, `required`,
`optional_field`, `default`, and full `description` (the description is
often the most important part — it says exactly which standard table a
value should come from, what units are expected, and what this repo's own
docstring caveats are for that field).

If the user only cares about specific modules or a subset of a discipline,
narrow with `--key <module_key>` (repeatable) — but when in doubt, export
the full LV+HV set and only populate what the source document actually
supports; there's no cost to asking for more schema than you end up using.

## Step 2 — identify and read the source document(s)

The user will point you at one or more files: a GA (General Arrangement)
drawing, an SLD (Single Line Diagram), a load schedule, a cable schedule,
an equipment list, a DNO connection offer, a soil resistivity report, etc.
Use the `Read` tool — it handles PDFs and images directly. Read every
provided document before extracting anything; a value on one sheet is
often only interpretable correctly alongside a legend, a title block, or a
schedule on another sheet or another page of the same PDF.

Note what you're actually looking at:
- **SLDs** are the most directly useful source for electrical LV/HV data:
  transformer nameplate ratings, protective device ratings and settings,
  cable sizes/routes if annotated, earthing arrangement, switchgear
  ratings.
- **GA drawings** are more useful for physical/geometric data: cable
  route lengths, earth grid dimensions, equipment locations — GA drawings
  mix multiple disciplines on one sheet, so most of what's on it won't be
  relevant to the LV/HV electrical modules; that's expected, extract only
  what applies.
- **Schedules/spreadsheets** (load schedules, cable schedules) are
  usually the highest-confidence source, since they're already tabulated
  data rather than something requiring visual interpretation of a drawing.

## Step 3 — map extracted values to fields

For each module in the schema from Step 1, go through its fields one at a
time and ask: *can I point to the specific place in the source
document(s) where this exact value is stated, unambiguously, in
compatible units?*

- **Yes, directly and unambiguously stated** → include it.
- **Implied but not stated** (e.g. you could compute it from two other
  numbers on the drawing) → do NOT include it. Derivation is the calc
  module's job, or the engineer's, not this skill's — this skill transcribes,
  it does not calculate or infer.
- **Stated but with a plausible-sounding "typical" fallback in the
  field's `description`** (many fields have an illustrative default per
  the schema, e.g. a growth margin or correction factor) → still do NOT
  include it just because a default exists. Only include it if the
  *specific project's* source document actually states that project's
  own value. If the source is silent, leave the field out and let the
  app's own default apply.
- **Ambiguous, contradicted between two sheets, illegible, or you're
  genuinely unsure** → do NOT include it. Note it in the extraction notes
  (Step 5) instead.

One field needs special handling: `loads_text` on
`electrical_lv_load_schedule_diversity` is not a single value but a
multi-line pasted format — one load per line, `name, rated_power_kw,
power_factor[, diversity_factor_percent]` (see that field's own
`description` in the schema export for the authoritative format,
including the important caveat that diversity factors depend on the
project's own operational duty and are not read from a fixed table — only
include a per-load diversity factor if the source document actually states
one, and only include a load line at all if you have both power and power
factor for it with real confidence). Build this field only from an
actual load/equipment schedule in the source documents — do not invent
loads that aren't listed, and do not include a load with a rated power but
no power factor by guessing a "typical" one.

Do not attempt to resolve any field marked `"required": true` in the
schema that you can't confidently populate — leave it out just like any
other field. A module simply won't have that field prefilled; the app
handles a partially-imported module the same as a module nobody has
touched yet.

## Step 4 — write the output JSON

One JSON object, keyed by module key exactly as returned by the schema
export, each value an object of `{field_name: value}` pairs for only the
fields you populated in Step 3. Omit any module entirely if you found
nothing for it — don't include an empty `{}` for it.

```json
{
  "electrical_lv_load_schedule_diversity": {
    "loads_text": "Duty pump, 15, 0.85, 100\nStandby pump, 15, 0.85, 0\nLighting, 5, 0.95, 66",
    "system_voltage_v": 400
  },
  "electrical_hv_transformer_sizing": {
    "hv_voltage_kv": 11,
    "rated_transformer_kva": 500
  }
}
```

Value types must match the schema (`float`/`int`/`str`/`bool`, or one of
the exact strings listed in `allowed_values` for a `literal` field) — the
app validates against each module's pydantic model on submit, so a wrong
type or an out-of-range value will surface as a normal form validation
error there, not silently corrupt anything, but getting the type right
the first time saves the user a round trip.

Save the file somewhere the user can find it — ask where they'd like it
if not obvious, otherwise use the project's scratchpad location if one is
configured, or the current working directory with a clear name like
`extracted_calc_inputs.json`.

## Step 5 — write extraction notes alongside the JSON

Produce a short companion markdown (or plain text) note — this is the
audit trail, the same idea as every calc module's own `warnings` list, just
one level up (about the extraction itself rather than about a calculation):

- **What was extracted, and from where** (e.g. "Transformer rating 500kVA
  read from SLD sheet E-01, nameplate schedule").
- **What was deliberately left out and why** — every `required` field you
  didn't populate, with a one-line reason (not found / ambiguous /
  needs a value the source doesn't state).
- **Anything contradictory or worth a second look** — e.g. two sheets
  disagreeing on a rating.

## Step 6 — tell the user what to do next

Point them at the app's sidebar: **"Import extracted data (JSON)"**
expander, upload the file, click **Import**. Mention the extraction notes
file so they review what was and wasn't populated before running any
calc — an import is a starting point for the engineer to check and
complete, not a finished, ready-to-submit form.

## Scope

Electrical (LV) and Electrical (HV) only, for now (9 modules across those
two disciplines as of when this skill was written — confirm the current
set with the Step 1 schema export, don't assume the count). Other
disciplines (Structural, Civils, Mechanical Piping, Geotechnical) are not
in scope for this skill unless the user explicitly asks to extend it —
their source documents (structural GAs, piping isometrics, ground
investigation logs) are different enough in kind that this skill's
LV/HV-specific guidance above (SLD-centric, load-schedule format, etc.)
doesn't transfer directly.
