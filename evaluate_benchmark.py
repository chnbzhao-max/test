#!/usr/bin/env python3
"""Score independently human-labelled records; no generated ground-truth scores."""
import argparse
import json
from pathlib import Path
from westminster_leads.classifier import classify
from westminster_leads.config import TAXONOMY


def evaluate(samples, backend):
    counts = {trade: [0, 0, 0] for trade in TAXONOMY}  # TP, FP, FN
    contact_correct = 0
    refs = set()
    if not samples:
        raise ValueError('Evaluation requires nonempty independent human-labelled examples')
    for sample in samples:
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
    def metrics(tp, fp, fn):
        return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': tp/(tp+fp) if tp+fp else None,
                'recall': tp/(tp+fn) if tp+fn else None, 'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    return {'samples': len(samples), 'backend': backend, 'micro': metrics(*map(sum, zip(*counts.values()))),
            'per_trade': {t: metrics(*v) for t, v in counts.items()}, 'contact_accuracy': contact_correct/len(samples)}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('labels', type=Path)
    p.add_argument('--backend', choices=['rules', 'openai'], default='rules')
    p.add_argument('--output', type=Path, default=Path('data/evaluation.json'))
    a = p.parse_args()
    result = evaluate(json.loads(a.labels.read_text()), a.backend)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
