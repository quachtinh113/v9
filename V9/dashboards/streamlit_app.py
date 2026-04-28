import streamlit as st
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(os.path.dirname(__file__)).resolve().parent
sys.path.append(str(ROOT_DIR))

from src.dashboard.data_loader import load_yaml, get_all_projects_data
from src.dashboard.alerts import check_alerts

st.set_page_config(
    page_title="Quant V9 Operating Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load configurations
dashboard_config = load_yaml(ROOT_DIR / "configs" / "dashboard_config.yaml")
risk_config = load_yaml(ROOT_DIR / "configs" / "risk_config.yaml")

# Load data
data = get_all_projects_data(dashboard_config)

# Check alerts
alerts = check_alerts(data, risk_config, dashboard_config)

# Sidebar
st.sidebar.title("V9 Quant Terminal")
st.sidebar.markdown("---")

if alerts:
    st.sidebar.error(f"🚨 ACTIVE ALERTS ({len(alerts)})")
    for alert in alerts:
        if alert["level"] == "CRITICAL":
            st.sidebar.error(alert["msg"])
        else:
            st.sidebar.warning(alert["msg"])
else:
    st.sidebar.success("✅ System Healthy")

st.sidebar.markdown("---")
st.sidebar.info("Select a page above to monitor system metrics.")

# Main page content
st.title("System Overview")
st.markdown("Welcome to the Quant V9 Operating Terminal.")
st.markdown("Use the sidebar to navigate to specific monitoring modules.")

col1, col2, col3 = st.columns(3)
col1.metric("Monitored Assets", len(dashboard_config.get("dashboard", {}).get("monitored_assets", [])))
col2.metric("Active Projects Data", len(data.get("state", {})))
col3.metric("Critical Alerts", len([a for a in alerts if a["level"] == "CRITICAL"]))
