import argparse

import pandas as pd

from .backtest import summary, walk_forward
from .config import load_config
from .db import connect
from .ingest import read_csv, upsert
from .scoring import calculate_scores


def observations(connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM observations", connection)


def score(connection, config):
    weights = dict(config["weights"], source_weights=config["sources"])
    scores = calculate_scores(observations(connection), weights)
    if not scores.empty:
        connection.execute("DELETE FROM scores WHERE scored_at = ?", (scores.scored_at.iloc[0],))
        scores.to_sql("scores", connection, if_exists="append", index=False)
    return scores


def main():
    parser = argparse.ArgumentParser(description="EarlySignal pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Initialize the database")
    init.add_argument("--demo", action="store_true")
    ingest = sub.add_parser("ingest", help="Import normalized CSV")
    ingest.add_argument("csv")
    sub.add_parser("score", help="Calculate latest scores")
    backtest = sub.add_parser("backtest", help="Walk-forward evaluation")
    backtest.add_argument("--horizon", type=int, default=14)
    args = parser.parse_args()
    connection, config = connect(), load_config()
    if args.command == "init":
        count = upsert(connection, read_csv("data/demo_observations.csv")) if args.demo else 0
        print(f"Database ready; imported {count} demo observations")
    elif args.command == "ingest":
        print(f"Imported {upsert(connection, read_csv(args.csv))} observations")
    elif args.command == "score":
        results = score(connection, config)
        print(results[["country", "product", "fmos", "stage"]].to_string(index=False))
    else:
        weights = dict(config["weights"], source_weights=config["sources"])
        results = walk_forward(observations(connection), weights, args.horizon)
        connection.execute("DELETE FROM backtests")
        results.to_sql("backtests", connection, if_exists="append", index=False)
        print(summary(results))


if __name__ == "__main__":
    main()
