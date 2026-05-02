# Open-Meteo — Construction Site Risk

A construction site weather risk engine that translates live forecast data into OSHA-compliant work-stoppage decisions — with a live deployed demo, async Python architecture, regulatory-grounded thresholds, and a pure-logic risk engine that's fully tested and framework-agnostic. It shows domain depth, not just coding ability.

## Live Demo

[https://open-meteo-weather-risk-jbgvmepvegrd7jtkk23nrz.streamlit.app/](https://open-meteo-weather-risk-jbgvmepvegrd7jtkk23nrz.streamlit.app/)

## Quickstart

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser. Select a preset city or enter custom coordinates, choose a forecast window (1–7 days), and click **Get Risk Assessment**.

## How It Works

```
Open-Meteo API  →  Weather Client  →  Risk Engine  →  Streamlit UI
(no API key)       (async httpx)      (pure Python)    (interactive)
```

The risk engine evaluates four independent factors per hour and sums them into a composite score (0–100):

| Factor | Max contribution | STOP trigger |
|---|---|---|
| Wind speed / gusts | 70 pts | ≥45 mph effective |
| Precipitation | 30 pts | >0.3 mm active |
| Visibility | 20 pts | <200 m |
| Weather code (WMO) | 70 pts | Thunderstorm (codes 95/96/99) |

## Risk Levels

| Level | Score | Meaning |
|---|---|---|
| GREEN | 0–39 | Normal operations |
| CAUTION | 40–69 | Elevated conditions — supervisors alerted |
| STOP | 70–100 | Work suspension required |

## Activity Restrictions

Evaluated independently from the composite score using direct OSHA threshold comparisons:

| Activity | Suspended when |
|---|---|
| Crane | Sustained wind >30 mph or gusts >35 mph (OSHA 1926.1417) |
| Exterior | Wind >40 mph or thunderstorm |
| Electrical | Any active precipitation (OSHA 1910.333) |
| General | STOP-level conditions or thunderstorm |

## Project Structure

```
app/
├── clients/weather.py   # Async httpx client — fetches Open-Meteo hourly forecast
├── engine/risk.py       # Pure Python risk engine — no framework dependency
└── models/              # Pydantic models for weather input and risk output
tests/
└── test_risk_engine.py  # Unit tests — scoring logic and activity restrictions
streamlit_app.py         # Entry point — wires client, engine, and UI
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Why Actionable Data Matters

Raw data doesn't make decisions — people do. But people operating under time pressure, regulatory exposure, or incomplete context need data that's already been interpreted for them. The gap between "here is a number" and "here is what to do" is where most data systems fall short.

This project is one example of closing that gap: a weather forecast is interesting; a work-stoppage decision tied to specific OSHA thresholds is useful. The same principle applies across domains:

- **Healthcare**: A patient's vitals feed becomes actionable when it surfaces an escalation flag before a nurse has to calculate it manually.
- **Logistics**: A shipment tracking stream becomes actionable when it predicts a delay and re-routes before a customer asks.
- **Finance**: A market data feed becomes actionable when it triggers a position review based on pre-defined risk parameters, not a dashboard someone has to monitor.

The pattern is consistent: take a domain with real consequences, understand the decision logic that experts already use, encode it explicitly, and put it in the path of the person who needs to act. The technology is secondary. The hard part is knowing the domain well enough to know what the right decision even is.

## Data Source

[Open-Meteo](https://open-meteo.com/) — free, no API key required. Forecasts update hourly. All wind values are in mph; visibility in meters.
