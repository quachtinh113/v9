import streamlit as st
import sys, os
from pathlib import Path

ROOT_DIR = Path(os.path.dirname(__file__)).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
from src.dashboard.data_loader import load_yaml, get_all_projects_data
from src.dashboard.alerts import check_alerts

st.set_page_config(page_title="Executive Overview", layout="wide")
st.title("Executive Overview")

dashboard_config = load_yaml(ROOT_DIR / "configs" / "dashboard_config.yaml")
risk_config = load_yaml(ROOT_DIR / "configs" / "risk_config.yaml")
data = get_all_projects_data(dashboard_config)
alerts = check_alerts(data, risk_config, dashboard_config)

st.header("System Health")
if alerts:
    st.error(f"{len(alerts)} Active Alerts detected!")
    for a in alerts:
        st.write(f"- **{a['level']}**: {a['msg']}")
else:
    st.success("All systems operating within Risk Parameters.")

st.header("Global Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Positions", sum(1 for p in data.get("positions", {}).values() if p.get("active")))
col2.metric("Total Basket Risk", "Calculated %")
col3.metric("Running PnL", "$0.00")
