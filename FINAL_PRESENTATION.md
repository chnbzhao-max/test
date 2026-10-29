# Westminster prototype — demonstration outline

1. Explain the PDF goal: convert one council's public planning applications into potential downstream trade leads. Distinguish the working public Datahub adapter from the blocked direct council portal; disclose secondary-source freshness and contact limitations.
2. Run `.venv/bin/python run.py --demo`. Show source-labelled JSON, per-record Markdown, SQLite persistence and three trade digests under `data/demo/`.
3. Run the command a second time: unchanged records are not duplicated or reclassified.
4. Start `.venv/bin/python web_demo.py`; locally filter Roofing and SW1A, switch granted/all statuses and download filtered Markdown. Every synthetic lead is marked as such.
5. Show tests and `last_run.json`. Explain rules scores are not accuracy; no real LLM evaluation numbers are claimed.
6. Show the optional OpenAI path, token-cost tracking and evaluator without making a paid API call during the demo.
7. Demonstrate `scheduler.py --once -- --demo`, then explain the example production schedule and local failure logs.
8. Show run.py --source datahub --weeks 4 --limit 2000 --digest-days 28 for real metadata. Next gates: commercial terms, council cross-check when available, live portal selectors, ~50 independent labels, accuracy and trade-user feedback.

No recorded video is included. This document is a reproducible live-demo script, not a claim that a presentation or user research has happened.
