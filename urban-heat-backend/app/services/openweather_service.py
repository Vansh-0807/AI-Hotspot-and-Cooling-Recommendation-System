"""Fetch live temperature data from OpenWeatherMap."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

logger = logging.getLogger(__name__)

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class OpenWeatherService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenWeather API key is required for live temperature data")
        self.api_key = api_key

    def fetch_temperature_c_sync(self, lat: float, lon: float) -> float:
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        with httpx.Client(timeout=30) as client:
            response = client.get(OPENWEATHER_URL, params=params)
            if response.status_code == 401:
                raise ValueError("Invalid OpenWeather API key")
            if response.status_code != 200:
                raise ValueError(f"OpenWeather error: {response.status_code} — {response.text[:200]}")
            data = response.json()
            return round(float(data["main"]["temp"]), 2)

    def fetch_temperatures_batch(
        self,
        points: list[tuple[float, float]],
        max_workers: int = 6,
    ) -> dict[tuple[float, float], float]:
        """Fetch live temperature at each grid centroid (parallel, rate-limit friendly)."""
        if not points:
            return {}

        unique = list(dict.fromkeys(points))
        results: dict[tuple[float, float], float] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self.fetch_temperature_c_sync, lat, lon): (lat, lon)
                for lat, lon in unique
            }
            for future in as_completed(futures):
                key = futures[future]
                results[key] = future.result()

        return results
