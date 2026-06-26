from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openweather_api_key: str = ""
    google_maps_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""
    openai_api_key: str = ""

    # Raipur-only region (no demo / synthetic cities)
    target_city: str = "Raipur"
    target_location_query: str = "Raipur, Chhattisgarh, India"
    target_bbox: str = "81.58,21.20,81.72,21.32"
    grid_rows: int = 8
    grid_cols: int = 8

    database_url: str = "sqlite:///urban_heat.db"
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501,http://localhost:8080"

    cooling_tree_per_10pct: float = 0.8
    cooling_roof_per_30pct: float = 1.0
    cooling_pavement_per_20pct: float = 0.5
    max_cooling_c: float = 4.0

    severity_high_c: float = 2.5
    severity_medium_c: float = 1.5

    @property
    def demo_city(self) -> str:
        """Backward-compatible alias used by older routes."""
        return self.target_city

    @property
    def bbox_tuple(self) -> tuple[float, float, float, float]:
        parts = [float(x.strip()) for x in self.target_bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("TARGET_BBOX must be min_lon,min_lat,max_lon,max_lat")
        return parts[0], parts[1], parts[2], parts[3]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
