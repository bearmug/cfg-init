#!/usr/bin/env python3
"""Run local scorer evaluation; optional private JSON cases never leave loopback.

python3 eval_score.py [--cases private.json] [--threshold 0.8] [--output results.json]
Cases: [{"id": "case", "prompt": "text", "assistant_context": "", "label": 0}]
Labels refer to dissatisfaction with the assistant, not external product quality.
"""
import argparse
import json
from pathlib import Path
import statistics
import time
import feedback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('eval_cases.json'))
    parser.add_argument('--threshold', type=float, default=0.8)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = []
    for case in json.loads(args.cases.read_text()):
        if type(case['label']) is not int or case['label'] not in (0, 1):
            raise ValueError('labels must be 0 or 1')
        start = time.monotonic()
        score, _, _ = feedback.score_event({'prompt': case['prompt'], 'assistant_context': case.get('assistant_context', '')})
        results.append({'id': case['id'], 'label': case['label'], 'score': score, 'seconds': time.monotonic() - start})
    tp = sum(r['label'] == 1 and r['score'] >= args.threshold for r in results)
    fp = sum(r['label'] == 0 and r['score'] >= args.threshold for r in results)
    fn = sum(r['label'] == 1 and r['score'] < args.threshold for r in results)
    report = {'threshold': args.threshold, 'count': len(results), 'tp': tp, 'fp': fp, 'fn': fn,
              'precision': tp / (tp + fp) if tp + fp else None,
              'recall': tp / (tp + fn) if tp + fn else None,
              'mean_ms': statistics.mean(r['seconds'] for r in results) * 1000,
              'results': results}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
