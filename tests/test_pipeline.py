import tempfile
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
        self.assertEqual(set(scores.country), {"US", "IN"})
        self.assertGreater(scores.confidence.min(), 0)

    def test_backtest_has_samples(self):
        weights = dict(self.config["weights"], source_weights=self.config["sources"])
        results = walk_forward(self.frame, weights, horizon=7, step=14)
        self.assertGreater(summary(results)["samples"], 0)
        self.assertTrue(results.predicted_score.between(0, 100).all())


if __name__ == "__main__":
    unittest.main()
