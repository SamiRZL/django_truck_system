import requests
from config import settings

def call_routes_api(origin, destination, waypoints=None, mode="DRIVE"):
    """Call Google Routes API v2 and return parsed JSON."""
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "routes.distanceMeters,"
            "routes.duration,"
            "routes.legs,"
            "routes.polyline.encodedPolyline"
        ),
    }

    body = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": mode,
    }
    if waypoints:
        body["intermediates"] = [{"address": w} for w in waypoints]

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def reverse_geocode(lat, lng):
    """Return formatted address from lat/lng using Google Geocoding API."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lng}", "key": settings.GOOGLE_MAPS_API_KEY}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0]["formatted_address"] if results else None
