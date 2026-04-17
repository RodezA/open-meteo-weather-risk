import pytest
from app.engine.risk import assess_hourly_risk, RiskLevel
from app.models.weather import HourlyWeather


def _make_hourly(**overrides) -> HourlyWeather:
    """Build a single-hour HourlyWeather with safe defaults, overridable per-field."""
    defaults = dict(
        time=["2026-04-13T09:00"],
        temperature_2m=[20.0],
        apparent_temperature=[19.0],
        wind_speed_10m=[5.0],
        wind_gusts_10m=[8.0],
        precipitation_probability=[10],
        precipitation=[0.0],
        visibility=[10000.0],
        weather_code=[0],
    )
    defaults.update(overrides)
    return HourlyWeather(**defaults)


class TestGreenConditions:
    def test_calm_clear_day(self):
        result = assess_hourly_risk(_make_hourly())
        assert len(result) == 1
        assert result[0].risk_level == RiskLevel.GREEN
        assert result[0].risk_score < 40

    def test_all_activities_allowed_in_green(self):
        result = assess_hourly_risk(_make_hourly())
        for activity in result[0].activities:
            assert activity.allowed, f"{activity.activity} should be allowed in GREEN"


class TestWindThresholds:
    def test_crane_suspended_above_30mph(self):
        hourly = _make_hourly(wind_speed_10m=[31.0], wind_gusts_10m=[34.0])
        result = assess_hourly_risk(hourly)
        crane = next(a for a in result[0].activities if a.activity == "crane")
        assert not crane.allowed
        assert "OSHA" in crane.reason

    def test_crane_caution_between_20_and_30mph(self):
        hourly = _make_hourly(wind_speed_10m=[22.0], wind_gusts_10m=[26.0])
        result = assess_hourly_risk(hourly)
        crane = next(a for a in result[0].activities if a.activity == "crane")
        assert crane.allowed
        assert crane.reason is not None  # caution note present

    def test_gusts_trigger_crane_suspension(self):
        # Sustained wind is fine but gusts exceed 35 mph limit
        hourly = _make_hourly(wind_speed_10m=[20.0], wind_gusts_10m=[36.0])
        result = assess_hourly_risk(hourly)
        crane = next(a for a in result[0].activities if a.activity == "crane")
        assert not crane.allowed

    def test_extreme_wind_triggers_stop(self):
        hourly = _make_hourly(wind_speed_10m=[50.0], wind_gusts_10m=[60.0])
        result = assess_hourly_risk(hourly)
        assert result[0].risk_level == RiskLevel.STOP


class TestPrecipitation:
    def test_electrical_suspended_with_any_precipitation(self):
        hourly = _make_hourly(precipitation=[0.05])
        result = assess_hourly_risk(hourly)
        electrical = next(a for a in result[0].activities if a.activity == "electrical")
        assert not electrical.allowed
        assert "OSHA" in electrical.reason

    def test_electrical_allowed_with_zero_precipitation(self):
        hourly = _make_hourly(precipitation=[0.0], precipitation_probability=[30])
        result = assess_hourly_risk(hourly)
        electrical = next(a for a in result[0].activities if a.activity == "electrical")
        assert electrical.allowed

    def test_heavy_precip_raises_score(self):
        hourly = _make_hourly(precipitation=[0.5])
        result = assess_hourly_risk(hourly)
        assert result[0].risk_score >= 30


class TestSevereWeather:
    def test_thunderstorm_suspends_all_activities(self):
        hourly = _make_hourly(weather_code=[95])
        result = assess_hourly_risk(hourly)
        assert result[0].risk_level == RiskLevel.STOP
        for activity in result[0].activities:
            assert not activity.allowed, f"{activity.activity} should be suspended in thunderstorm"

    def test_thunderstorm_sets_stop_level(self):
        hourly = _make_hourly(weather_code=[99])
        result = assess_hourly_risk(hourly)
        assert result[0].risk_level == RiskLevel.STOP


class TestVisibility:
    def test_severe_low_visibility_raises_score(self):
        hourly = _make_hourly(visibility=[100.0])
        result = assess_hourly_risk(hourly)
        assert result[0].risk_score >= 20

    def test_good_visibility_no_contribution(self):
        hourly = _make_hourly(visibility=[10000.0])
        result = assess_hourly_risk(hourly)
        # visibility should contribute 0 to score
        assert result[0].risk_score < 20  # only background conditions


class TestMultiHour:
    def test_returns_one_result_per_hour(self):
        hourly = HourlyWeather(
            time=["2026-04-13T08:00", "2026-04-13T09:00", "2026-04-13T10:00"],
            temperature_2m=[15.0, 16.0, 17.0],
            apparent_temperature=[14.0, 15.0, 16.0],
            wind_speed_10m=[5.0, 10.0, 35.0],
            wind_gusts_10m=[8.0, 15.0, 45.0],
            precipitation_probability=[5, 10, 60],
            precipitation=[0.0, 0.0, 0.2],
            visibility=[10000.0, 8000.0, 500.0],
            weather_code=[0, 0, 61],
        )
        results = assess_hourly_risk(hourly)
        assert len(results) == 3
        # Last hour should be worst
        assert results[2].risk_score > results[0].risk_score
