import tempfile
import os
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd

from earlysignal.backtest import summary, walk_forward
from earlysignal.config import load_config
from earlysignal.db import connect
from earlysignal.ingest import read_csv, upsert
from earlysignal.scoring import calculate_scores


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        cls.rows = read_csv("data/demo_observations.csv")
        cls.frame = pd.DataFrame(cls.rows)
        numeric = ["value", "sentiment", "purchase_intent", "seller_count", "ad_intensity", "incumbent_share"]
        cls.frame[numeric] = cls.frame[numeric].astype(float)

    def test_database_upsert_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            db = connect(str(Path(directory) / "test.db"))
            upsert(db, self.rows[:5]); upsert(db, self.rows[:5])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 5)

    def test_scores_are_bounded_and_complete(self):
        weights = dict(self.config["weights"], source_weights=self.config["sources"])
        scores = calculate_scores(self.frame, weights)
        self.assertTrue(scores.fmos.between(0, 100).all())
        self.assertEqual(set(scores.country), {"US", "GB", "EU", "IN"})
        self.assertEqual(self.config["countries"], ["US", "GB", "EU", "IN"])
        self.assertGreater(scores.confidence.min(), 0)

    def test_backtest_has_samples(self):
        weights = dict(self.config["weights"], source_weights=self.config["sources"])
        results = walk_forward(self.frame, weights, horizon=7, step=14)
        self.assertGreater(summary(results)["samples"], 0)
        self.assertTrue(results.predicted_score.between(0, 100).all())

    def test_backtest_uses_calendar_days_and_complete_endpoints(self):
        row = self.frame.iloc[0].to_dict()
        dates = pd.date_range("2026-01-01", periods=22, freq="2D")
        frame = pd.DataFrame([dict(row, observed_at=date, value=100 + i)
                              for i, date in enumerate(dates)])
        results = walk_forward(frame, self.config["weights"], horizon=14, step=7)
        self.assertEqual(results.as_of.tolist(), ["2026-01-29"])
        self.assertAlmostEqual(results.future_growth.iloc[0], round(7 / 114, 4))
        # A peer with later data must not make this product's partial horizon eligible.
        peer = frame.assign(product="Other product")
        partial = pd.concat([frame.iloc[:-1], peer], ignore_index=True)
        results = walk_forward(partial, self.config["weights"], horizon=14)
        self.assertEqual(results["product"].tolist(), ["Other product"])

    def test_empty_history_and_invalid_windows(self):
        for frame in [pd.DataFrame(), self.frame.iloc[:1]]:
            self.assertEqual(summary(walk_forward(frame, self.config["weights"]))["samples"], 0)
        for horizon, step in [(0, 7), (-1, 7), (14, 0), (14, -1)]:
            with self.assertRaisesRegex(ValueError, "positive"):
                walk_forward(self.frame, self.config["weights"], horizon, step)
        scores = calculate_scores(self.frame, self.config["weights"], "1900-01-01")
        self.assertTrue(scores.empty)
        self.assertIn("fmos", scores.columns)

    def test_future_observations_do_not_change_scores(self):
        cutoff = sorted(self.frame.observed_at.unique())[28]
        historical = self.frame[self.frame.observed_at <= cutoff]
        pd.testing.assert_frame_equal(
            calculate_scores(self.frame, self.config["weights"], cutoff),
            calculate_scores(historical, self.config["weights"], cutoff))

    def test_empty_cli_and_backtest_replacement_are_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "empty.db")
            db = connect(path)
            db.execute("INSERT INTO backtests VALUES ('old', 'old', 14, 'US', 'old', 70, .2, 1)")
            db.commit()
            db.close()
            for command in ["score", "backtest"]:
                subprocess.run([sys.executable, "-m", "earlysignal.cli", command],
                               env=dict(os.environ, EARLYSIGNAL_DB=path),
                               capture_output=True, text=True, check=True)
            db = connect(path)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM backtests").fetchone()[0], 0)
            db.close()


if __name__ == "__main__":
    unittest.main()
