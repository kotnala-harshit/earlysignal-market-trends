import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from earlysignal.db import connect
from earlysignal.ingest import read_csv, upsert
from scripts.export_dashboard import export


class DashboardExportTest(unittest.TestCase):
    def test_database_snapshot_empty_imported_and_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database, output = root / 'test.db', root / 'data.json'
            db = connect(str(database))
            result = export(output, database)
            self.assertEqual(result['mode'], 'empty')
            self.assertEqual(result['scores'], [])
            self.assertEqual(result['backtest']['samples'], 0)
            rows = read_csv('data/demo_observations.csv')[:5]
            for row in rows:
                row['is_demo'] = 0
            upsert(db, rows)
            db.close()
            result = export(output, database)
            self.assertEqual(result['mode'], 'imported')
            self.assertEqual(result['observation_count'], 5)
            self.assertTrue(result['scores'])
            self.assertEqual(sum(len(h['points']) for h in result['history']), 5)
            self.assertEqual(json.loads(output.read_text()), result)
            missing = root / 'missing.db'
            with self.assertRaises(sqlite3.OperationalError):
                export(output, missing)
            self.assertFalse(missing.exists())
            self.assertEqual(json.loads(output.read_text()), result)


if __name__ == '__main__':
    unittest.main()
