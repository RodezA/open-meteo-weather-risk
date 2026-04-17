from __future__ import annotations

from typing import List

from pydantic import BaseModel


class CurrentWeather(BaseModel):
    time: str
    temperature_2m: float
    apparent_temperature: float
    wind_speed_10m: float
    wind_gusts_10m: float
    precipitation: float
    visibility: float
    weather_code: int


class HourlyWeather(BaseModel):
    time: List[str]
    temperature_2m: List[float]
    apparent_temperature: List[float]
    wind_speed_10m: List[float]
    wind_gusts_10m: List[float]
    precipitation_probability: List[int]
    precipitation: List[float]
    visibility: List[float]
    weather_code: List[int]


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    current: CurrentWeather
    hourly: HourlyWeather
