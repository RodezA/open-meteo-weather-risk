import httpx
from app.models.weather import WeatherResponse

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "wind_speed_10m",
    "wind_gusts_10m",
    "precipitation_probability",
    "precipitation",
    "visibility",
    "weather_code",
]

CURRENT_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "wind_speed_10m",
    "wind_gusts_10m",
    "precipitation",
    "visibility",
    "weather_code",
]


async def fetch_weather(
    lat: float,
    lon: float,
    forecast_days: int = 1,
    timezone: str = "America/Denver",
) -> WeatherResponse:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(CURRENT_VARS),
        "hourly": ",".join(HOURLY_VARS),
        "forecast_days": forecast_days,
        "wind_speed_unit": "mph",
        "visibility_unit": "m",
        "timezone": timezone,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        return WeatherResponse.model_validate(response.json())
