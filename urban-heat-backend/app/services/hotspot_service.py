import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import GridCell
from app.models.schemas import HotspotCell, HotspotStats, HotspotsResponse, Severity
from app.services.ml_service import MLHotspotDetector


@dataclass
class CityBaselines:
    mean_temp: float
    median_tree: float
    median_impervious: float
    median_traffic: float
    median_water_dist: float


def get_cells_for_city(db: Session, city: str) -> list[GridCell]:
    return db.query(GridCell).filter(GridCell.city == city).all()


def get_cell_by_id(db: Session, cell_id: str) -> GridCell | None:
    return db.query(GridCell).filter(GridCell.cell_id == cell_id).first()


def compute_baselines(cells: list[GridCell]) -> CityBaselines:
    temps = [c.temperature_c for c in cells]
    trees = [c.tree_cover_pct for c in cells]
    imperv = [c.impervious_pct for c in cells]
    traffic = [c.traffic_index for c in cells]
    water = [c.water_proximity_m for c in cells]

    def median(vals: list[float]) -> float:
        s = sorted(vals)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2

    return CityBaselines(
        mean_temp=sum(temps) / len(temps),
        median_tree=median(trees),
        median_impervious=median(imperv),
        median_traffic=median(traffic),
        median_water_dist=median(water),
    )


def classify_severity(anomaly_c: float, settings: Settings | None = None) -> Severity:
    s = settings or get_settings()
    if anomaly_c >= s.severity_high_c:
        return "high"
    if anomaly_c >= s.severity_medium_c:
        return "medium"
    return "low"


class HotspotService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.ml_detector = MLHotspotDetector()

    def get_hotspots(self, db: Session, city: str, query_date) -> HotspotsResponse:
        cells = get_cells_for_city(db, city)
        if not cells:
            raise ValueError(f"No grid data for city: {city}")

        baselines = compute_baselines(cells)
        if cells:
            lons = [c.centroid_lon for c in cells]
            lats = [c.centroid_lat for c in cells]
            bbox = [
                min(lons) - 0.01,
                min(lats) - 0.01,
                max(lons) + 0.01,
                max(lats) + 0.01,
            ]
        else:
            bbox = list(self.settings.bbox_tuple)

        ml_input = [
            {
                "cell_id": c.cell_id,
                "temperature_c": c.temperature_c,
                "impervious_pct": c.impervious_pct,
                "tree_cover_pct": c.tree_cover_pct,
                "traffic_index": c.traffic_index,
                "centroid_lat": c.centroid_lat,
                "centroid_lon": c.centroid_lon,
            }
            for c in cells
        ]
        ml_results = self.ml_detector.detect(ml_input)
        all_ml_scores = [ml_results[c.cell_id]["ml_anomaly_score"] for c in cells]

        hotspot_cells: list[HotspotCell] = []
        max_temp = max(c.temperature_c for c in cells)
        hotspot_count = 0

        for cell in cells:
            anomaly = round(cell.temperature_c - baselines.mean_temp, 2)
            ml_info = ml_results.get(cell.cell_id, {})
            ml_is_hotspot = ml_info.get("is_hotspot", False)

            if ml_is_hotspot:
                severity: Severity = self.ml_detector.severity_from_anomaly(
                    ml_info.get("ml_anomaly_score", 0), all_ml_scores
                )
            else:
                severity = classify_severity(anomaly, self.settings)

            if severity in ("high", "medium") or ml_is_hotspot:
                hotspot_count += 1

            geometry = json.loads(cell.geometry_json)
            hotspot_cells.append(
                HotspotCell(
                    cell_id=cell.cell_id,
                    geometry=geometry,
                    temperature_c=round(cell.temperature_c, 2),
                    anomaly_c=anomaly,
                    severity=severity,
                    centroid_lat=cell.centroid_lat,
                    centroid_lon=cell.centroid_lon,
                    ml_anomaly_score=ml_info.get("ml_anomaly_score"),
                    ml_is_hotspot=ml_is_hotspot,
                    cluster_id=ml_info.get("cluster_id"),
                )
            )

        return HotspotsResponse(
            city=city,
            date=query_date,
            bbox=bbox,
            cells=hotspot_cells,
            stats=HotspotStats(
                mean_temp_c=round(baselines.mean_temp, 2),
                max_temp_c=round(max_temp, 2),
                hotspot_count=hotspot_count,
            ),
        )
