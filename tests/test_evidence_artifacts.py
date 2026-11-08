import unittest

from cv.evidence_artifacts import build_evidence_artifacts


class EvidenceArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tracks = [
            {"frame": 0, "class_name": "player", "team": "team_a", "x": 10, "y": 10},
            {"frame": 0, "class_name": "player", "team": "team_a", "x": 90, "y": 10},
            {"frame": 0, "class_name": "player", "team": "team_b", "x": 10, "y": 90},
            {"frame": 0, "class_name": "goalkeeper", "team": "team_b", "x": 90, "y": 90},
        ]

    def test_heatmap_and_matrix_have_known_image_relative_cells(self):
        artifacts = build_evidence_artifacts(self.tracks, width=100, height=100, fps=5,
                                             heatmap_rows=2, heatmap_cols=2)
        all_heatmap = artifacts["heatmap"]["groups"]["all"]
        self.assertEqual(all_heatmap["counts"], [[1, 1], [1, 1]])
        self.assertEqual(all_heatmap["normalized"], [[0.25, 0.25], [0.25, 0.25]])
        self.assertEqual(artifacts["zoneMatrix"]["groups"]["team_a"]["observations"], 2)
        self.assertEqual(artifacts["zoneMatrix"]["coordinateSystem"], "image_relative_3x3")

    def test_shape_snapshot_is_normalized_and_limited(self):
        artifacts = build_evidence_artifacts(self.tracks, width=100, height=100, fps=5)
        shape = artifacts["teamShape"]
        self.assertEqual(shape["snapshots"][0]["groups"]["team_a"]["centroid"], {"x": 0.5, "y": 0.1})
        self.assertIn("not calibrated pitch coordinates", " ".join(shape["source"]["limitations"]))
