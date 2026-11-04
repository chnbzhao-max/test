# Westminster Planning Leads

[Chinese version](README.zh-CN.md)

This project collects Westminster planning applications and turns them into a short feed for building trades. A roofer, for example, can filter recent approvals for relevant work in a particular area instead of searching the whole planning register.

The program uses Python, SQLite and a local web interface. It saves the application data, assigns possible trades and produces HTML and Markdown digests. The default classifier uses keyword rules; an optional OpenAI backend is also included.

## Data source and progress

The working data source is the public **London Planning Datahub** API. The original plan was to collect directly from Westminster's Idox portal, but requests from the development environment returned HTTP 503. The HTML adapter is still in the repository for further work.

A run on **29 October 2026** collected **1,284 unique applications across 13 pages**, covering applications validated or decided between 2 and 29 October. The API total matched the number of unique records saved. These are historical test results; a new run may return different counts.

The Datahub pipeline, incremental updates, local dashboard and digest generation have been tested with real records. The release also passed 34 automated tests, and a GitHub Actions sync completed successfully. Details are in [Verification](docs/VERIFICATION.md) and [Release readiness](docs/RELEASE_READINESS.md).

## Running the project

Python 3.12 is recommended. In the project folder on macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Collect four weeks of real data and start the dashboard:

```sh
.venv/bin/python run.py --source datahub --weeks 4 --limit 10000 --digest-days 28
.venv/bin/python web_demo.py --datahub
```

Open `http://127.0.0.1:8000` in a browser. Press Ctrl+C in the terminal to stop the server. No Datahub API key is required.

For a quick offline check, use the eight synthetic examples:

```sh
.venv/bin/python run.py --demo
.venv/bin/python web_demo.py
```

Demo records are marked as synthetic and stored separately. On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. VS Code F5 configurations are provided; the [macOS setup guide](docs/VS_CODE_MAC.md) is in Chinese.

## Storage and repeat runs

Real Datahub records are stored under `data/datahub/`:

```text
planning_leads.db    Application records, classifications and sync progress
raw/                Normalised JSON exports
markdown/           One readable Markdown file per application
digests/            HTML and Markdown lead digests
logs/               Run reports and data audits
review/             Human-review samples and labels
```

The application reference is the database key. New references are inserted; changes to an existing application update its record. A content change triggers reclassification, while a change to source timestamps alone preserves the previous classification.

The first successful run saves a sync checkpoint. Later runs query `last_updated` and `last_synced` from that checkpoint, with a two-hour overlap. This also picks up changes to older applications outside the original four-week window. Failed runs keep the previous checkpoint so they can be retried.

Use the same command for normal updates:

```sh
.venv/bin/python run.py --source datahub --limit 10000 --digest-days 28
```

Keep the local database to retain progress. To expand or reconcile the historical window, add `--full-refresh --weeks 8`; changing `--weeks` alone does not reset an existing checkpoint. See [Incremental sync](docs/INCREMENTAL_SYNC.md) for the query and recovery behaviour.

Generated data, `.env`, virtual environments and backups are ignored by Git. A downloaded repository ZIP includes the code and documentation; collect data or restore a trusted backup to populate a new machine.

## Classification and digests

The rules cover 11 trades, including Roofing, Scaffolding, Groundworks, Plumbing and Landscaping. The full taxonomy is in `westminster_leads/config.py`. A prefilter removes selected non-construction applications, such as pure tree works and advertisement consents.

Applications can match several trades. The rule score of 0.75 is a fixed heuristic, not a measured probability of being correct. Rule-mode summaries come from the proposal text, and project scale is left unknown.

The default approval digest excludes separate listed-building consents, discharges, certain amendments and condition variations, retrospective proposals, refusals and conflicting pending statuses. This is a conservative lead-selection policy. The original records remain in the database, and different references at the same property are not automatically merged into one project.

Generate an area-specific digest from existing data:

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --trades Roofing,Scaffolding --area SW1 --digest-days 28
```

Or filter by a full centre postcode and a radius in kilometres:

```sh
.venv/bin/python run.py --source datahub --skip-scrape \
  --centre-postcode 'SW1A 1AA' --radius-km 2 --digest-days 28
```

Radius filtering uses Postcodes.io and the coordinates supplied by Datahub. Records without valid coordinates are excluded. The dashboard provides the same filters and a Markdown export.

A few useful options:

| Option | Purpose |
| --- | --- |
| `--limit` | Maximum classifications per run, not maximum records downloaded |
| `--skip-scrape` | Work with the data already stored locally |
| `--force` | Reclassify existing records after a rule or model change |
| `--digest-days` | Digest date window; the default is seven days |
| `--all-statuses` | Relax the approval filter for broader inspection |

The observed Datahub records did not provide applicant or agent contact details, so the contact route points back to the council portal. The program generates digest files; it does not send emails or contact applicants.

## Review and evaluation

Run the audit and open the independent-review interface:

```sh
.venv/bin/python prepare_demo.py
.venv/bin/python review_app.py
```

The audit checks the database against its JSON and Markdown exports, flags source inconsistencies and prepares 50 unlabelled review samples. The review page runs on port 8002. It hides model predictions and records the reviewer's labels, name, time and source-record hash. Existing reviews are preserved.

After the reviews are complete:

```sh
.venv/bin/python evaluate_benchmark.py \
  data/datahub/review/human_labels_template.json \
  --backend rules --output data/datahub/review/evaluation.json
```

The report includes precision, recall and F1 by trade, micro scores, contact-route accuracy and individual errors. The CLI rejects unfinished or source-mismatched reviews. Review independence and the choice of held-out samples still need to be documented by the reviewer. No classification-accuracy result is claimed for the currently unlabelled set.

To run the automated tests:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover collection, pagination, duplicate handling, sync recovery, lead filtering, geography, review saves, mocked LLM responses and backup restoration. [Quality review](docs/QUALITY_REVIEW.md) describes the issues found in real records and the resulting fixes.

## Optional LLM backend

OpenAI classification requires `LEADS_LLM_API_KEY` or an existing `OPENAI_API_KEY` in the execution environment. The VS Code single-record test configuration can load a local `.env` copied from `.env.example`. Ordinary terminal commands do not load `.env` automatically.

Once a key is configured, a single-record test is available:

```sh
.venv/bin/python llm_smoke.py --reference 'YOUR-EXISTING-APPLICATION-REFERENCE'
```

This leaves the source dataset unchanged. Batch classification is available through `run.py --source datahub --skip-scrape --backend openai --limit 10 --force`. API errors are reported rather than replaced with rule output.

Token usage is recorded. Cost estimates need current `LEADS_INPUT_USD_PER_MILLION` and `LEADS_OUTPUT_USD_PER_MILLION` rates; otherwise cost remains unknown. Keep credentials out of Git. A live OpenAI call has not yet been verified for this project.

## Presentation, backups and scheduling

`prepare_demo.py` reclassifies stored records with the current rules, runs the audit and builds a seven-slide presentation at `data/presentation/index.html`. Open it in a browser or print it to PDF. The preparation command uses existing data and makes no paid API calls.

For a private local backup, stop the review interface and run:

```sh
.venv/bin/python backup_data.py
```

Backups go to the Git-ignored `backups/` folder. Restore into a new empty directory and check the result before replacing active data. [HANDOVER.md](HANDOVER.md) covers recovery.

GitHub Actions runs tests and provides a Monday/Thursday 07:00 UTC sync schedule. The sync workflow can also be started from the Actions tab. It saves state in an Actions cache and uploads reports, digests and the presentation. Cache eviction and notification settings need monitoring; the cache is not a permanent backup. See [Automation](docs/AUTOMATION.md).

## Code layout

| File | Role |
| --- | --- |
| `run.py` | Pipeline entry point |
| `westminster_leads/datahub.py` | Datahub collection and incremental queries |
| `westminster_leads/storage.py` | SQLite, exports and sync state |
| `westminster_leads/classifier.py`, `config.py` | Prefilter, trade rules and OpenAI support |
| `westminster_leads/digest.py`, `geography.py` | Lead selection and geographic filters |
| `web_demo.py` | Local dashboard |
| `audit_data.py`, `review_app.py`, `evaluate_benchmark.py` | Data checks and classification evaluation |
| `westminster_leads/extractor.py` | Experimental council HTML adapter |

## Remaining work

The Datahub feed can lag behind the council register. A direct council comparison is still needed; the HTML adapter has only fixture-based validation. The independent human benchmark, live OpenAI test and feedback from tradespeople are also outstanding.

Planning approval does not establish a construction start date or permission to market to an applicant. Commercial use requires a review of data reuse conditions, copyright, UK GDPR and PECR. The local interfaces have no production authentication; wider deployment also needs durable storage and monitoring.

Further design and operation notes are in [Technical design](docs/DESIGN.md) and [Release readiness](docs/RELEASE_READINESS.md).
