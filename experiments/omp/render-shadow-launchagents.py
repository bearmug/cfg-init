#!/usr/bin/env python3
"""Render the two shadow LaunchAgents locally; do not install or activate them."""
import argparse
from pathlib import Path
import plistlib


LABELS = ('ai.omp.decider-shadow', 'ai.omp.jev-shadow')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--experiment-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    replacements = {'__HOME__': str(args.home.resolve()), '__OMP_EXPERIMENT_DIR__': str(args.experiment_dir.resolve())}

    def replace(value):
        if isinstance(value, str):
            for token, path in replacements.items():
                value = value.replace(token, path)
            return value
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    template_dir = Path(__file__).resolve().parent / 'launchagents'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for label in LABELS:
        config = replace(plistlib.loads((template_dir / (label + '.plist')).read_bytes()))
        path = args.output_dir / (label + '.plist')
        path.write_bytes(plistlib.dumps(config))
        print(path)


if __name__ == '__main__':
    main()
