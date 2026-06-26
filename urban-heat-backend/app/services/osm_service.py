"""OpenStreetMap Overpass API — environmental features per grid cell."""

import logging
import math
import time

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class OSMService:
    def fetch_features_for_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict:
        query = f"""
        [out:json][timeout:45];
        (
          way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["highway"~"primary|secondary|tertiary|trunk|residential"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["natural"="water"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["landuse"~"forest|park|grass|recreation_ground"]({min_lat},{min_lon},{max_lat},{max_lon});
          way["leisure"~"park|garden"]({min_lat},{min_lon},{max_lat},{max_lon});
        );
        out center;
        """

        last_error: Exception | None = None
        for attempt, base_url in enumerate(OVERPASS_MIRRORS):
            try:
                with httpx.Client(timeout=8.0) as client:
                    response = client.post(base_url, content=query)
                    if response.status_code == 429:
                        time.sleep(2 + attempt)
                        continue
                    if response.status_code != 200:
                        raise ValueError(f"Overpass HTTP {response.status_code}")
                    data = response.json()
                    parsed = self._parse_elements(data)
                    if not any(parsed.values()):
                        logger.warning("Overpass returned no features for bbox — counts will reflect sparse OSM coverage")
                    return parsed
            except Exception as exc:
                last_error = exc
                logger.warning("Overpass attempt %d failed: %s", attempt + 1, exc)
                time.sleep(1.5)

        raise ValueError(f"OpenStreetMap Overpass failed — cannot build live land-cover grid: {last_error}")

    def _parse_elements(self, data: dict) -> dict:
        buildings, roads, water, green = [], [], [], []
        for element in data.get("elements", []):
            center = element.get("center", {})
            if not center:
                continue
            lat, lon = center.get("lat"), center.get("lon")
            if lat is None or lon is None:
                continue
            tags = element.get("tags", {})
            if "building" in tags:
                buildings.append((lat, lon))
            elif "highway" in tags:
                roads.append((lat, lon))
            elif tags.get("natural") == "water":
                water.append((lat, lon))
            elif tags.get("landuse") in ("forest", "park", "grass", "recreation_ground"):
                green.append((lat, lon))
            elif tags.get("leisure") in ("park", "garden"):
                green.append((lat, lon))

        return {"buildings": buildings, "roads": roads, "water": water, "green": green}

    def score_cell(
        self,
        lat: float,
        lon: float,
        features: dict,
        cell_radius_m: float = 400,
    ) -> dict:
        buildings = features.get("buildings", [])
        roads = features.get("roads", [])
        water = features.get("water", [])
        green = features.get("green", [])

        def count_near(points: list) -> int:
            return sum(1 for plat, plon in points if _haversine_m(lat, lon, plat, plon) <= cell_radius_m)

        b_count = count_near(buildings)
        r_count = count_near(roads)
        g_count = count_near(green)

        tree_cover = min(65.0, round(g_count * 5.5, 1))
        impervious = min(98.0, round(b_count * 3.5 + r_count * 2.5, 1))
        traffic = min(1.0, round(r_count * 0.1, 2))

        water_dist = 5000.0
        for plat, plon in water:
            water_dist = min(water_dist, _haversine_m(lat, lon, plat, plon))

        return {
            "tree_cover_pct": tree_cover,
            "impervious_pct": impervious,
            "traffic_index": traffic,
            "water_proximity_m": round(water_dist, 0),
        }
