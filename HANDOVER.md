# Westminster — handover and operations

Use the existing checkout at `/workspace/test`; cloud tasks already run in isolated environments. Do not create worktrees unless requested. Install into `.venv` and use its interpreter. The current three PDFs remain unchanged.

## Routine operation

Run `run.py --demo` first for a network-free demonstration. Start `web_demo.py` for synthetic data or add `--live` for verified live data. A restored filesystem retains installed packages/data but not running services; restart the dashboard as needed. Do not expose the unprotected dashboard publicly.

After source/terms verification, schedule received/decided collection twice weekly. Example cron on Monday and Thursday at 08:00 machine time (confirm timezone before installation):

```
0 8 * * 1,4 cd /workspace/test && /workspace/test/.venv/bin/python run.py --terms-reviewed --weeks 4 >> /workspace/test/data/cron.log 2>&1
```

Create `data/` first. This is an example, not an installed cron job. Alternatively `scheduler.py --interval-hours 84 -- --terms-reviewed --weeks 4` runs one pipeline at a time in that process. Run only one scheduler per dataset; multi-process locking is not implemented. Use a supervisor for automatic daemon restart. For quick verification: `scheduler.py --once -- --demo`.

## Logs and recovery

- `data/<mode>/logs/last_run.json`: new/updated/unchanged, classified/excluded, pending count, failures, usage/cost, digest paths.
- `pipeline.log`: safe failure types and operations messages; `alerts.log`: append-only local failure reports. No outbound notification is configured.
- Exit 1 means pipeline failed, even if some records were saved. Resume after fixing the cause; primary-key upserts prevent duplicate rows. Incomplete extraction does not yield a new success digest. Older digest files may remain; check last_run.json before using them.
- CONNECT 403 before TLS: inspect environment allowlist and save required domains through environment settings. A draft save alone does not apply runtime policy. Never bypass the proxy or TLS checks.
- Portal 403/CAPTCHA or missing fields: stop; inspect permitted access and actual HTML. Do not mask it with fake records. Adapter fixture tests cannot validate a live source.
- API errors: inspect credential readiness and provider account/quota. Do not print keys or response bodies. Rules can be deliberately chosen for offline use; API failure does not automatically create rule output. Force is needed to replace cached classifications with a different model/method.
- Page cap: narrow window or increase cap only after verifying real pagination. Duplicate HTML is an error, not a reason to suppress a loop check.
- No new digest rows: confirm explicit grant decisions, parseable recent dates, selected area/trade and threshold. An empty file is not evidence of extraction success.
- SQLite/export inconsistency after interrupted disk write: rerun collection after fixing disk permissions/space. Upsert also repairs exports. Back up the entire data directory with the process stopped; verify restoration before deleting originals.

## Privacy, reuse and retention

Metadata may include personal data. No attachments are downloaded, and generated digests route users to the council. Confirm copyright/reuse permission before resale. Do not assume publicly visible names permit unsolicited marketing. Review UK GDPR lawful basis, minimisation, UK PECR, retention and deletion requests with the operator. No personal applicant emails/phones are inferred. Define retention before collecting live data; implement deletion/rotation for SQLite, exports, cache and backups together. Current prototype has no automatic retention policy or multiuser authentication.

## Cost and known limits

Rules are local and have no API charge. OpenAI reports token counts; supply current input/output rates to estimate cost. Cost is unknown until rates are supplied. Model pricing/availability, commercial reuse terms, live council selectors, council cross-check and an independent 50-record benchmark remain unverified. Four weeks of real Datahub validated/decided metadata were successfully retrieved; this is a secondary source. No actual customer delivery or automated outreach is implemented.

## Scaling to another council

Reuse storage, classification schema, taxonomy, evaluator, digests and scheduler. Replace source URL, form/field mapping, pagination and policy checks. Do not reuse Westminster permissions or fixtures as another council's verification.

## London Planning Datahub alternative

Use `run.py --source datahub --weeks 4 --limit 2000 --digest-days 28`. Data is isolated in data/datahub; reuse `--source datahub --skip-scrape` for classification/digests without fetching. Start dashboard with `web_demo.py --datahub`. No API key required. API host: planningdata.london.gov.uk; no environment config was changed for this work. Adapter uses public api-guest/applications/_search with fixed Westminster authority filter, validated/decided date windows, rate limiting, bounded retries and exact-count/duplicate checks. It cannot promise a transactionally stable source snapshot: if the index changes during retrieval, rerun and inspect count/duplicate failures. Historic withdrawals outside both date ranges require periodic wider reconciliation. Maximum from/size API window is 10,000; narrow date range rather than silently truncate.

Retain source_last_updated/source_last_synced for freshness. No applicant/agent data was available in observed records; contact route is portal, not an invented agent. No attachments were fetched. Datahub availability is not a commercial reuse licence. Verify current provider terms before resale. Defaults and saved environment startup instructions may still describe the original portal mode; consult current repository README first.

## Incremental Datahub scheduling

Current Datahub runs persist a successful scan-start checkpoint in SQLite sync_state and use last_updated OR last_synced with a default two-hour overlap. Ordinary `run.py --source datahub` commands auto-bootstrap once, then synchronize updates to all Westminster applications, including those outside the original history window. A nonblocking OS file lock serializes commands against the same dataset. Timestamp-only payload updates retain classification; unchanged exports are not rewritten. On failure, retain the old checkpoint and rerun. Source deletions and unmarked/backdated changes require separate reconciliation. Use --full-refresh for historical reconciliation; it preserves an existing incremental checkpoint. Do not wipe data to refresh code. See docs/INCREMENTAL_SYNC.md for exact query, split-window totals and recovery semantics. Older generic scheduler examples using portal mode are separate; for Datahub pass --source datahub and omit --force.
