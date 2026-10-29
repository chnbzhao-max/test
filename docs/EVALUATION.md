# Honest classifier evaluation

No real Westminster ground truth is currently available. Do not reuse the Essex 86.9% F1 or fabricate fifty labels from the same rules being tested.

Collect approximately 50 distinct live applications across all trade labels, positive and negative cases, refusals and borderline work. An independent human reads each description and supplies relevant trades and the best published contact route. Freeze the labels before running the classifier. Keep a held-out set when revising prompts. Use real reference IDs to prevent duplicates; remove personal details not needed for labelling.

File format (illustrative shape only; replace with real human labels):

```json
[
  {
    "record": {
      "reference": "REPLACE-WITH-REAL-REFERENCE",
      "description": "REPLACE-WITH-PUBLIC-PROPOSAL",
      "agent": "Published agent if present"
    },
    "trades": ["Roofing"],
    "contact_route": "agent"
  }
]
```

Every sample must include contact_route (agent/applicant/portal); excluded nonconstruction examples should use empty trades and null contact_route because prefiltering does not route contacts. The evaluator returns precision/recall/F1 per trade, micro metrics, contact-route accuracy and sample count. Undefined metrics are null, not an invented perfect score. Publish label counts and examples of errors alongside metrics. Test fixtures validate code arithmetic only, not real accuracy. Keep labelled data out of Git if it contains personal information.
