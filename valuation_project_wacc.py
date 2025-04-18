import yfinance as yf
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# ——— Page config (must be first) ———
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")

st.title("Last Published Annual Financial Statements with NOPAT, FCF, Invested Capital Breakdown + Inv/Sales Overlay")

st.markdown("""
This dashboard pulls:
1. Annual financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital,
   Working‑Capital metrics (DIO, DSO, DPO, CCC).
2. Industry Inventory/Sales ratio (Building Materials & Garden Equipment Dealers) from FRED.
3. Home Depot’s Inventory/Sales ratio from its quarterly statements.
All visuals and tables are arranged in collapsible sections for clarity.
""")

# ——— Constants & Helpers ———
API_KEY     = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL    = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio: Building Materials & Garden Equipment Dealers"}

def format_millions(x):
    return round(x / 1_000_000, 2) if x else 0

def to_millions(x):
    return round(x / 1e6, 2) if pd.notnull(x) else 0

# Fetch functions
def fetch_stock_data(ticker):
    return yf.Ticker(ticker)

@st.cache_data
def get_fred_data(series_id, start_date, end_date):
    params = {
        "series_id": series_id,
        "api_key":   API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end":   end_date,
    }
    resp = requests.get(FRED_URL, params=params)
    if resp.status_code != 200:
        st.error(f"Error fetching FRED: {resp.status_code}")
        return None
    data = resp.json().get("observations", [])
    df = pd.DataFrame(data)
    df["date"]  = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df if not df.empty else None

# GAAP structured view helper
def display_gaap_income_statement(fin, col):
    gaap_order = [
        "Total Revenue","Operating Revenue","Cost Of Revenue","Gross Profit",
        "Operating Expense","Selling General and Administrative","Research & Development",
        "Operating Income","EBIT","EBITDA"
    ]
    with st.expander("GAAP Income Statement", expanded=False):
        for item in gaap_order:
            if item in fin.index:
                val = format_millions(fin.at[item, col])
                st.write(f"**{item}**: {val}M")

# Main financial section
ticker = st.text_input("Enter Ticker:", "AAPL")
if ticker:
    stock = fetch_stock_data(ticker)
    fin   = stock.financials
    bs    = stock.balance_sheet
    cf    = stock.cashflow
    info  = stock.info

    if not fin.empty:
        latest = fin.columns[0]

        # Compute core metrics and display sections...
        # Summary Table, GAAP view, Balance Sheet, Cash Flow, Key Financials, Growth,
        # Working Capital metrics and CCC all unchanged.
        pass

# ——— FRED + Home Depot Quarterly Overlay ———
st.markdown("---")
st.subheader("Inventory/Sales Ratio: Industry vs. Home Depot (Quarterly)")
col1, col2 = st.columns(2)
with col1:
    sd = st.date_input("FRED Start Date", pd.to_datetime("2000-01-01"))
with col2:
    ed = st.date_input("FRED End Date", pd.to_datetime("2025-12-31"))

if st.button("Fetch & Plot Quarterly Inv/Sales Overlay"):
    # Fetch FRED series
    sid, desc = next(iter(FRED_SERIES.items()))
    df_f = get_fred_data(sid, sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
    if df_f is None:
        st.warning("No FRED data.")
    else:
        # Display FRED raw data
        st.subheader("FRED Industry Inv/Sales Raw Data")
        st.dataframe(df_f.set_index("date"))

        # Fetch Home Depot quarterly data
        hd = fetch_stock_data("HD")
        fin_q = hd.quarterly_financials
        bs_q  = hd.quarterly_balance_sheet

        # Use quarters common to both and sort
        periods_q = sorted([c for c in fin_q.columns if c in bs_q.columns])
        dates_q   = [pd.to_datetime(c) for c in periods_q]

        invs_q, revs_q = [], []
        for c in periods_q:
            try:
                invs_q.append(bs_q.at["Inventory", c])
            except:
                invs_q.append(0)
            try:
                revs_q.append(fin_q.at["Total Revenue", c])
            except:
                revs_q.append(0)

        # Display Home Depot raw quarterly values
        hd_df = pd.DataFrame({"date": dates_q, "Inventory": invs_q, "Revenue": revs_q})
        hd_df.set_index("date", inplace=True)
        st.subheader("Home Depot Quarterly Raw Inventory & Revenue")
        st.dataframe(hd_df)

        # Calculate quarterly Inventory/Sales ratio (%)
        hd_ratio_q = [(inv/rev*100) if rev else None for inv, rev in zip(invs_q, revs_q)]

        # Display Home Depot ratio series
        ratio_df = pd.DataFrame({"date": dates_q, "HD Inv/Sales (%)": hd_ratio_q})
        ratio_df.set_index("date", inplace=True)
        st.subheader("Home Depot Quarterly Inv/Sales Ratio (%)")
        st.dataframe(ratio_df)

        # Plot overlay
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_f["date"], df_f["value"], label="Industry Inv/Sales (Monthly FRED)")
        ax.plot(ratio_df.index, ratio_df["HD Inv/Sales (%)"], marker='o', linestyle='-', label="Home Depot Inv/Sales (Quarterly)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Inv/Sales Ratio (%)")
        ax.set_title("Industry vs. Home Depot Inventory/Sales Ratio (Quarterly)")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

st.markdown("Data sourced from Yahoo Finance & FRED.")
