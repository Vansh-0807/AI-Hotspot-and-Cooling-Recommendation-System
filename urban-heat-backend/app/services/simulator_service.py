from app.config import Settings, get_settings
from app.models.schemas import ScenarioInput, ScenarioResult, SimulateRequest, SimulateResponse
from app.services.hotspot_service import get_cell_by_id
from sqlalchemy.orm import Session


class SimulatorService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _cooling_for_scenario(self, scenario: ScenarioInput) -> float:
        s = self.settings
        if scenario.intervention == "increase_tree_cover":
            delta = scenario.delta_pct or 10
            return (delta / 10) * s.cooling_tree_per_10pct
        if scenario.intervention == "cool_roofs":
            coverage = scenario.coverage_pct or 30
            return (coverage / 30) * s.cooling_roof_per_30pct
        if scenario.intervention == "reflective_pavement":
            coverage = scenario.coverage_pct or scenario.delta_pct or 20
            return (coverage / 20) * s.cooling_pavement_per_20pct
        if scenario.intervention == "green_corridor":
            delta = scenario.delta_pct or 15
            return (delta / 10) * s.cooling_tree_per_10pct * 0.9
        if scenario.intervention == "retention_pond":
            return 0.6
        return 0.0

    def simulate(self, db: Session, request: SimulateRequest) -> SimulateResponse:
        cell = get_cell_by_id(db, request.cell_id)
        if not cell:
            raise ValueError(f"Cell not found: {request.cell_id}")

        baseline = cell.temperature_c
        results: list[ScenarioResult] = []
        total_cooling = 0.0

        for scenario in request.scenarios:
            cooling = min(self._cooling_for_scenario(scenario), self.settings.max_cooling_c)
            projected = max(baseline - cooling, baseline - self.settings.max_cooling_c)
            results.append(
                ScenarioResult(
                    intervention=scenario.intervention,
                    delta_pct=scenario.delta_pct,
                    coverage_pct=scenario.coverage_pct,
                    projected_temp_c=round(projected, 2),
                    cooling_c=round(cooling, 2),
                )
            )
            total_cooling += cooling

        combined_cooling = min(total_cooling * 0.85, self.settings.max_cooling_c)
        combined_projected = round(baseline - combined_cooling, 2)

        return SimulateResponse(
            cell_id=request.cell_id,
            baseline_temp_c=round(baseline, 2),
            results=results,
            combined_projected_temp_c=combined_projected if len(request.scenarios) > 1 else None,
            combined_cooling_c=round(combined_cooling, 2) if len(request.scenarios) > 1 else None,
        )
