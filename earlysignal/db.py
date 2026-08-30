import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY,
  observed_at TEXT NOT NULL,
  country TEXT NOT NULL CHECK(country IN ('US','IN')),
  source TEXT NOT NULL,
  product TEXT NOT NULL,
  category TEXT NOT NULL,
  value REAL NOT NULL CHECK(value >= 0),
  sentiment REAL DEFAULT 0 CHECK(sentiment BETWEEN -1 AND 1),
  purchase_intent REAL DEFAULT 0 CHECK(purchase_intent BETWEEN 0 AND 1),
  seller_count REAL DEFAULT 0,
  ad_intensity REAL DEFAULT 0 CHECK(ad_intensity BETWEEN 0 AND 1),
  incumbent_share REAL DEFAULT 0 CHECK(incumbent_share BETWEEN 0 AND 1),
  is_demo INTEGER NOT NULL DEFAULT 0,
  UNIQUE(observed_at,country,source,product)
);
CREATE INDEX IF NOT EXISTS idx_observation_lookup ON observations(country,category,product,observed_at);
CREATE TABLE IF NOT EXISTS scores (
  scored_at TEXT NOT NULL, country TEXT NOT NULL, product TEXT NOT NULL, category TEXT NOT NULL,
  velocity REAL NOT NULL, confidence REAL NOT NULL, diffusion REAL NOT NULL, saturation REAL NOT NULL,
  commercial REAL NOT NULL, fmos REAL NOT NULL, stage TEXT NOT NULL,
  PRIMARY KEY(scored_at,country,product)
);
CREATE TABLE IF NOT EXISTS backtests (
  run_at TEXT NOT NULL, as_of TEXT NOT NULL, horizon_days INTEGER NOT NULL, country TEXT NOT NULL,
  product TEXT NOT NULL, predicted_score REAL NOT NULL, future_growth REAL NOT NULL, hit INTEGER NOT NULL
);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    db_path = Path(path or os.getenv("EARLYSIGNAL_DB", "data/earlysignal.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection
