from unittest.mock import patch

from app.services import geocode_service


def test_geocode_appends_atlanta_and_parses_lat_lng():
    payload = {
        "status": "OK",
        "results": [
            {
                "formatted_address": "Peachtree St NE, Atlanta, GA",
                "geometry": {"location": {"lat": 33.7591, "lng": -84.3875}},
            }
        ],
    }
    with patch("app.services.geocode_service.requests.get") as mocked:
        mocked.return_value.ok = True
        mocked.return_value.json.return_value = payload
        with patch.object(geocode_service.Config, "GOOGLE_MAPS_API_KEY", "maps-key"):
            result = geocode_service.geocode_location("Peachtree Street")
    assert result["latitude"] == 33.7591
    assert result["longitude"] == -84.3875
    assert "Atlanta" in result["google_maps"]
    params = mocked.call_args.kwargs["params"]
    assert "Atlanta" in params["address"]
