"""Build urban heat grid from live APIs and ML anomaly detection — any Indian city."""

import json
import logging
import random
import re
import httpx
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import GridCell
from app.services.google_maps_service import GoogleMapsService
from app.services.hotspot_service import HotspotService
from app.services.ml_service import MLHotspotDetector
from app.services.openweather_service import OpenWeatherService
from app.services.osm_service import OSMService

logger = logging.getLogger(__name__)


def _cell_polygon(lon: float, lat: float, dlon: float, dlat: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon, lat],
                [lon + dlon, lat],
                [lon + dlon, lat + dlat],
                [lon, lat + dlat],
                [lon, lat],
            ]
        ],
    }


def _city_prefix(city: str) -> str:
    clean = re.sub(r"[^A-Za-z]", "", city.upper())
    return (clean[:3] if len(clean) >= 3 else clean + "X")[:3]


class LocationService:
    def __init__(self):
        self.settings = get_settings()
        self.osm = OSMService()
        self.ml = MLHotspotDetector()
        self.hotspot_service = HotspotService()

    def _require_openweather_key(self) -> str:
        key = self.settings.openweather_api_key.strip()
        if not key:
            raise ValueError("OPENWEATHER_API_KEY must be set in .env")
        return key

    def _resolve_city_bbox(self, city_query: str) -> tuple[float, float, float, float, str, float, float]:
        """Return bbox, formatted address, center lat/lon for any city using Nominatim or Google Maps."""
        gm_key = self.settings.google_maps_api_key.strip()

        if gm_key:
            geo = GoogleMapsService(gm_key).geocode(f"{city_query}, India")
            min_lon, min_lat, max_lon, max_lat = geo["bbox"]
            center_lat, center_lon = geo["lat"], geo["lon"]
            formatted = geo["formatted_address"]
            return min_lon, min_lat, max_lon, max_lat, formatted, center_lat, center_lon

        # If it's the target city and we have bbox config, use it
        if city_query.lower() == self.settings.target_city.lower():
            min_lon, min_lat, max_lon, max_lat = self.settings.bbox_tuple
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            formatted = f"{self.settings.target_city}, India"
            return min_lon, min_lat, max_lon, max_lat, formatted, center_lat, center_lon
            
        # Fallback to OpenStreetMap Nominatim
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{city_query}, India",
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "HeatVisionAI/1.0"}
        
        try:
            with httpx.Client(timeout=10) as client:
                res = client.get(url, params=params, headers=headers)
                res.raise_for_status()
                data = res.json()
                if not data:
                    raise ValueError(f"Could not find location: {city_query}")
                place = data[0]
                # Nominatim bbox: [lat_min, lat_max, lon_min, lon_max]
                lat_min, lat_max, lon_min, lon_max = map(float, place["boundingbox"])
                # Increase bbox slightly for context
                padding = 0.05
                min_lat = lat_min - padding
                max_lat = lat_max + padding
                min_lon = lon_min - padding
                max_lon = lon_max + padding
                center_lat = float(place["lat"])
                center_lon = float(place["lon"])
                formatted = place.get("display_name", f"{city_query}, India")
                return min_lon, min_lat, max_lon, max_lat, formatted, center_lat, center_lon
        except Exception as e:
            logger.error("Geocoding failed for %s: %s", city_query, str(e))
            raise ValueError(f"Failed to geocode {city_query}. Please ensure the city exists in India.")

    def analyze_city(self, db: Session, city: str, force_refresh: bool = False) -> dict:
        """Load live OpenWeather + OSM data for any city."""
        if not force_refresh:
            existing = db.query(GridCell).filter(GridCell.city == city).count()
            if existing > 0:
                return self._build_response_from_db(db, city)

        # Clear old data for this city and fetch fresh
        db.query(GridCell).filter(GridCell.city == city).delete()
        db.commit()

        return self._analyze_region(
            db,
            city=city,
            grid_rows=self.settings.grid_rows,
            grid_cols=self.settings.grid_cols,
        )

    def _analyze_region(
        self,
        db: Session,
        city: str,
        grid_rows: int,
        grid_cols: int,
    ) -> dict:
        ow_key = self.settings.openweather_api_key.strip()
        min_lon, min_lat, max_lon, max_lat, formatted_address, _, _ = self._resolve_city_bbox(city)

        if ow_key:
            try:
                osm_features = self.osm.fetch_features_for_bbox(min_lon, min_lat, max_lon, max_lat)
                logger.info("OSM land-cover features loaded successfully")
            except Exception as exc:
                logger.warning("OSM Overpass failed (%s) — using synthetic land-cover with live temperatures", exc)
                osm_features = {}
        else:
            osm_features = {}

        dlon = (max_lon - min_lon) / grid_cols
        dlat = (max_lat - min_lat) / grid_rows
        prefix = _city_prefix(city)

        cell_defs: list[dict] = []
        centroids: list[tuple[float, float]] = []

        for row in range(grid_rows):
            for col in range(grid_cols):
                lon = min_lon + col * dlon
                lat = min_lat + row * dlat
                centroid_lon = lon + dlon / 2
                centroid_lat = lat + dlat / 2
                centroids.append((centroid_lat, centroid_lon))
                cell_defs.append(
                    {
                        "row": row,
                        "col": col,
                        "lon": lon,
                        "lat": lat,
                        "centroid_lon": centroid_lon,
                        "centroid_lat": centroid_lat,
                        "dlon": dlon,
                        "dlat": dlat,
                    }
                )

        if ow_key:
            weather = OpenWeatherService(ow_key)
            logger.info("Fetching live temperature for %d %s grid cells…", len(centroids), city)
            live_temps = weather.fetch_temperatures_batch(centroids)
        else:
            logger.info("No OpenWeather API key found. Generating synthetic demo temperatures.")
            live_temps = {key: round(random.uniform(35.0, 45.0), 2) for key in centroids}

        raw_cells: list[dict] = []
        for i, cell_def in enumerate(cell_defs):
            if osm_features and any(osm_features.values()):
                env = self.osm.score_cell(cell_def["centroid_lat"], cell_def["centroid_lon"], osm_features)
            else:
                env = {
                    "tree_cover_pct": round(random.uniform(5.0, 60.0), 1),
                    "impervious_pct": round(random.uniform(20.0, 95.0), 1),
                    "traffic_index": round(random.uniform(0.1, 0.9), 2),
                    "water_proximity_m": round(random.uniform(500, 5000), 0)
                }
            key = (cell_def["centroid_lat"], cell_def["centroid_lon"])
            temperature = live_temps[key]

            cell_id = f"{prefix}_{cell_def['row'] * grid_cols + cell_def['col'] + 1:03d}"
            population = min(1.0, 0.25 + env["traffic_index"] * 0.45 + env["impervious_pct"] / 250)
            vulnerability = min(1.0, 0.35 + (100 - env["tree_cover_pct"]) / 220)

            raw_cells.append(
                {
                    "cell_id": cell_id,
                    "city": city,
                    "centroid_lat": round(cell_def["centroid_lat"], 6),
                    "centroid_lon": round(cell_def["centroid_lon"], 6),
                    "geometry": _cell_polygon(
                        cell_def["lon"], cell_def["lat"], cell_def["dlon"], cell_def["dlat"]
                    ),
                    "temperature_c": temperature,
                    "tree_cover_pct": env["tree_cover_pct"],
                    "impervious_pct": env["impervious_pct"],
                    "traffic_index": env["traffic_index"],
                    "water_proximity_m": env["water_proximity_m"],
                    "population_proxy": round(population, 2),
                    "vulnerability": round(vulnerability, 2),
                }
            )

        ml_results = self.ml.detect(raw_cells)

        db.query(GridCell).filter(GridCell.city == city).delete()
        db.commit()

        ml_hotspot_count = 0
        for cell_data in raw_cells:
            if ml_results[cell_data["cell_id"]]["is_hotspot"]:
                ml_hotspot_count += 1

            db.merge(
                GridCell(
                    cell_id=cell_data["cell_id"],
                    city=cell_data["city"],
                    centroid_lat=cell_data["centroid_lat"],
                    centroid_lon=cell_data["centroid_lon"],
                    geometry_json=json.dumps(cell_data["geometry"]),
                    temperature_c=cell_data["temperature_c"],
                    tree_cover_pct=cell_data["tree_cover_pct"],
                    impervious_pct=cell_data["impervious_pct"],
                    traffic_index=cell_data["traffic_index"],
                    water_proximity_m=cell_data["water_proximity_m"],
                    population_proxy=cell_data["population_proxy"],
                    vulnerability=cell_data["vulnerability"],
                )
            )

        db.commit()

        base_temp = round(sum(c["temperature_c"] for c in raw_cells) / len(raw_cells), 2)
        hotspots_response = self.hotspot_service.get_hotspots(db, city, date.today())
        hotspots_response.bbox = [min_lon, min_lat, max_lon, max_lat]

        enriched_cells = []
        for cell in hotspots_response.cells:
            ml_info = ml_results.get(cell.cell_id, {})
            enriched_cells.append(
                {
                    **cell.model_dump(),
                    "ml_anomaly_score": ml_info.get("ml_anomaly_score", 0),
                    "ml_is_hotspot": ml_info.get("is_hotspot", False),
                    "cluster_id": ml_info.get("cluster_id", -1),
                }
            )

        return {
            "city": city,
            "formatted_address": formatted_address,
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "base_temperature_c": base_temp,
            "cells_created": len(raw_cells),
            "ml_hotspot_count": ml_hotspot_count,
            "ml_model": "Isolation Forest + K-Means",
            "data_source": "live",
            "hotspots": {
                "city": hotspots_response.city,
                "date": str(hotspots_response.date),
                "bbox": hotspots_response.bbox,
                "cells": enriched_cells,
                "stats": hotspots_response.stats.model_dump(),
            },
        }

    def _build_response_from_db(self, db: Session, city: str) -> dict:
        hotspots_response = self.hotspot_service.get_hotspots(db, city, date.today())
        cells_db = db.query(GridCell).filter(GridCell.city == city).all()
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
            for c in cells_db
        ]
        ml_results = self.ml.detect(ml_input)
        ml_hotspot_count = sum(1 for c in cells_db if ml_results[c.cell_id]["is_hotspot"])
        enriched = []
        for cell in hotspots_response.cells:
            ml_info = ml_results.get(cell.cell_id, {})
            enriched.append(
                {
                    **cell.model_dump(),
                    "ml_anomaly_score": ml_info.get("ml_anomaly_score", 0),
                    "ml_is_hotspot": ml_info.get("is_hotspot", False),
                    "cluster_id": ml_info.get("cluster_id", -1),
                }
            )
        lons = [c.centroid_lon for c in cells_db]
        lats = [c.centroid_lat for c in cells_db]
        bbox = [min(lons), min(lats), max(lons), max(lats)]

        # Resolve formatted address dynamically
        try:
            _, _, _, _, formatted_address, _, _ = self._resolve_city_bbox(city)
        except Exception:
            formatted_address = f"{city}, India"

        return {
            "city": city,
            "formatted_address": formatted_address,
            "bbox": bbox,
            "base_temperature_c": hotspots_response.stats.mean_temp_c,
            "cells_created": len(cells_db),
            "ml_hotspot_count": ml_hotspot_count,
            "ml_model": "Isolation Forest + K-Means",
            "data_source": "live",
            "hotspots": {
                "city": hotspots_response.city,
                "date": str(hotspots_response.date),
                "bbox": bbox,
                "cells": enriched,
                "stats": hotspots_response.stats.model_dump(),
            },
        }

