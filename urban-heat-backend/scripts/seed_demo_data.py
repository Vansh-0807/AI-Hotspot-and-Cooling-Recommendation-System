"""DEPRECATED: Raipur uses live OpenWeather + OSM only. Do not run this script."""

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.db.database import SessionLocal, init_db  # noqa: E402
from app.db.models import GridCell  # noqa: E402


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


def seed(db=None, city: str | None = None, rows: int = 8, cols: int = 8) -> int:
    settings = get_settings()
    target_city = city or settings.demo_city
    min_lon, min_lat, max_lon, max_lat = settings.bbox_tuple

    dlon = (max_lon - min_lon) / cols
    dlat = (max_lat - min_lat) / rows

    rng = random.Random(42)
    created = 0
    close_db = False

    if db is None:
        init_db()
        db = SessionLocal()
        close_db = True
        db.query(GridCell).filter(GridCell.city == target_city).delete()
        db.commit()

    for row in range(rows):
        for col in range(cols):
            lon = min_lon + col * dlon
            lat = min_lat + row * dlat
            centroid_lon = lon + dlon / 2
            centroid_lat = lat + dlat / 2

            # Synthetic heat island pattern: center + NE industrial zone hotter
            cx = (centroid_lon - (min_lon + max_lon) / 2) / (max_lon - min_lon)
            cy = (centroid_lat - (min_lat + max_lat) / 2) / (max_lat - min_lat)
            dist = math.sqrt(cx**2 + cy**2)
            industrial = 1.0 if cx > 0.1 and cy > 0.1 else 0.0

            tree_cover = max(5, min(45, 28 - dist * 25 - industrial * 15 + rng.uniform(-5, 5)))
            impervious = min(95, max(40, 100 - tree_cover + industrial * 20 + rng.uniform(-5, 10)))
            traffic = min(1.0, max(0.1, 0.3 + industrial * 0.5 + dist * 0.4 + rng.uniform(-0.1, 0.1)))
            water_dist = max(100, 800 - tree_cover * 15 + rng.uniform(-200, 400))

            base_temp = 33.0 + dist * 4 + industrial * 3 + (100 - tree_cover) * 0.05
            temperature = base_temp + rng.uniform(-0.8, 0.8)

            cell_id = f"BHP_{row * cols + col + 1:03d}"
            population = min(1.0, 0.3 + industrial * 0.5 + dist * 0.3)
            vulnerability = min(1.0, 0.4 + (100 - tree_cover) / 200)

            cell = GridCell(
                cell_id=cell_id,
                city=target_city,
                centroid_lat=round(centroid_lat, 6),
                centroid_lon=round(centroid_lon, 6),
                geometry_json=json.dumps(_cell_polygon(lon, lat, dlon, dlat)),
                temperature_c=round(temperature, 2),
                tree_cover_pct=round(tree_cover, 1),
                impervious_pct=round(impervious, 1),
                traffic_index=round(traffic, 2),
                water_proximity_m=round(water_dist, 0),
                population_proxy=round(population, 2),
                vulnerability=round(vulnerability, 2),
            )
            db.merge(cell)
            created += 1

    db.commit()
    if close_db:
        db.close()
    return created


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} grid cells for {get_settings().demo_city}")
