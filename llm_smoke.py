#!/usr/bin/env python3
"""Explicit, single-record live OpenAI validation. Never runs automatically."""
import argparse
import json
import os
from pathlib import Path
from westminster_leads.config import ROOT
from westminster_leads.storage import Store
from westminster_leads.classifier import classify, excluded

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='One paid API request; source dataset is not modified')
    p.add_argument('--reference', required=True)
    p.add_argument('--model', default='gpt-4o-mini')
    p.add_argument('--data-dir', type=Path, default=ROOT/'data/datahub')
    a = p.parse_args()
    if not (os.environ.get('LEADS_LLM_API_KEY') or os.environ.get('OPENAI_API_KEY')):
        p.exit(2, 'No LLM credential configured. Configure LEADS_LLM_API_KEY securely in the VS Code launch environment or Codespaces Secrets; never paste it in chat. No request was made.\n')
    if not (a.data_dir/'planning_leads.db').exists(): p.error('Dataset not found')
    store = Store(a.data_dir)
    try: record = next((r for r,c in store.records() if r['reference'] == a.reference), None)
    finally: store.close()
    if not record or excluded(record): p.error('Choose an existing construction application that passes prefiltering')
    try: result = classify(record, 'openai', a.model)
    except Exception as error: p.exit(1, 'LLM smoke failed: '+type(error).__name__+'; no source data changed.\n')
    report = {'reference': a.reference, 'live_llm_call_verified': True, 'accuracy_measured': False, 'result': result}
    target = a.data_dir/'logs/llm_smoke.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
