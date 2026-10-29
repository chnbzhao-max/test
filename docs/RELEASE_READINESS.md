# Readiness evidence and external prerequisites

This release adds operational and review tooling; it is not a claim that independent human evaluation or production deployment has been completed.

| Capability | Implemented / observed | Remaining prerequisite |
| --- | --- | --- |
| Real Datahub ingestion | Actual Westminster records, exact totals, repeat runs and update checkpoint verified | Provider freshness; current reuse terms |
| Direct council adapter | Fixture tests; current public portal request still returns 503 | Accessible source and actual selector/field cross-check |
| Rules and lead filters | Concrete regression fixes, current real dataset reclassified | Independent human benchmark and held-out error review |
| Human review | Blind local web form, explicit negative labels, reviewer/time/source hash, atomic saves and CSRF checks | A real independent reviewer must complete labels |
| Metrics | CLI validates human attestations, emits per-trade and micro P/R/F1, contact-route accuracy, error list and token cost | Completed labels; self-attestation is not independent verification |
| OpenAI adapter | Mocked schema/cost/contact tests; one-record smoke command | No key is configured here; live API call is NOT verified |
| Digests and radius | Actual dashboard/filter/export HTTP checks, real postcode centre lookup | Public coordinate quality and commercial use conditions |
| Scheduled job | GitHub Actions workflow, state caching, reports, fail statuses; local commands tested | Hosted Actions run and account notification settings must be checked separately |
| Local data backup | Private ZIP, SQLite consistent backup; restored data/classification/checkpoint in a temporary test | User-controlled durable storage and routine backups |
| macOS VS Code | Project-relative interpreter config, F5 launch profiles, instructions | Actual execution on the user's Mac; development verification runs on Linux |
| Presentation | Seven-slide offline deck built from actual local counts; Chinese speaking notes | User should rehearse and state limitations honestly |

Local suite: **34 tests passed**. A review-interface HTTP test used a temporary synthetic fixture only; it did not label the real evaluation set or measure accuracy. Live local HTTP tests exercised the actual Datahub dashboard and postcode-centred radius export. The current deck was generated from 1,284 stored records, with 42 Roofing / 56 Scaffolding / 36 Groundworks eligible leads in the then-current 28-day window. Counts overlap and can change as the source updates.

No LLM secret was present in the cloud runtime. The smoke script exited without a request as designed. No external email/Slack notification was sent. No environment draft was modified or environment published. Reuse/copyright/UK GDPR/PECR questions remain for the operator; public access alone is not a resale licence.

Hosted workflow observations, when available, are recorded below separately from local tests.
