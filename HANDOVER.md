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

Rules are local and have no API charge. OpenAI reports token counts; supply current input/output rates to estimate cost. Cost is unknown until rates are supplied. Model pricing, availability, source terms, live portal selectors, an independent 50-record benchmark and real four-week history all remain unverified. No actual customer delivery or automated outreach is implemented.

## Scaling to another council

Reuse storage, classification schema, taxonomy, evaluator, digests and scheduler. Replace source URL, form/field mapping, pagination and policy checks. Do not reuse Westminster permissions or fixtures as another council's verification.
