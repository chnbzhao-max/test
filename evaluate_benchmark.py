#!/usr/bin/env python3
"""Score independently human-labelled records; no generated ground-truth scores."""
import argparse
import json
from pathlib import Path
from westminster_leads.classifier import classify
from westminster_leads.config import TAXONOMY


def evaluate(samples, backend, require_human=False):
    if require_human:
        from review_app import record_hash
        for sample in samples:
            if sample.get('label_source') != 'human' or not sample.get('reviewer') or not sample.get('reviewed_at') or sample.get('reviewed_record_sha256') != record_hash(sample['record']):
                raise ValueError('Independent human review and matching source snapshot required; use review_app.py')
    counts = {trade: [0, 0, 0] for trade in TAXONOMY}  # TP, FP, FN
    contact_correct = 0
    errors = []
    usage = {}
    costs = []
    refs = set()
    if not samples:
        raise ValueError('Evaluation requires nonempty independent human-labelled examples')
    for sample in samples:
        if not isinstance(sample.get('trades'), list) or 'contact_route' not in sample:
            raise ValueError('Complete independent human labels before evaluation; trades must be an array')
        if sample.get('contact_route') not in ('agent', 'applicant', 'portal', None) or (sample.get('trades') and sample.get('contact_route') is None):
            raise ValueError('Invalid ground-truth contact route')
        ref = sample['record']['reference']
        if ref in refs or not set(sample['trades']) <= set(TAXONOMY):
            raise ValueError('Duplicate reference or invalid labels')
        refs.add(ref)
        predicted = classify(sample['record'], backend)
        actual, guessed = set(sample['trades']), set(predicted['relevant_trades'])
        for trade in TAXONOMY:
            counts[trade][0] += int(trade in actual & guessed)
            counts[trade][1] += int(trade in guessed-actual)
            counts[trade][2] += int(trade in actual-guessed)
        contact_correct += int(predicted.get('contact_route') == sample.get('contact_route'))
        if actual != guessed or predicted.get('contact_route') != sample.get('contact_route'):
            errors.append({'reference': ref, 'false_positive_trades': sorted(guessed-actual), 'false_negative_trades': sorted(actual-guessed), 'expected_contact': sample.get('contact_route'), 'predicted_contact': predicted.get('contact_route')})
        for key,value in predicted.get('usage', {}).items():
            if isinstance(value,int): usage[key] = usage.get(key,0)+value
        costs.append(predicted.get('estimated_cost_usd', 0 if backend == 'rules' else None))
    def metrics(tp, fp, fn):
        return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': tp/(tp+fp) if tp+fp else None,
                'recall': tp/(tp+fn) if tp+fn else None, 'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    return {'samples': len(samples), 'backend': backend, 'micro': metrics(*map(sum, zip(*counts.values()))),
            'per_trade': {t: metrics(*v) for t, v in counts.items()}, 'contact_accuracy': contact_correct/len(samples), 'label_provenance': 'human-attested' if require_human else 'unspecified; not verified as independent', 'held_out': False, 'errors': errors, 'usage': usage, 'estimated_cost_usd': sum(costs) if all(c is not None for c in costs) else None, 'warnings': ['Fewer than 50 samples; preliminary only'] if len(samples) < 50 else ['Sampling and holdout independence require reviewer verification']}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('labels', type=Path)
    p.add_argument('--backend', choices=['rules', 'openai'], default='rules')
    p.add_argument('--output', type=Path, default=Path('data/evaluation.json'))
    a = p.parse_args()
    result = evaluate(json.loads(a.labels.read_text()), a.backend, require_human=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
