# Engineering Report Profile v22

## Purpose

The default printed interval report must answer engineer-facing questions first:

1. What was found?
2. Where was it found?
3. How reliable is the interpretation?
4. Why was the conclusion made?
5. What should be checked next?

The default profile must not start from internal counters, raw dataframe rows, NaN diagnostics or long technical tables.

## Profiles

### engineering

Default profile. Includes:

- executive summary;
- main interval table;
- interval cards;
- reasoning, recommendations and limitations;
- hydrocarbon interval summary and markers.

Excludes by default:

- preliminary row-count interpretation table;
- numeric min/max/mean table;
- bounded raw dataframe table.

### expert

Technical profile. Includes the engineering content plus:

- preliminary interpretation class counts;
- numeric statistics;
- bounded raw dataframe preview;
- technical appendix material.

## Rationale

A practicing geologist or mud-logging engineer usually needs the interpreted intervals first. Row counts and raw table dumps are useful for audit/debug work, but they should not dominate the printed report.
