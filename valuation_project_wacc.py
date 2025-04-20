import yfinance as yf
import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# Page config
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")

st.title("Annual Financials with NOPAT, FCF, Inv/Sales + Live & Historical Price")

st.markdown("""
This dashboard:
1. Pulls financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital, and Working Capital metrics.
2. Fetches Inventory/Sales ratio for Building Materials & Garden Equipment Dealers from FRED.
3. Displays the live stock price and historical price chart.
""")

# Helper functions
def fetch_ticker(ticker):
    return yf.Ticker(ticker)

def format_millions(x):
    return int(round(x/1e6)) if pd.notnull(x) else 0

def get_10yr_treasury_yield():
    tnx = yf.Ticker("^TNX")
    hist = tnx.history(period="5d")
    return hist['Close'].dropna().iloc[-1] / 100 if not hist.empty else 0.04

def safe_latest(df, field):
    return df.iloc[df.index.get_loc(field)].dropna().values[0] if not df.empty and field in df.index else 0

def safe_col(df, field, col):
    return df.at[field, col] if not df.empty and field in df.index and col in df.columns else 0

# FRED setup
API_KEY = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio"}

@st.cache_data
def get_fred_data(series_id, start, end):
    r = requests.get(FRED_URL, params={
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end
    })
    if r.status_code != 200:
        st.error(f"Error fetching FRED: {r.status_code}")
        return None
    df = pd.DataFrame(r.json().get("observations", []))
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df

# --- Main Section ---
ticker = st.text_input("Enter Ticker:", "DOCN")
if ticker:
    tk = fetch_ticker(ticker)
    info = tk.info

    # Live Price
    live = info.get('currentPrice') or info.get('regularMarketPrice')
    if live:
        st.metric("Live Price", f"${live:.2f}")

    # Historical Close
    st.subheader("Historical Close Price")
    hist = tk.history(period="max")
    if not hist.empty:
        st.line_chart(hist['Close'])
    else:
        st.warning("No historical price.")

    # Financials
    fin = tk.financials
    bs = tk.balance_sheet
    cf = tk.cashflow

    if not fin.empty:
        ry = get_10yr_treasury_yield()

        # Core Metrics
        pretax = safe_latest(fin, 'Pretax Income')
        taxprov = safe_latest(fin, 'Tax Provision')
        ebit = safe_latest(fin, 'EBIT')
        ebitda = safe_latest(fin, 'EBITDA')
        damo = safe_latest(cf, 'Depreciation Amortization Depletion')
        capex = safe_latest(cf, 'Capital Expenditure')
        ppe = safe_latest(cf, 'Net PPE Purchase And Sale') * -1  # Net PPE outflow
        wcchg = safe_latest(cf, 'Change In Working Capital')

        # NOPAT & FCF
        tax_rate = safe_latest(fin, 'Tax Rate For Calcs')
        nopat = ebit * (1 - tax_rate)
        fcf = nopat + damo - capex - wcchg

        # Capital Structure
        ltd = safe_latest(bs, 'Long Term Debt')
        std = safe_latest(bs, 'Short Term Debt')
        td = ltd + std
        te = safe_latest(bs, 'Total Equity Gross Minority Interest')
        tic = safe_latest(bs, 'Invested Capital')

        # Market parameters
        beta_e = info.get('beta', 1)
        market_risk_premium = 0.0443
        credit_spread = 0.026
        debt_beta = credit_spread / market_risk_premium

        # Calculate Unlevered Asset Beta (β_A)
        # Formula: β_A = (D*(1-T)/(D*(1-T) + E)) * β_D + (E/(D*(1-T) + E)) * β_E
        levered_denom = td * (1 - tax_rate) + te
        beta_a = ((td * (1 - tax_rate)) / levered_denom) * debt_beta + (te / levered_denom) * beta_e if levered_denom else 0

        # Cost of Equity & Debt
        er_eq = ry + beta_e * market_risk_premium
        er_de = ry + credit_spread * debt_beta

        # Weightings
        di = td / (td + te) if (td + te) else 0
        ei = te / (td + te) if (td + te) else 0

        # WACC
        wacc = (ei * er_eq) + (di * er_de * (1 - tax_rate))

        # ... rest of your code continues unchanged ...

        # Display the Unlevered Asset Beta
        st.subheader("Unlevered Asset Beta Calculation")
        st.write(f"**Asset Beta (β_A):** {beta_a:.4f}")
