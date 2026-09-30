#!/usr/bin/env python3
"""Summarize local/remote agreement, not ground-truth accuracy."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


def percentile(values, fraction):
    values = sorted(x for x in values if isinstance(x, (float, int)) and math.isfinite(x))
    return values[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def summarize(rows):
    pairs = [q for row in rows if row.get('trialActive') for q in row.get('questions', [])]
    eligible = [q for q in pairs if q.get('type') in ('choice', 'noul')]
    decisions = [q for q in pairs if q.get('type') in ('choice', 'noul') and isinstance(q.get('agreement'), bool)]
    scores = [q['scoreAbsDelta'] for q in pairs if isinstance(q.get('scoreAbsDelta'), (int, float))]
    gates = []
    for threshold in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
        accepted = [q for q in decisions if isinstance(q.get('localCertainty'), (float, int)) and q['localCertainty'] >= threshold]
        gates.append({'threshold': threshold, 'pairedDecisions': len(decisions), 'accepted': len(accepted),
                      'coverage': len(accepted) / len(eligible) if eligible else None,
                      'coverageOnPaired': len(accepted) / len(decisions) if decisions else None,
                      'agreementWithJev': sum(q['agreement'] for q in accepted) / len(accepted) if accepted else None})
    result = {'requests': len(rows), 'activeRequests': sum(bool(r.get('trialActive')) for r in rows),
              'eligibleDecisions': len(eligible),
              'pairedDecisions': len(decisions),
              'agreementWithJev': sum(q['agreement'] for q in decisions) / len(decisions) if decisions else None,
              'scorePairs': len(scores), 'scoreMeanAbsDelta': sum(scores) / len(scores) if scores else None,
              'gates': gates, 'interpretation': 'Agreement with Jev is not ground-truth accuracy. Coverage includes unpaired failures; coverageOnPaired does not.'}
    for side in ('local', 'remote'):
        records = [r.get(side, {}) for r in rows]
        costs = [r['cost'] for r in records if isinstance(r.get('cost'), (float, int))]
        result[side] = {'statuses': dict(Counter(r.get('status', 'missing') for r in records)),
                        'latencyMs': {'p50': percentile([r.get('ms') for r in records], 0.5), 'p95': percentile([r.get('ms') for r in records], 0.95)},
                        'inputTokens': sum(r.get('inputTokens') or 0 for r in records),
                        'outputTokens': sum(r.get('outputTokens') or 0 for r in records),
                        'costReportedRequests': len(costs),
                        'reportedCostUsd': sum(costs) if costs else None}
    result['totalLatencyMs'] = {'p50': percentile([r.get('totalMs') for r in rows], 0.5), 'p95': percentile([r.get('totalMs') for r in rows], 0.95)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', type=Path, default=Path.home() / '.omp/agent/telemetry/decider-jev/requests.jsonl')
    args = parser.parse_args()
    rows = []
    incomplete = 0
    if args.path.exists():
        for line in args.path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                incomplete += 1
    result = summarize(rows)
    result['unparseableLines'] = incomplete
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
