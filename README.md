# Westminster Planning Leads

A Python prototype that turns public Westminster planning-application metadata into a trade-specific lead feed. It collects applications, stores structured records, classifies potential trade requirements, and produces filtered HTML and Markdown digests.

The project was built from scratch against the requirements supplied with the repository. Planning permission is treated as a potential business signal, not proof that construction will begin or that a contractor is being sought.

## Project status

The end-to-end prototype has run successfully with real data from the **London Planning Datahub**, a secondary source. A verified run on **29 October 2026** retrieved 1,284 unique Westminster applications across 13 pages for the four-week validated-or-decided date window. Counts change as the source updates.

Implemented and exercised:

- Real metadata collection, bounded pagination, duplicate detection, and source attribution.
- SQLite storage with per-application JSON and Markdown exports.
- Persistent incremental synchronisation, update detection, and failure recovery.
- Rule-based classification, conservative approval filtering, and trade digests.
- A local dashboard with area, postcode-prefix, and postcode-centred radius filters.
- A blind human-review interface, evaluation tooling, local backups, and an offline presentation generator.
- GitHub Actions tests and a successfully executed hosted synchronisation workflow.

**Validation still outstanding:** an independent human-labelled classification benchmark, a live OpenAI API test, an independent comparison against the council register, commercial reuse review, and customer feedback. The direct council HTML adapter remains unverified against live Westminster pages. Automated test results are not classification-accuracy measurements.

Detailed evidence and limitations: [Release readiness](docs/RELEASE_READINESS.md), [Source verification](docs/VERIFICATION.md), and [Data-quality review](docs/QUALITY_REVIEW.md).

## Quick start: offline demonstration

Python 3.12 is recommended. From the project directory on macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --demo
.venv/bin/python web_demo.py
```

Open `http://127.0.0.1:8000` in your local browser. Stop the server with Ctrl+C.

The demonstration uses **eight explicitly synthetic applications**, requires no API key, and makes no paid API calls. Sample Roofing, Scaffolding, and Groundworks digests are written to `data/demo/digests/` as HTML and Markdown. They are not real sales leads.

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python`. VS Code launch configurations are included for collection, the dashboard, human review, presentation preparation, and an optional single-record LLM test. The [macOS VS Code guide](docs/VS_CODE_MAC.md) is currently written in Chinese.

## Collect real Westminster data

The working adapter uses the public London Planning Datahub guest interface. No Datahub API key is required.

```sh
.venv/bin/python run.py --source datahub --weeks 4 --limit 10000 --digest-days 28
.venv/bin/python web_demo.py --datahub
```

On the first successful run, the pipeline collects applications whose **validated date or decision date** falls within the requested history window. It does not substitute the validated date for a received date. Later ordinary runs use the saved incremental checkpoint instead of downloading the same four-week window again.

The command generates:

```text
data/datahub/
├── planning_leads.db       # Application records, classifications, and sync checkpoint
├── raw/                    # Normalised per-application JSON
├── markdown/               # Readable per-application Markdown
├── digests/                # Filtered HTML and Markdown digests
├── logs/                   # Run reports, audit results, and local failure logs
└── review/                 # Human-review samples and separately stored predictions
```

Generated data, credentials, virtual environments, and backups are excluded from Git. **A repository ZIP contains the source and documentation, not an already populated database or generated presentation.** Each local checkout, Codespace, or hosted runner needs its own dataset or a trusted restored backup.

The report at `data/datahub/logs/last_run.json` records new, updated, unchanged, classified, and pending counts, together with extraction statistics and failures. An exact API total matching the unique records establishes completeness for that query against Datahub; it does not establish completeness against the council register.

## Incremental synchronisation

Use the same command on subsequent days:

```sh
.venv/bin/python run.py --source datahub --limit 10000 --digest-days 28
```

The pipeline requests Westminster records whose `last_updated` or `last_synced` timestamp falls between the previous successful checkpoint, with a **two-hour safety overlap**, and the start of the current scan. This includes updates to older applications outside the initial history window.

- New reference: insert and classify.
- Changed application content: update and invalidate the previous classification.
- Source timestamps alone changed: retain the classification.
- Unchanged content: retain the record and avoid rewriting unchanged exports.
- Failed run: retain the previous checkpoint so the next run can retry safely.

Overlap can deliberately retransmit some records. An empty incremental result still requires a lightweight API request and does not mean the local database is empty. Preserve the SQLite database to retain progress. Same-dataset Datahub commands use a process lock.

To reconcile or expand historical coverage explicitly:

```sh
.venv/bin/python run.py --source datahub --full-refresh --weeks 8 --limit 10000 --digest-days 28
```

An existing incremental checkpoint is retained during a history refresh. Changing `--weeks` alone does not reset established incremental progress. See [Incremental synchronisation](docs/INCREMENTAL_SYNC.md) for split-window pagination, delayed updates, recovery, and source-deletion limitations.

## Classification and lead selection

The default backend is a local keyword-based classifier. The taxonomy covers 11 categories: Scaffolding, Groundworks, Roofing, Kitchens & Bathrooms, Electrical, Plumbing, Skip Hire / Waste Removal, Architecture, Party-Wall Surveying, General Building / Refurbishment, and Landscaping. All 11 are retained because the supplied materials list Plumbing in addition to the stated ten categories.

A prefilter excludes selected non-construction proposals, such as pure tree works and advertisement consents. Remaining records may match multiple trades or no trades. **A record passing the prefilter is not automatically an actionable lead.**

Rule scores, typically 0.75 for a matched trade, are heuristic values, not calibrated probabilities. Rule-mode summaries are derived from the proposal text, and project scale remains unknown. Broad or historical wording can still cause classification errors.

Default approval selection is deliberately conservative: separate LBC references, discharges, certain amendments and condition variations, retrospective proposals, refusals, and conflicting pending statuses are excluded from primary-permission digests. This is a business filter, not a legal judgement about those consents. Original records remain stored and available to broader views. Distinct applications at the same property are not automatically merged into one project.

`--limit` caps classifications per run, not records downloaded. Inspect `pending_classification` and continue with `--skip-scrape` if needed. Routine runs do not need `--force`; use it deliberately after changing classification rules or models.

## Digests and geographic filters

Regenerate digests from existing records without collection:

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --trades Roofing,Scaffolding --area SW1 --min-confidence 0.7 --digest-days 28
```

The default digest window is seven days; `--digest-days 28` selects four weeks. Granted-only digests use decision dates. All-status views use received dates where available, otherwise validated dates. `--all-statuses` relaxes approval filtering; it does not turn excluded proposals into verified leads.

For a real postcode-centred radius:

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --centre-postcode 'SW1A 1AA' --radius-km 2 --digest-days 28
```

Radius filtering uses Postcodes.io for the centre and published Datahub coordinates for application locations. It measures straight-line distance, excludes records without valid coordinates, and only searches the collected Westminster dataset. It is not a driving-distance calculation or a search across neighbouring councils.

The dashboard supports these filters and Markdown export. It binds to loopback by default and has no production user authentication. HTML digests are email-style previews: **the application does not send email or perform outreach**. Contact routing falls back to the council portal when applicant or agent information is unavailable; no contact details are invented.

## Optional OpenAI classification

Set `LEADS_LLM_API_KEY` securely in the execution environment; an existing `OPENAI_API_KEY` is also supported. Never commit credentials or send them in chat. The explicit VS Code LLM smoke-test profile can load a local, Git-ignored `.env` copied from `.env.example`; normal terminal commands do not automatically load that file.

A single-record live test, once a key is configured:

```sh
.venv/bin/python llm_smoke.py --reference 'YOUR-EXISTING-APPLICATION-REFERENCE'
```

This makes at most one classification API call, leaves source records unchanged, and writes a separate report. Choose an application that passes the prefilter. No key means no request. A successful single call verifies integration, not classification accuracy.

To classify a limited batch explicitly:

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --backend openai --model gpt-4o-mini --limit 10 --force
```

Outputs are schema-validated. API failures are reported rather than silently replaced with rule results. Inputs select minimal proposal metadata rather than applicant names or personal addresses, although proposal text itself may contain personal information.

Token usage is recorded. Dollar estimates require current `LEADS_INPUT_USD_PER_MILLION` and `LEADS_OUTPUT_USD_PER_MILLION` rates; otherwise cost is reported as unknown. Check current model availability and provider prices. Scheduled jobs use rules and do not spend LLM credits.

## Audit, human review, and evaluation

Refresh rules and prepare the default audit and presentation without downloading data:

```sh
.venv/bin/python prepare_demo.py
```

Or run the audit separately after regenerating matching 28-day digests:

```sh
.venv/bin/python run.py --source datahub --skip-scrape --force --limit 10000 --digest-days 28
.venv/bin/python audit_data.py
.venv/bin/python review_app.py
```

The audit checks stored records, exports, and digest consistency, reports source contradictions, and prepares an unlabelled 50-record review template without overwriting existing reviews. The private review interface runs on port 8002, hides predictions, and records reviewer identity, time, and a source-record hash. Reviewers must choose trades or explicitly label a negative example.

Once independent reviews are complete:

```sh
.venv/bin/python evaluate_benchmark.py \
  data/datahub/review/human_labels_template.json \
  --backend rules --output data/datahub/review/evaluation.json
```

The CLI rejects incomplete or source-mismatched attestations. It produces micro and per-trade precision, recall, F1, contact-route accuracy, error details, and usage/cost information. Attestation does not independently authenticate the reviewer or prove a held-out sample. Sampling coverage and separation from model development must be documented. No benchmark accuracy is claimed for the currently unlabelled set.

## Tests

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The verified release passed 34 tests locally and in GitHub Actions. Coverage includes pagination, update detection, checkpoint recovery, source validation, filtering, geographic calculations, review persistence, mocked LLM handling, and backup restoration. Synthetic fixtures and mocked API calls are identified as such; they are not live council or LLM validation.

## Automation, backups, and presentation

GitHub Actions provides tests and a Monday/Thursday **07:00 UTC** synchronisation workflow, also available through **Actions → Westminster scheduled sync → Run workflow**. A real hosted run completed successfully. It preserves state using an Actions cache and supplies downloadable reports, digests, and the presentation as artifacts. Cache eviction, schedule delays, and account notification settings remain operational considerations; a cache is not a permanent database backup. See [Automation](docs/AUTOMATION.md).

For a private local backup, stop the review interface first:

```sh
.venv/bin/python backup_data.py
```

Backups are stored under Git-ignored `backups/`, include local review information, and are not uploaded. Restore only into a new empty directory and validate before replacing active data. See [Handover](HANDOVER.md).

To prepare a presentation from existing real data:

```sh
.venv/bin/python prepare_demo.py
```

Open `data/presentation/index.html` in a browser. The seven-slide deck uses current local counts and supports printing to PDF. [Presentation notes](FINAL_PRESENTATION.md) explain the package; [Chinese speaking notes](docs/PRESENTATION_SCRIPT_ZH.md) are also included.

## Direct council adapter: experimental

The separate HTML adapter is implemented but not verified against live Westminster pages; observed access attempts returned HTTP 503. Before using it, confirm the current official portal, inspect terms and robots rules, check for supported feeds, and validate the real form and detail selectors. Network restrictions may require the council hosts to be allowed in your own execution environment.

```sh
.venv/bin/python verify_portal.py
# Only after terms and live adapter validation:
.venv/bin/python run.py --terms-reviewed --weeks 1 --max-pages 30
```

This mode uses bounded pagination, a six-hour detail cache, rate limiting, and retries. `--refresh` bypasses that cache. It does not download drawings or attachments, or bypass access challenges. `--terms-reviewed` records operator confirmation; it does not grant reuse permission. See [Discovery](docs/DISCOVERY.md).

## Project structure

| File or directory | Responsibility |
| --- | --- |
| `run.py` | End-to-end command-line pipeline |
| `westminster_leads/datahub.py` | Working public Datahub adapter and incremental queries |
| `westminster_leads/extractor.py` | Experimental council HTML adapter |
| `westminster_leads/storage.py` | SQLite, exports, synchronisation state, and process lock |
| `westminster_leads/classifier.py`, `config.py` | Prefilter, taxonomy, rules, and optional OpenAI integration |
| `westminster_leads/digest.py`, `geography.py` | Lead selection, exports, and geographic filtering |
| `web_demo.py` | Private read-only dashboard |
| `audit_data.py`, `review_app.py`, `evaluate_benchmark.py` | Audit, human labels, and evaluation |
| `backup_data.py`, `prepare_demo.py`, `build_presentation.py` | Backup and presentation tools |
| `.github/workflows/` | Tests and scheduled synchronisation |
| `.vscode/`, `docs/`, `HANDOVER.md` | Launch configurations, design, operation, and limitations |

## Responsible use and limitations

Datahub is a secondary source and may omit or delay council information. Planning approval does not establish a start date, trade requirement, or marketing permission. Applicant/agent information can be personal data; collect only what is needed and assess copyright, reuse conditions, UK GDPR, PECR, retention, and contact permissions before commercial use. Public accessibility alone is not a resale licence.

The interfaces are private prototype tools, not an authenticated public service. Production use needs durable storage, appropriate access controls, monitoring, independent quality evaluation, and user feedback. See [Technical design](docs/DESIGN.md) and [Release readiness](docs/RELEASE_READINESS.md) for the remaining acceptance criteria.
