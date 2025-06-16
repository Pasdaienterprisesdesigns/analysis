import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# === CONFIG ===
SIM_API_KEY = "sim_444cGnNxG0exoklzAjwNsmIGcv03PBDG"  
HEADERS = {"X-Sim-Api-Key": SIM_API_KEY}

# === API CALLS ===
def get_token_info(token_address):
    url = f"https://api.sim.dune.com/v1/evm/token/{token_address}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        st.error("Token not found or API error.")
        return None
    data = res.json()["token"]
    return {
        "name": data["name"],
        "symbol": data["symbol"],
        "creator_address": data["creator_address"],
        "created_at": data["created_at"]
    }

def get_token_holders(token_address, limit=100):
    url = f"https://api.sim.dune.com/v1/evm/token_holders/{token_address}?limit={limit}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        st.error("Could not fetch token holders.")
        return []
    return res.json().get("holders", [])

# === RISK SCORING ===
def calculate_risk_score(holders, token_info):
    flags = []
    score = 100

    total_holders = len(holders)
    if total_holders < 20:
        score -= 20
        flags.append("Less than 20 holders")

    top_1_pct = holders[0]['percent_of_total'] if holders else 0
    if top_1_pct > 70:
        score -= 30
        flags.append("Top wallet holds more than 70%")

    top_10_pct = sum([h['percent_of_total'] for h in holders[:10]]) if holders else 0
    if top_10_pct > 90:
        score -= 20
        flags.append("Top 10 wallets hold more than 90%")

    if token_info and "created_at" in token_info:
        try:
            creation_date = pd.to_datetime(token_info["created_at"])
            age_days = (pd.Timestamp.now(tz="UTC") - creation_date).days
            if age_days < 10:
                score -= 10
                flags.append("Token is less than 10 days old")
        except Exception as e:
            st.warning(f"Could not process token creation date: {e}")

    return max(score, 0), flags

# === MAIN UI ===
st.set_page_config(page_title="Token Risk Screener", layout="wide")
st.title("🧠 Token Risk Engine — New Listings Screener")

token_address = st.text_input("Paste ERC-20 Token Address (e.g. 0x...)", "")

if token_address:
    with st.spinner("Fetching token data..."):
        token_info = get_token_info(token_address)
        holders = get_token_holders(token_address)

    if token_info and holders:
        st.subheader(f"{token_info['name']} ({token_info['symbol']})")
        st.markdown(f"**Creator Address:** `{token_info['creator_address']}`")
        st.markdown(f"**Created On:** {token_info['created_at']}")

        score, flags = calculate_risk_score(holders, token_info)

        st.subheader("🧪 Risk Analysis")
        st.metric(label="Risk Score (0-100)", value=score)
        for flag in flags:
            st.warning(f"🚩 {flag}")

        st.subheader("📊 Top Holders Distribution")
        df = pd.DataFrame(holders[:10])
        df['percent_of_total'] = df['percent_of_total'].round(2)
        df_display = df[['address', 'amount', 'percent_of_total']]
        st.dataframe(df_display)

        fig = px.pie(df, names='address', values='percent_of_total',
                     title='Top 10 Holders Share')
        st.plotly_chart(fig, use_container_width=True)

