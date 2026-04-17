"""
Construction Site Work Stoppage Risk Engine

Evaluates hourly weather conditions against OSHA and industry thresholds
and produces a composite risk score and per-activity work restrictions.

Risk levels:
  GREEN  (0–39)  — Normal operations
  CAUTION (40–69) — Heightened awareness, supervisors alerted
  STOP   (70–100) — Work suspension required

Activity categories and their primary thresholds (wind in mph):
  crane      — Most sensitive: OSHA 1926.1417 prohibits crane ops in
                wind > 30 mph or manufacturer limit, whichever is lower
  exterior   — General site work exposed to elements
  electrical — Zero-tolerance for precipitation (OSHA 1910.333)
  general    — All other ground-level site activity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from app.models.weather import HourlyWeather


class RiskLevel(str, Enum):
    GREEN = "GREEN"
    CAUTION = "CAUTION"
    STOP = "STOP"


# WMO weather codes that indicate severe/electrical storm conditions
SEVERE_WEATHER_CODES = {
    95,  # Thunderstorm
    96,  # Thunderstorm with slight hail
    99,  # Thunderstorm with heavy hail
}

HEAVY_SNOW_CODES = {71, 73, 75, 77}  # Slight/moderate/heavy snowfall, snow grains


@dataclass
class ActivityStatus:
    activity: str
    allowed: bool
    reason: Optional[str] = None


@dataclass
class HourlyRisk:
    time: str
    risk_score: int
    risk_level: RiskLevel
    activities: List[ActivityStatus]
    primary_driver: str  # The single factor most responsible for the score


def _score_wind(wind_speed: float, wind_gusts: float) -> Tuple[int, Optional[str]]:
    """Return (score contribution 0-40, reason) based on wind conditions."""
    # Gusts are weighted more than sustained — they're the acute hazard
    effective = max(wind_speed, wind_gusts * 0.8)

    if effective >= 45:
        return 70, "Extreme wind {:.0f} mph / gusts {:.0f} mph".format(wind_speed, wind_gusts)
    if effective >= 35:
        return 40, "High wind {:.0f} mph / gusts {:.0f} mph".format(wind_speed, wind_gusts)
    if effective >= 25:
        return 20, "Elevated wind {:.0f} mph / gusts {:.0f} mph".format(wind_speed, wind_gusts)
    if effective >= 15:
        return 8, None
    return 0, None


def _score_precipitation(precipitation: float, precip_probability: int) -> Tuple[int, Optional[str]]:
    """Return (score contribution 0-30, reason)."""
    if precipitation > 0.3:
        return 30, "Heavy precipitation {:.1f} mm".format(precipitation)
    if precipitation > 0.1:
        return 20, "Active precipitation {:.1f} mm".format(precipitation)
    if precip_probability >= 70:
        return 10, "High precipitation probability {}%".format(precip_probability)
    if precip_probability >= 40:
        return 5, None
    return 0, None


def _score_visibility(visibility_m: float) -> Tuple[int, Optional[str]]:
    """Return (score contribution 0-20, reason). Visibility in meters."""
    if visibility_m < 200:
        return 20, "Severe low visibility {:.0f}m".format(visibility_m)
    if visibility_m < 500:
        return 15, "Low visibility {:.0f}m".format(visibility_m)
    if visibility_m < 1000:
        return 8, "Reduced visibility {:.0f}m".format(visibility_m)
    return 0, None


def _score_weather_code(weather_code: int) -> Tuple[int, Optional[str]]:
    """Return (score contribution 0-30, reason) for severe event codes."""
    if weather_code in SEVERE_WEATHER_CODES:
        return 70, "Thunderstorm — all outdoor work suspended"
    if weather_code in HEAVY_SNOW_CODES:
        return 20, "Heavy snow event"
    return 0, None


def _activity_restrictions(
    wind_speed: float,
    wind_gusts: float,
    precipitation: float,
    weather_code: int,
    risk_score: int,
) -> List[ActivityStatus]:
    activities = []
    thunderstorm = weather_code in SEVERE_WEATHER_CODES
    has_precip = precipitation > 0.0

    # Crane — OSHA 1926.1417: suspend at sustained > 30 mph or gusts > 35 mph
    if thunderstorm or wind_speed > 30 or wind_gusts > 35:
        activities.append(ActivityStatus(
            activity="crane",
            allowed=False,
            reason=(
                "Thunderstorm" if thunderstorm
                else "Wind {:.0f} mph / gusts {:.0f} mph exceeds OSHA 1926.1417 limit".format(wind_speed, wind_gusts)
            ),
        ))
    elif wind_speed > 20 or wind_gusts > 25:
        activities.append(ActivityStatus(
            activity="crane",
            allowed=True,
            reason="Approaching wind limits — supervisor approval required",
        ))
    else:
        activities.append(ActivityStatus(activity="crane", allowed=True))

    # Exterior — suspend at extreme wind or severe weather
    if thunderstorm or wind_speed > 40:
        activities.append(ActivityStatus(
            activity="exterior",
            allowed=False,
            reason="Thunderstorm" if thunderstorm else "Extreme wind {:.0f} mph".format(wind_speed),
        ))
    elif risk_score >= 40:
        activities.append(ActivityStatus(
            activity="exterior",
            allowed=True,
            reason="Elevated conditions — PPE check required",
        ))
    else:
        activities.append(ActivityStatus(activity="exterior", allowed=True))

    # Electrical — zero tolerance for any precipitation (OSHA 1910.333)
    if thunderstorm or has_precip:
        activities.append(ActivityStatus(
            activity="electrical",
            allowed=False,
            reason="Thunderstorm" if thunderstorm else "Active precipitation — OSHA 1910.333",
        ))
    else:
        activities.append(ActivityStatus(activity="electrical", allowed=True))

    # General — suspend only in severe conditions
    if thunderstorm or risk_score >= 70:
        activities.append(ActivityStatus(
            activity="general",
            allowed=False,
            reason="Thunderstorm" if thunderstorm else "Extreme weather conditions",
        ))
    else:
        activities.append(ActivityStatus(activity="general", allowed=True))

    return activities


def _to_risk_level(score: int) -> RiskLevel:
    if score >= 70:
        return RiskLevel.STOP
    if score >= 40:
        return RiskLevel.CAUTION
    return RiskLevel.GREEN


def assess_hourly_risk(hourly: HourlyWeather) -> List[HourlyRisk]:
    results = []
    n = len(hourly.time)

    for i in range(n):
        wind_score, wind_reason = _score_wind(
            hourly.wind_speed_10m[i], hourly.wind_gusts_10m[i]
        )
        precip_score, precip_reason = _score_precipitation(
            hourly.precipitation[i], hourly.precipitation_probability[i]
        )
        vis_score, vis_reason = _score_visibility(hourly.visibility[i])
        code_score, code_reason = _score_weather_code(hourly.weather_code[i])

        raw_score = min(100, wind_score + precip_score + vis_score + code_score)

        # Determine primary driver (highest contributing factor)
        candidates = [
            (wind_reason, wind_score),
            (precip_reason, precip_score),
            (vis_reason, vis_score),
            (code_reason, code_score),
        ]
        labeled = [(r, s) for r, s in candidates if r is not None]
        primary_driver = max(labeled, key=lambda x: x[1])[0] if labeled else "Normal conditions"

        activities = _activity_restrictions(
            wind_speed=hourly.wind_speed_10m[i],
            wind_gusts=hourly.wind_gusts_10m[i],
            precipitation=hourly.precipitation[i],
            weather_code=hourly.weather_code[i],
            risk_score=raw_score,
        )

        results.append(HourlyRisk(
            time=hourly.time[i],
            risk_score=raw_score,
            risk_level=_to_risk_level(raw_score),
            activities=activities,
            primary_driver=primary_driver,
        ))

    return results
