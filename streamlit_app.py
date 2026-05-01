import asyncio
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st
from app.clients.weather import fetch_weather
from app.engine.risk import assess_hourly_risk, RiskLevel

_LEVEL_ORDER = {RiskLevel.GREEN: 0, RiskLevel.CAUTION: 1, RiskLevel.STOP: 2}

RISK_COLORS = {
    "GREEN": "#2d7a2d",
    "CAUTION": "#b87a00",
    "STOP": "#cc2222",
}

RISK_BG = {
    "GREEN": "#e6f4e6",
    "CAUTION": "#fff3cd",
    "STOP": "#fde8e8",
}

ACTIVITY_ICONS = {
    "crane": "🏗️",
    "exterior": "🦺",
    "electrical": "⚡",
    "general": "👷",
}


def fetch_risk(lat: float, lon: float, days: int) -> dict:
    weather = asyncio.run(fetch_weather(lat=lat, lon=lon, forecast_days=days))
    hourly_risks = assess_hourly_risk(weather.hourly)
    peak = max(hourly_risks, key=lambda r: (_LEVEL_ORDER[r.risk_level], r.risk_score))
    return {
        "latitude": weather.latitude,
        "longitude": weather.longitude,
        "timezone": weather.timezone,
        "timezone_abbreviation": weather.timezone_abbreviation,
        "forecast_days": days,
        "peak_risk_level": peak.risk_level.value,
        "peak_risk_hour": peak.time,
        "hourly_risk": [
            {
                "time": r.time,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level.value,
                "primary_driver": r.primary_driver,
                "activities": [
                    {"activity": a.activity, "allowed": a.allowed, "reason": a.reason}
                    for a in r.activities
                ],
            }
            for r in hourly_risks
        ],
    }


def risk_badge(level: str) -> str:
    color = RISK_COLORS[level]
    bg = RISK_BG[level]
    return (
        f'<span style="background:{bg};color:{color};padding:2px 10px;'
        f'border-radius:12px;font-weight:700;font-size:0.85rem;">{level}</span>'
    )


def render_activity_pills(activities: list) -> str:
    parts = []
    for a in activities:
        icon = ACTIVITY_ICONS.get(a["activity"], "")
        if a["allowed"]:
            parts.append(
                f'<span style="background:#e6f4e6;color:#2d7a2d;padding:1px 8px;'
                f'border-radius:10px;font-size:0.8rem;margin-right:4px">{icon} {a["activity"]}</span>'
            )
        else:
            parts.append(
                f'<span style="background:#fde8e8;color:#cc2222;padding:1px 8px;'
                f'border-radius:10px;font-size:0.8rem;margin-right:4px;text-decoration:line-through">'
                f'{icon} {a["activity"]}</span>'
            )
    return "".join(parts)


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Simplesense — Site Risk",
    page_icon="🏗️",
    layout="wide",
)


st.title("Construction Site Weather Risk")
st.caption("Hourly work-stoppage risk powered by Open-Meteo · OSHA 1926.1417 / 1910.333")

# ── Session state defaults ────────────────────────────────────────────────────

if "lat" not in st.session_state:
    st.session_state.lat = 40.7128
if "lon" not in st.session_state:
    st.session_state.lon = -74.0060
if "selected_city" not in st.session_state:
    st.session_state.selected_city = "New York, NY"

# ── Sidebar inputs ────────────────────────────────────────────────────────────

PRESETS = {
    "New York, NY": (40.7128, -74.0060),
    "Chicago, IL": (41.8781, -87.6298),
    "Houston, TX": (29.7604, -95.3698),
    "Miami, FL": (25.7617, -80.1918),
    "Denver, CO": (39.7392, -104.9903),
}

with st.sidebar:
    st.image("open_meteo_logo.png", width=160)
    st.header("Site Location")

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] .stButton > button {
            padding-top: 0.2rem !important;
            padding-bottom: 0.2rem !important;
            font-size: 0.8rem !important;
            line-height: 1.3 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**Quick locations**")
    for city, (plat, plon) in PRESETS.items():
        is_selected = st.session_state.selected_city == city
        label = f"✓ {city}" if is_selected else city
        if st.button(label, use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state.lat = plat
            st.session_state.lon = plon
            st.session_state.selected_city = city
            st.rerun()

    run = st.button("Get Risk Assessment", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("**Custom coordinates**")
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input("Latitude", value=st.session_state.lat, min_value=-90.0, max_value=90.0, format="%.4f")
    with col2:
        lon = st.number_input("Longitude", value=st.session_state.lon, min_value=-180.0, max_value=180.0, format="%.4f")

    if lat != st.session_state.lat or lon != st.session_state.lon:
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.session_state.selected_city = "Custom"

    days = st.slider("Forecast days", min_value=1, max_value=7, value=1)

# ── Main content ──────────────────────────────────────────────────────────────

if run:
    with st.spinner("Fetching weather and computing risk..."):
        try:
            data = fetch_risk(st.session_state.lat, st.session_state.lon, days)
        except Exception as exc:
            st.error(f"Error fetching weather data: {exc}")
            st.stop()

    hourly = data["hourly_risk"]
    peak_level = data["peak_risk_level"]
    peak_hour = data["peak_risk_hour"]

    # ── Summary banner ────────────────────────────────────────────────────────
    peak_color = RISK_COLORS[peak_level]
    peak_bg = RISK_BG[peak_level]
    st.markdown(
        f'<div style="background:{peak_bg};border-left:5px solid {peak_color};'
        f'padding:14px 18px;border-radius:6px;margin-bottom:1rem">'
        f'<span style="font-size:1.1rem;font-weight:600;color:{peak_color}">Peak risk: {peak_level}</span>'
        f'<span style="color:#555;margin-left:16px">at {datetime.fromisoformat(peak_hour).strftime("%-I:%M %p, %b %-d")} ({data["timezone_abbreviation"]})</span>'
        f'<br><span style="color:#666;font-size:0.85rem">📍 {st.session_state.selected_city} &nbsp;·&nbsp; {data["latitude"]:.4f}, {data["longitude"]:.4f}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Risk score chart ──────────────────────────────────────────────────────
    st.subheader("Risk score by hour")

    tz_abbr = data["timezone_abbreviation"] if "timezone_abbreviation" in data else "MST"
    times = [h["time"].split("T")[1] for h in hourly]
    scores = [h["risk_score"] for h in hourly]
    levels = [h["risk_level"] for h in hourly]

    bar_colors = [RISK_COLORS[lvl] for lvl in levels]
    fig = go.Figure(go.Bar(x=times, y=scores, marker_color=bar_colors))
    fig.update_layout(
        height=220,
        margin=dict(t=10, b=10, l=0, r=0),
        xaxis_title=f"Hour ({tz_abbr})",
        yaxis_title="Risk Score",
        yaxis_range=[0, 100],
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Hourly detail table ───────────────────────────────────────────────────
    st.subheader("Hourly breakdown")

    header_cols = st.columns([1.2, 0.9, 1.5, 3.5, 3.5])
    header_cols[0].markdown(f"**Hour ({tz_abbr})**")
    header_cols[1].markdown("**Score**")
    header_cols[2].markdown("**Level**")
    header_cols[3].markdown("**Primary driver**")
    header_cols[4].markdown("**Activities**")

    st.markdown('<hr style="margin:4px 0 8px">', unsafe_allow_html=True)

    for h in hourly:
        row = st.columns([1.2, 0.9, 1.5, 3.5, 3.5])
        hour_label = h["time"].split("T")[1]
        row[0].markdown(hour_label)
        row[1].markdown(f'**{h["risk_score"]}**')
        row[2].markdown(risk_badge(h["risk_level"]), unsafe_allow_html=True)
        row[3].markdown(h["primary_driver"])
        row[4].markdown(render_activity_pills(h["activities"]), unsafe_allow_html=True)

    # ── Activity legend ───────────────────────────────────────────────────────
    with st.expander("OSHA thresholds reference"):
        st.markdown("""
| Activity | Restriction trigger |
|---|---|
| 🏗️ Crane | Suspended: sustained wind >30 mph or gusts >35 mph (OSHA 1926.1417) |
| 🦺 Exterior | Suspended: wind >40 mph or thunderstorm |
| ⚡ Electrical | Suspended: any active precipitation (OSHA 1910.333) |
| 👷 General | Suspended: STOP-level conditions or thunderstorm |
        """)
