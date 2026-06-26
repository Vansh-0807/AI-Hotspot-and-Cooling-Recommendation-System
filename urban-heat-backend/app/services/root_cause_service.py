from sqlalchemy.orm import Session

from app.db.models import GridCell
from app.models.schemas import AnalysisResponse, Contributor
from app.services.hotspot_service import CityBaselines, compute_baselines, get_cell_by_id, get_cells_for_city


FACTOR_LABELS = {
    "low_tree_cover": "Low tree cover",
    "high_impervious_surface": "High concrete / impervious surface",
    "traffic_congestion": "Traffic congestion",
    "lack_of_water_bodies": "Lack of nearby water bodies",
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_contributors(cell: GridCell, baselines: CityBaselines) -> list[Contributor]:
    tree_score = _clamp01((baselines.median_tree - cell.tree_cover_pct) / max(baselines.median_tree, 1))
    imperv_score = _clamp01((cell.impervious_pct - baselines.median_impervious) / max(100 - baselines.median_impervious, 1))
    traffic_score = _clamp01((cell.traffic_index - baselines.median_traffic) / max(1 - baselines.median_traffic, 0.01))
    water_score = _clamp01((cell.water_proximity_m - baselines.median_water_dist) / max(baselines.median_water_dist, 100))

    return [
        Contributor(
            factor="low_tree_cover",
            score=round(tree_score, 2),
            detail=f"Tree cover {cell.tree_cover_pct:.0f}% vs city avg {baselines.median_tree:.0f}%",
        ),
        Contributor(
            factor="high_impervious_surface",
            score=round(imperv_score, 2),
            detail=f"Concrete/asphalt {cell.impervious_pct:.0f}%",
        ),
        Contributor(
            factor="traffic_congestion",
            score=round(traffic_score, 2),
            detail=f"Traffic index {cell.traffic_index:.2f}",
        ),
        Contributor(
            factor="lack_of_water_bodies",
            score=round(water_score, 2),
            detail=f"Nearest water body {cell.water_proximity_m / 1000:.1f} km",
        ),
    ]


def build_summary(primary_cause: str, contributors: list[Contributor]) -> str:
    label = FACTOR_LABELS.get(primary_cause, primary_cause)
    top = sorted(contributors, key=lambda c: c.score, reverse=True)[:2]
    secondary = FACTOR_LABELS.get(top[1].factor, top[1].factor) if len(top) > 1 else ""
    if secondary:
        return (
            f"This zone is a heat island driven mainly by {label.lower()} "
            f"with contributing factors from {secondary.lower()}."
        )
    return f"This zone is a heat island driven mainly by {label.lower()}."


class RootCauseService:
    def analyze(self, db: Session, cell_id: str) -> AnalysisResponse:
        cell = get_cell_by_id(db, cell_id)
        if not cell:
            raise ValueError(f"Cell not found: {cell_id}")

        city_cells = get_cells_for_city(db, cell.city)
        baselines = compute_baselines(city_cells)
        contributors = score_contributors(cell, baselines)
        contributors.sort(key=lambda c: c.score, reverse=True)
        primary = contributors[0].factor

        return AnalysisResponse(
            cell_id=cell_id,
            temperature_c=round(cell.temperature_c, 2),
            contributors=contributors,
            primary_cause=primary,
            summary=build_summary(primary, contributors),
        )
