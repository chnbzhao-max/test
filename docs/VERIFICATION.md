# Live validation / 真实验证记录

Date: 2026-10-29. Execution location: Codex managed cloud environment, **not the user's GitHub Codespaces**.

## Observed evidence

- Runtime HTTP policy: unrestricted, enforced.
- Current official planning register guidance: HTTP 200. Links confirm the Idox host, advanced search and weekly list.
- `https://idoxpa.westminster.gov.uk/robots.txt`: HTTP 503.
- `https://idoxpa.westminster.gov.uk/online-applications/search.do?action=advanced`: HTTP 503.
- Proxy response text: `upstream connect error or disconnect/reset before headers. reset reason: connection termination`.

No real application details were fetched from the direct council portal. Four weeks of real metadata were subsequently obtained from the alternative public Datahub interface (see below). Terms, robots, exact live form schema, pagination completeness and classifier accuracy remain unverified. A 503 here does not establish global portal downtime or the same outcome from Codespaces. The prior guidance URL was stale; DISCOVERY.md now links to the verified current page.

## Run the same preflight in Codespaces

Stop a running dashboard with Ctrl+C, then run in the repository terminal:

```sh
git pull --ff-only origin main
.venv/bin/python verify_portal.py
```

The script reads official guidance and robots. If robots cannot be read or disallows access, it stops before search. Otherwise it checks the advanced search form and date input names. It prints safe status metadata and writes `data/verification/preflight.json`; it never prints cookies, keys or hidden form values. Exit 1 is an incomplete/failed preflight; exit 0 means the checked connectivity and form prerequisites passed, not that scraping, terms or lead accuracy are verified.

Share the printed report to diagnose the next step. If the Codespaces browser can load the public portal but Python cannot, record that distinction; do not disable TLS or bypass access challenges.

## Once preflight passes

1. Review current official terms, copyright/reuse and data protection requirements. Check for a supported API/feed before deciding on HTML extraction. Do not copy Essex permissions.
2. Inspect real form actions and fields; inspect one permitted public result/detail page. Correct adapter mappings only from actual evidence.
3. Run `.venv/bin/python run.py --terms-reviewed --weeks 1 --refresh`. This flag records operator confirmation, not permission supplied by the script.
4. On the same date, search the portal for the exact inclusive seven-day interval (today minus six days through today), separately for received and determined. Compare the union of references with SQLite and raw exports. Account for overlaps rather than adding both counts blindly. Check every page was traversed and no hidden result cap applies.
5. Manually compare at least ten reference/description/address/status/decision/date records across both searches, including refusals and grants. Confirm dates are parsed, and unapproved applications never enter granted-only digests.
6. Repeat with `--refresh`: references must stay unique. Site updates can legitimately change some payloads; verify the reason rather than demanding unchanged counts during a live update.
7. After one-week checks pass, expand to `--weeks 4`. Default classification limit is 100; inspect pending_classification and continue with `--skip-scrape` or choose an appropriate limit. Expand digest window using `--digest-days 28` when inspecting four-week leads.
8. Independently label approximately fifty real applications; evaluate rules and LLM separately. No accuracy claim should come from the synthetic unit tests.

Automated tests now also cover diagnostic early stopping on inaccessible/disallowing robots and ensure a passing preflight does not claim extraction readiness. No environment configuration was changed or published during this validation.

## Alternative source validated: London Planning Datahub

The public endpoint `https://planningdata.london.gov.uk/api-guest/applications/_search` returned HTTP 200 and real Westminster records. A public unfiltered probe was followed by a fixed `lpa_name: Westminster` query. The borough text varies (Westminster / City Of Westminster), so the adapter validates planning-authority identity instead of relying on a single borough string.

Two full runs for **2026-10-02 through 2026-10-29 inclusive** queried **valid_date OR decision_date**, not received date. Both completed thirteen pages and matched the API's exact total of **1,241 unique references**. Run 1: 1,241 new, 1,241 classified/pre-screened, 201 excluded, zero failures and zero pending. Run 2: zero new, zero changed, 1,241 unchanged, zero reclassifications and zero failures. This verifies idempotence against an unchanged API result, not against future updates.

SQLite contained 1,241 entries; exports contained 1,241 JSON and 1,241 Markdown files. All provenance values were london_datahub and no DEMO references were present. Classified nonexcluded applications route to portal because agent/applicant data was not available. Three real-data trade digests were generated. Actual local HTTP requests to the Datahub dashboard and filtered Markdown export returned 200 with the secondary-source attribution and no demo references. Fifteen automated tests passed, including pagination, out-of-range/wrong-authority records, source-total drift, duplicates, page limits and diagnostic policy stops.

A sampled record had source_last_synced 2026-10-28; preserve per-record freshness rather than assuming council real time. Absence of data in a particular field is not evidence that the council does not publish it. This validation does **not** establish:

- Council completeness or correctness: direct portal access is still unavailable, so no independent council-to-Datahub reference/field comparison was possible.
- An accurate trade classifier: rules ran, but about fifty independent human labels and any live LLM benchmark remain outstanding.
- Commercial reuse permission: the hosted public API was accessible, but the GLA guidance returned a JavaScript challenge and the Datastore dataset page returned 403. No challenge or access refusal was bypassed; current reuse terms need operator review before resale.

No environment draft updates or publication occurred. Code and tests are versioned; harvested data remains ignored by Git and must be fetched in each Codespaces workspace. API metadata is a separate source, not a way around council robots rules.
