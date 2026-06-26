from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
BudgetTier = Literal["low", "medium", "high"]
InterventionType = Literal[
    "increase_tree_cover",
    "cool_roofs",
    "reflective_pavement",
    "green_corridor",
    "retention_pond",
]


class HealthResponse(BaseModel):
    status: str
    city: str
    database: str
    version: str = "1.1.0"
    data_ready: bool = False
    keys_configured: bool = False
    cell_count: int = 0


class HotspotCell(BaseModel):
    cell_id: str
    geometry: dict[str, Any]
    temperature_c: float
    anomaly_c: float
    severity: Severity
    centroid_lat: float
    centroid_lon: float
    ml_anomaly_score: float | None = None
    ml_is_hotspot: bool | None = None
    cluster_id: int | None = None


class HotspotStats(BaseModel):
    mean_temp_c: float
    max_temp_c: float
    hotspot_count: int


class HotspotsResponse(BaseModel):
    city: str
    date: date
    bbox: list[float]
    cells: list[HotspotCell]
    stats: HotspotStats


class Contributor(BaseModel):
    factor: str
    score: float = Field(ge=0, le=1)
    detail: str


class AnalysisResponse(BaseModel):
    cell_id: str
    temperature_c: float
    contributors: list[Contributor]
    primary_cause: str
    summary: str


class RecommendationRequest(BaseModel):
    cell_id: str
    budget_tier: BudgetTier = "medium"


class RecommendationItem(BaseModel):
    action: str
    quantity: str | None = None
    coverage_pct: float | None = None
    estimated_cooling_c: float
    cost_tier: BudgetTier
    priority: int


class RecommendationResponse(BaseModel):
    cell_id: str
    recommendations: list[RecommendationItem]
    narrative: str


class ScenarioInput(BaseModel):
    intervention: InterventionType
    delta_pct: float | None = None
    coverage_pct: float | None = None


class SimulateRequest(BaseModel):
    cell_id: str
    scenarios: list[ScenarioInput]


class ScenarioResult(BaseModel):
    intervention: InterventionType
    delta_pct: float | None = None
    coverage_pct: float | None = None
    projected_temp_c: float
    cooling_c: float


class SimulateResponse(BaseModel):
    cell_id: str
    baseline_temp_c: float
    results: list[ScenarioResult]
    combined_projected_temp_c: float | None = None
    combined_cooling_c: float | None = None


class PriorityItem(BaseModel):
    rank: int
    cell_id: str
    heat_stress_score: float
    intervention_roi: float
    recommended_action: str
    expected_cooling_c: float
    priority_score: float


class PriorityResponse(BaseModel):
    city: str
    rankings: list[PriorityItem]


class SettingsStatusResponse(BaseModel):
    openweather_configured: bool
    google_maps_configured: bool
    gemini_configured: bool
    mistral_configured: bool
    ai_provider: str
    ml_model: str
    demo_city: str


class SettingsUpdateRequest(BaseModel):
    openweather_api_key: str | None = None
    google_maps_api_key: str | None = None
    gemini_api_key: str | None = None
    mistral_api_key: str | None = None


class LocationAnalyzeRequest(BaseModel):
    location_query: str | None = Field(
        default=None,
        description="City or address to geocode via Google Maps (e.g. 'Delhi, India')",
    )
    bbox: list[float] | None = Field(
        default=None,
        description="Optional bounding box: min_lon, min_lat, max_lon, max_lat",
    )
    city: str | None = Field(default=None, description="City name when using bbox only")
    openweather_api_key: str | None = None
    google_maps_api_key: str | None = None
    grid_rows: int = Field(default=8, ge=4, le=16)
    grid_cols: int = Field(default=8, ge=4, le=16)


class LocationAnalyzeResponse(BaseModel):
    city: str
    formatted_address: str
    bbox: list[float]
    base_temperature_c: float
    cells_created: int
    ml_hotspot_count: int
    ml_model: str
    data_source: str = "live"
    hotspots: HotspotsResponse


class DashboardResponse(BaseModel):
    city: str
    formatted_address: str
    data_source: str = "live"
    base_temperature_c: float
    ml_hotspot_count: int
    ml_model: str
    hotspots: HotspotsResponse
    priority: PriorityResponse
