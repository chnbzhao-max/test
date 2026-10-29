# Scheduled operation and failure reporting

## GitHub Actions

The repository includes two workflows:

- Tests: every push/PR plus manual execution; Python 3.12 and the full unittest suite.
- Westminster scheduled sync: Monday/Thursday 07:00 UTC plus manual Run workflow. This is 07:00 London winter / 08:00 London summer. GitHub schedules may be delayed and must be enabled on the default branch.

The sync job restores the dataset from an Actions cache, runs the incremental rules pipeline, runs the data audit, preserves state (including recoverable partial writes) and uploads current digests/reports as seven-day artifacts. Concurrent sync jobs are serialised. Failed pipeline/audit commands fail the workflow; GitHub's workflow summary displays counts rather than masking the exit status.

On GitHub: Actions → Westminster scheduled sync → Run workflow. Reports and digest downloads appear under the run's Artifacts. This runner has its own database; it does not automatically copy your Mac/Codespaces database. If no prior cache is available it bootstraps four weeks of history.

## State limits

GitHub Actions cache is opportunistic storage, not a permanent database backup. Caches can be evicted or expire; schedules can be disabled after repository inactivity; hosted runs have quotas and time limits. The twice-weekly interval is intended to retain a warm cache, but this is not a durability guarantee. Use a managed runner/VM and durable backed-up volume for production continuity or large datasets. Source metadata is public but artifact/cache access follows GitHub repository policy; do not add keys, private contact information or local human-review files to workflow outputs.

Only rules are used automatically, so scheduled runs cannot spend LLM credits. The workflow never reads .env or asks for API keys. No source documents, drawings or applicant-contact enrichment is downloaded. Review current data reuse terms before any commercial distribution.

## Alerts

Local failures append to data/datahub/logs/alerts.log and return nonzero. Hosted failures create a failed GitHub Actions run. Turn on Actions email/web notifications in your GitHub notification settings to receive those failures. This uses GitHub's native delivery; the application does not send unsolicited mail or Slack messages. No external notification was sent during development, and delivery is not claimed until you test your account's notification settings.

## Local scheduler

```sh
.venv/bin/python scheduler.py --once -- --source datahub --limit 10000 --digest-days 28
.venv/bin/python scheduler.py --interval-hours 84 -- --source datahub --limit 10000 --digest-days 28
```

The second command must remain running; closing the terminal or sleeping your Mac stops reliable scheduling. launchd/cron installation on your own Mac is not performed by this repository. Prefer GitHub Actions for a demonstration of unattended hosted operation, with the cache limitations above.
