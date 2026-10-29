# Westminster data-quality review — 2026-10-29

Scope: the 1,241 actual London Planning Datahub records already collected for 2026-10-02 through 2026-10-29, validated OR decided dates. This is a secondary-source audit, not an independent council validation or a human classifier benchmark.

## Data and persistence checks

- 1,241 unique references; no synthetic provenance or DEMO identifiers.
- All descriptions and assembled addresses populated.
- No records outside the requested window on both date fields.
- Every raw JSON export equals its SQLite payload. Every Markdown export contains the reference and full description, normalising CR/LF line endings for text comparison.
- 516 records have no decision date; all 516 have status Application Under Consideration. Two also carry decision Approved; these are source contradictions, not errors silently repaired in the database. The approval selector rejects pending status even when decision says Approved.
- Contradictions: `26/04412/LLBCO`, `26/07190/MOD106`. Keep original metadata and verify at council when available.

A fresh API query retrieved ten references spread across the sorted dataset: 23/08356/ADLBC, 26/04273/FULL, 26/05361/ADFULL, 26/05816/CLOPUD, 26/06168/ADV, 26/06551/ADLBC, 26/06809/FULL, 26/06955/TPO, 26/07110/ADFULL, SNN26/00097. Description, validated date, decision date, decision, status and postcode matched in all 60 comparisons. This checks import fidelity to the same provider, not truth against another source.

## Concrete findings and corrections

1. Datahub can assign Full planning & listed building consent to both the FULL and linked LBC references. For example 25/02470/FULL and 25/02471/LBC describe linked work. A combined type label alone must not make LBC a separate primary-permission lead. The default approval digest now excludes LBC reference suffixes even when the type looks combined. Both original applications remain in storage and can be inspected in all-status mode. Different FULL applications at one property are not automatically merged.
2. The previous garden keyword tagged work simply located in a garden, such as air-conditioning installation, as Landscaping. Landscaping now needs a relevant work phrase (landscaping, paving, decking, etc.), rather than a location mention alone.
3. Kitchen extraction and bathroom vents are ventilation work, not automatically kitchen/bathroom refits. Explicit extract/ventilation and kitchen/dining-room location phrases are removed from the room-refit matching text. Mixed proposals with a separate kitchen refit still match.
4. Default primary-permission leads now conservatively exclude condition variations and retrospective descriptions, as well as separate listed-building permissions, discharges, certificates and amendments. This is a business filter, not a legal assertion that these applications lack permission or can never be useful. They remain in all-status views.

## Digest result on this snapshot

| Trade | Before quality corrections | After quality corrections |
| --- | ---: | ---: |
| Roofing | 62 | 41 |
| Scaffolding | 87 | 54 |
| Groundworks | 47 | 34 |

Counts use minimum score 0.7, explicit eligible approval, decision date within the 28-day window. Rows overlap between trades; do not add the columns as unique customers. Fewer rows reflect tighter eligibility, not measured precision improvement. Twenty automated tests passed, including regression cases for the concrete findings and audit corruption detection.

## Reproduce in Codespaces

```sh
git pull --ff-only origin main
.venv/bin/python run.py --source datahub --skip-scrape --force --limit 2000 --digest-days 28
.venv/bin/python audit_data.py
.venv/bin/python -m unittest discover -s tests -v
```

Force deliberately refreshes cached rules classifications. If data has changed or grown beyond 2,000 records, inspect pending_classification and adjust the limit. The audit expects regenerated 28-day digests by default. An empty dataset or actual integrity issue returns nonzero. Retained older records outside the requested window are listed separately; they are not automatically corrupt. Report: data/datahub/logs/audit.json. The audit does not make network calls.

## Independent human review still needed

The audit creates a deterministic 50-record, application-type-stratified review template at data/datahub/review/human_labels_template.json. Trade labels are null, not model-produced ground truth. Existing review files are never overwritten. Predictions are separate in predictions_at_sampling.json so a reviewer can label without seeing them. This sample is for diagnostic coverage, not a representative prevalence estimate, and is not guaranteed to cover every trade.

Have an independent reviewer fill trades with canonical labels (or [] for no relevant trades) and contact_route with agent/applicant/portal (null only for intentionally excluded proposals). Record rationale and reviewer identity outside any sensitive public exports. Only after all labels are complete, run:

```sh
.venv/bin/python evaluate_benchmark.py data/datahub/review/human_labels_template.json --backend rules --output data/datahub/review/evaluation.json
```

No F1/accuracy is reported here. AI inspection of selected examples is not independent human labelling. Remaining known limits include generic roof-location/plant phrases potentially triggering Roofing, broad erection triggers for Groundworks, historic work quoted in proposals, related FULL applications, and no verified applicant/agent routes. More targeted labels and held-out validation are required before claiming sellable lead quality. Council cross-check, commercial reuse terms and live LLM validation are still outstanding.
