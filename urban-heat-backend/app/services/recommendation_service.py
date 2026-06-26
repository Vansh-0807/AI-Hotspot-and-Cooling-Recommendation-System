import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.schemas import BudgetTier, RecommendationItem, RecommendationRequest, RecommendationResponse
from app.services.mistral_service import MistralService
from app.services.root_cause_service import RootCauseService
from app.services.runtime_config import get_runtime_config

logger = logging.getLogger(__name__)

TEMPLATES: dict[str, list[dict]] = {
    "low_tree_cover": [
        {"action": "plant_trees", "quantity": "500 trees", "cooling": 1.8, "cost": "medium"},
        {"action": "green_corridor", "quantity": "2 km corridor", "cooling": 1.4, "cost": "high"},
    ],
    "high_impervious_surface": [
        {"action": "cool_roofs", "coverage_pct": 30, "cooling": 1.2, "cost": "medium"},
        {"action": "reflective_pavement", "coverage_pct": 25, "cooling": 0.7, "cost": "low"},
    ],
    "traffic_congestion": [
        {"action": "green_corridor", "quantity": "1.5 km shade buffer", "cooling": 1.0, "cost": "medium"},
        {"action": "plant_trees", "quantity": "300 trees", "cooling": 1.2, "cost": "low"},
    ],
    "lack_of_water_bodies": [
        {"action": "retention_pond", "quantity": "1 mini wetland", "cooling": 0.9, "cost": "high"},
        {"action": "plant_trees", "quantity": "200 trees", "cooling": 0.8, "cost": "low"},
    ],
}

NARRATIVE_TEMPLATES: dict[str, str] = {
    "low_tree_cover": (
        "Prioritize native tree planting along exposed corridors. "
        "A green buffer will reduce surface heating and improve pedestrian comfort."
    ),
    "high_impervious_surface": (
        "Apply cool roofs on flat industrial rooftops and increase reflective pavement "
        "on high-traffic asphalt zones to lower absorbed heat."
    ),
    "traffic_congestion": (
        "Install shaded green buffers near congested corridors to reduce vehicular heat "
        "and improve air quality in transit zones."
    ),
    "lack_of_water_bodies": (
        "Introduce small retention ponds or bioswales to increase local evaporative cooling "
        "and mitigate daytime heat buildup."
    ),
}


def _budget_multiplier(tier: BudgetTier) -> float:
    return {"low": 0.7, "medium": 1.0, "high": 1.3}[tier]


class RecommendationService:
    def __init__(self):
        self.root_cause_service = RootCauseService()

    def _try_mistral_narrative(self, analysis_summary: str, recs: list[RecommendationItem]) -> str | None:
        settings = get_settings()
        api_key = get_runtime_config().effective_mistral(settings.mistral_api_key)
        if not api_key:
            return None
        try:
            mistral = MistralService(api_key)
            return mistral.generate_cooling_narrative(analysis_summary, [r.action for r in recs])
        except Exception as exc:
            logger.warning("Mistral narrative failed: %s", exc)
            return None

    def _try_gemini_narrative(self, analysis_summary: str, recs: list[RecommendationItem]) -> str | None:
        settings = get_settings()
        api_key = get_runtime_config().effective_gemini(settings.gemini_api_key)
        if not api_key:
            return None
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            actions = ", ".join(r.action for r in recs)
            prompt = (
                "Write 2-3 sentences of actionable urban cooling advice for city planners. "
                "Use only the facts provided. Do not invent numbers.\n"
                f"Context: {analysis_summary}\n"
                f"Recommended actions: {actions}"
            )
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            logger.warning("Gemini narrative failed: %s", exc)
            return None

    def _ai_narrative(self, analysis_summary: str, recs: list[RecommendationItem]) -> str | None:
        narrative = self._try_mistral_narrative(analysis_summary, recs)
        if narrative:
            return narrative
        return self._try_gemini_narrative(analysis_summary, recs)

    def recommend(self, db: Session, cell_id: str, budget_tier: BudgetTier = "medium") -> RecommendationResponse:
        analysis = self.root_cause_service.analyze(db, cell_id)
        templates = TEMPLATES.get(analysis.primary_cause, TEMPLATES["low_tree_cover"])
        multiplier = _budget_multiplier(budget_tier)

        recommendations: list[RecommendationItem] = []
        for i, tmpl in enumerate(templates[:2], start=1):
            cooling = round(tmpl["cooling"] * multiplier, 2)
            recommendations.append(
                RecommendationItem(
                    action=tmpl["action"],
                    quantity=tmpl.get("quantity"),
                    coverage_pct=tmpl.get("coverage_pct"),
                    estimated_cooling_c=cooling,
                    cost_tier=tmpl["cost"],
                    priority=i,
                )
            )

        narrative = self._ai_narrative(analysis.summary, recommendations)
        if not narrative:
            narrative = NARRATIVE_TEMPLATES.get(
                analysis.primary_cause,
                NARRATIVE_TEMPLATES["low_tree_cover"],
            )

        return RecommendationResponse(
            cell_id=cell_id,
            recommendations=recommendations,
            narrative=narrative,
        )

    def handle_request(self, db: Session, request: RecommendationRequest) -> RecommendationResponse:
        return self.recommend(db, request.cell_id, request.budget_tier)
