"""
ML hotspot detection using Isolation Forest (anomaly detection) and K-Means (spatial clustering).

Isolation Forest identifies cells that are outliers in the multi-dimensional urban heat feature
space (temperature, impervious surface, tree cover, traffic). K-Means groups detected hotspots
into intervention zones for planners.
"""

import logging

import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class MLHotspotDetector:
    def __init__(self, contamination: float = 0.15, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state

    def detect(
        self,
        cells: list[dict],
    ) -> dict[str, dict]:
        """
        Run Isolation Forest on cell features and K-Means on hotspot centroids.
        Returns dict keyed by cell_id with ml_anomaly_score, is_hotspot, cluster_id.
        """
        if len(cells) < 4:
            return {
                c["cell_id"]: {
                    "ml_anomaly_score": 0.0,
                    "is_hotspot": False,
                    "cluster_id": 0,
                }
                for c in cells
            }

        features = np.array(
            [
                [
                    c["temperature_c"],
                    c["impervious_pct"],
                    100 - c["tree_cover_pct"],
                    c["traffic_index"] * 100,
                ]
                for c in cells
            ],
            dtype=np.float64,
        )

        iso = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        predictions = iso.fit_predict(features)
        anomaly_scores = -iso.score_samples(features)

        results: dict[str, dict] = {}
        hotspot_indices: list[int] = []

        for i, cell in enumerate(cells):
            is_anomaly = predictions[i] == -1
            results[cell["cell_id"]] = {
                "ml_anomaly_score": round(float(anomaly_scores[i]), 4),
                "is_hotspot": is_anomaly,
                "cluster_id": -1,
            }
            if is_anomaly:
                hotspot_indices.append(i)

        if len(hotspot_indices) >= 2:
            n_clusters = min(3, len(hotspot_indices))
            coords = np.array(
                [[cells[i]["centroid_lat"], cells[i]["centroid_lon"]] for i in hotspot_indices]
            )
            kmeans = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
            labels = kmeans.fit_predict(coords)
            for idx, cluster in zip(hotspot_indices, labels):
                results[cells[idx]["cell_id"]]["cluster_id"] = int(cluster)
        elif len(hotspot_indices) == 1:
            results[cells[hotspot_indices[0]]["cell_id"]]["cluster_id"] = 0

        return results

    def severity_from_anomaly(self, anomaly_score: float, scores: list[float]) -> str:
        if not scores:
            return "low"
        min_s, max_s = min(scores), max(scores)
        if max_s - min_s < 1e-6:
            return "medium"
        normalized = (anomaly_score - min_s) / (max_s - min_s)
        if normalized >= 0.7:
            return "high"
        if normalized >= 0.4:
            return "medium"
        return "low"
