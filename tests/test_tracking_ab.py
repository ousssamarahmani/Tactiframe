import json
import tempfile
import unittest
from pathlib import Path

from cv.tracking_ab import compare_tracking_runs


class TrackingAbTests(unittest.TestCase):
    def write_session(self, root: Path, name: str, ids: int, new_ids: list[int]) -> Path:
        session = root / name
        session.mkdir()
        metrics = {
            "uniquePlayerIds": ids, "trackObservations": 100,
            "validatedBallCandidates": 10, "candidateEvents": 2,
            "trackContinuity": {"meanObservationsPerId": 10, "medianObservationsPerId": 8,
                                "shortTrackShare": 0.2},
        }
        (session / "evaluation.json").write_text(json.dumps({"runId": name, "metrics": metrics}))
        (session / "track_diagnostics.json").write_text(json.dumps({
            "windows": [{"newTrackIds": value} for value in new_ids],
        }))
        return session

    def test_compares_metrics_and_writes_candidate_report(self):
        temp_root = Path(__file__).resolve().parents[1] / ".tmp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temp:
            root = Path(temp)
            baseline = self.write_session(root, "baseline", 20, [4, 6])
            candidate = self.write_session(root, "candidate", 18, [2, 4])
            report = compare_tracking_runs(baseline, candidate)
            self.assertEqual(report["metrics"]["uniquePlayerIds"]["delta"], -2)
            self.assertEqual(report["metrics"]["meanNewTrackIdsPerWindow"]["delta"], -2.0)
            self.assertTrue((candidate / "tracking_ab_comparison.json").is_file())
