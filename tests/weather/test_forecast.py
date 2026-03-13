from unittest.mock import patch, MagicMock

from src.weather.forecast import fetch_weather, WeatherData

SAMPLE_RESPONSE = {
    "weather": [{"description": "ciel degagé", "id": 800}],
    "main": {"temp": 12.5, "temp_min": 8.0, "temp_max": 16.0},
    "name": "Fontenay-sous-Bois",
}

@patch("src.weather.forecast.requests.get")
def test_fetch_weather_returns_data(mock_get: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_get.return_value = mock_response

    result = fetch_weather(lat=48.8566, lon=2.4739, api_key="test-key")

    assert isinstance(result, WeatherData)
    assert result.city == "Fontenay-sous-Bois"
    assert result.temp_current == 12.5
    assert result.temp_min == 8.0
    assert result.temp_max == 16.0
    assert result.description == "ciel degagé"

@patch("src.weather.forecast.requests.get")
def test_fetch_weather_returns_none_on_error(mock_get: MagicMock):
    mock_get.side_effect = Exception("API down")
    result = fetch_weather(lat=0.0, lon=0.0, api_key="test")
    assert result is None
