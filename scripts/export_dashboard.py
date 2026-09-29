"""Export a portable dashboard snapshot from SQLite, or the bundled demo CSV."""
import argparse
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from earlysignal.backtest import summary, walk_forward
from earlysignal.config import load_config
from earlysignal.ingest import read_csv
from earlysignal.scoring import calculate_scores


def export(output: Path, database: Path | None = None):
    if database:
        # Read-only prevents a mistyped database path from creating an empty database.
        with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            data = pd.read_sql_query('SELECT * FROM observations', connection)
    else:
        data = pd.DataFrame(read_csv(str(ROOT / 'data/demo_observations.csv')))
    numeric = ['value', 'sentiment', 'purchase_intent', 'seller_count', 'ad_intensity', 'incumbent_share', 'is_demo']
    data[numeric] = data[numeric].apply(pd.to_numeric, errors='raise')
    config = load_config(str(ROOT / 'config.yml'))
    weights = dict(config['weights'], source_weights=config['sources'])
    scores = calculate_scores(data, weights)
    results = walk_forward(data, weights)
    history = []
    for (product, country, source), group in data.groupby(['product', 'country', 'source']):
        daily = group.groupby('observed_at').value.mean().sort_index()
        history.append(dict(product=product, country=country, source=source,
                            points=[[str(day), round(float(value), 3)] for day, value in daily.items()]))
    demo = int(data.is_demo.eq(1).sum())
    payload = dict(generated_at=datetime.now(timezone.utc).isoformat(),
                   as_of=str(data.observed_at.max()) if len(data) else None,
                   mode='empty' if data.empty else 'demo' if demo == len(data) else 'mixed' if demo else 'imported',
                   observation_count=len(data), countries=config['countries'],
                   sources=sorted(data.source.unique().tolist()), weights=config['weights'],
                   scores=scores.to_dict('records'), history=history,
                   backtest=dict(summary(results), horizon_days=14),
                   backtests=results.drop(columns=['run_at']).to_dict('records'))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, allow_nan=False, separators=(',', ':')) + '\n')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, help='Existing SQLite database (default: synthetic demo)')
    parser.add_argument('--output', type=Path, default=ROOT / 'frontend/data.json')
    args = parser.parse_args()
    payload = export(args.output, args.database)
    print(f"Exported {len(payload['scores'])} opportunities to {args.output} ({payload['mode']})")
