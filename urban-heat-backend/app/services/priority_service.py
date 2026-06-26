from sqlalchemy.orm import Session

from app.models.schemas import BudgetTier, PriorityItem, PriorityResponse, RecommendationItem
from app.services.hotspot_service import HotspotService, compute_baselines, get_cells_for_city
from app.services.recommendation_service import RecommendationService
from app.services.root_cause_service import RootCauseService


COST_TIER_MAP: dict[BudgetTier, float] = {"low": 1.0, "medium": 2.0, "high": 4.0}


class PriorityService:
    def __init__(self):
        self.hotspot_service = HotspotService()
        self.root_cause_service = RootCauseService()
        self.recommendation_service = RecommendationService()

    def rank(self, db: Session, city: str, top_n: int = 10) -> PriorityResponse:
        cells = get_cells_for_city(db, city)
        if not cells:
            raise ValueError(f"No grid data for city: {city}")

        baselines = compute_baselines(cells)
        ranked: list[PriorityItem] = []

        for cell in cells:
            anomaly = cell.temperature_c - baselines.mean_temp
            if anomaly < 0.5:
                continue

            heat_stress = (
                0.5 * min(anomaly / 5, 1.0)
                + 0.3 * cell.population_proxy
                + 0.2 * cell.vulnerability
            )

            analysis = self.root_cause_service.analyze(db, cell.cell_id)
            recs = self.recommendation_service.recommend(db, cell.cell_id, "medium")
            top_rec = recs.recommendations[0] if recs.recommendations else None
            if not top_rec:
                continue

            cost = COST_TIER_MAP.get(top_rec.cost_tier, 2.0)
            roi = top_rec.estimated_cooling_c / cost
            priority_score = heat_stress * roi

            ranked.append(
                {
                    "cell_id": cell.cell_id,
                    "heat_stress_score": round(heat_stress, 2),
                    "intervention_roi": round(roi, 2),
                    "recommended_action": top_rec.action,
                    "expected_cooling_c": top_rec.estimated_cooling_c,
                    "priority_score": round(priority_score, 2),
                }
            )

        ranked.sort(key=lambda r: r["priority_score"], reverse=True)
        top = [
            PriorityItem(rank=i, **item)
            for i, item in enumerate(ranked[:top_n], start=1)
        ]

        return PriorityResponse(city=city, rankings=top)
