import streamlit as st
import sys, os
from pathlib import Path

ROOT_DIR = Path(os.path.dirname(__file__)).resolve().parents[1]
sys.path.append(str(ROOT_DIR))
from src.dashboard.data_loader import load_yaml, get_all_projects_data

st.set_page_config(page_title="Risk Monitor", layout="wide")
st.title("Risk Monitor")

dashboard_config = load_yaml(ROOT_DIR / "configs" / "dashboard_config.yaml")
risk_config = load_yaml(ROOT_DIR / "configs" / "risk_config.yaml")
data = get_all_projects_data(dashboard_config)

st.subheader("Global Risk Limits")
st.json(risk_config.get("risk_engine", {}))

st.subheader("Asset Risk States")
st.write(data.get("state", {}))
