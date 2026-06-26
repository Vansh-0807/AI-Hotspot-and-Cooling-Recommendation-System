"""Google Maps Geocoding API — resolve city names to coordinates and bounding boxes."""

import logging

import httpx

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


class GoogleMapsService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Maps API key is required for location search")
        self.api_key = api_key

    def geocode(self, query: str) -> dict:
        params = {"address": query, "key": self.api_key}
        with httpx.Client(timeout=30) as client:
            response = client.get(GEOCODE_URL, params=params)
            if response.status_code != 200:
                raise ValueError(f"Google Geocoding error: {response.status_code}")
            data = response.json()
            if data.get("status") == "REQUEST_DENIED":
                raise ValueError(f"Google Maps API denied: {data.get('error_message', 'check API key')}")
            if data.get("status") != "OK" or not data.get("results"):
                raise ValueError(f"Location not found: {query}")

            result = data["results"][0]
            location = result["geometry"]["location"]
            lat, lon = location["lat"], location["lng"]

            viewport = result["geometry"].get("viewport", {})
            if viewport:
                ne = viewport.get("northeast", {})
                sw = viewport.get("southwest", {})
                bbox = (
                    sw.get("lng", lon - 0.1),
                    sw.get("lat", lat - 0.1),
                    ne.get("lng", lon + 0.1),
                    ne.get("lat", lat + 0.1),
                )
            else:
                bbox = (lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05)

            city_name = result.get("formatted_address", query)
            return {
                "city": city_name.split(",")[0].strip(),
                "formatted_address": city_name,
                "lat": lat,
                "lon": lon,
                "bbox": bbox,
            }
