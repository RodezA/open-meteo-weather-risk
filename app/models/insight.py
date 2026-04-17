from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.engine.risk import RiskLevel


class ActivityStatusOut(BaseModel):
    activity: str
    allowed: bool
    reason: Optional[str] = None


class HourlyRiskOut(BaseModel):
    time: str
    risk_score: int
    risk_level: RiskLevel
    activities: List[ActivityStatusOut]
    primary_driver: str


class SiteRiskResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    timezone_abbreviation: str
    forecast_days: int
    hourly_risk: List[HourlyRiskOut]
    peak_risk_level: RiskLevel
    peak_risk_hour: str
