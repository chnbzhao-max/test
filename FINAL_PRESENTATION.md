# Presentation package

For macOS VS Code: docs/VS_CODE_MAC.md. Select F5 profile **Prepare presentation (offline)** after collecting real data, or run:

```sh
.venv/bin/python prepare_demo.py
```

Open `data/presentation/index.html` in a browser. Seven pages use actual local database counts, with Next/Previous navigation and print-to-PDF styling. Chinese five-minute speaking notes: docs/PRESENTATION_SCRIPT_ZH.md. Do not claim accuracy figures from automated tests or unlabelled samples.

Show: real source record → Markdown → trade digest → radius filter → incremental checkpoint → blind-review UI → scheduling/report evidence. Read docs/RELEASE_READINESS.md before presenting. A saved workflow definition is distinct from an actual hosted run, and a mock API test is distinct from a live LLM call.

No recorded video or external user-feedback study is included. The deck, speaking notes, runnable demo and honest limitations are supplied for the live presentation.
