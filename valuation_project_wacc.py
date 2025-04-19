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
1. Pulls annual financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital, and Working‑Capital metrics (DIO, DSO, DPO, CCC).
2. Fetches the Industry Inventory/Sales ratio (Building Materials & Garden Equipment Dealers) from FRED.
3. Calculates and plots Home Depot’s Inventory/Sales ratio based on the same periods provided by yFinance.
4. Displays the live stock price and historical price chart for the selected ticker.
""")

# Helper functions
def fetch_ticker(ticker):
    return yf.Ticker(ticker)

def format_millions(x):
    return int(round(x/1e6)) if pd.notnull(x) else 0

def get_10yr_treasury_yield():
    tnx = yf.Ticker("^TNX")
    hist = tnx.history(period="5d")
    if not hist.empty:
        return hist['Close'].dropna().iloc[-1] / 100
    return 0.04

def safe_latest(df, field):
    if not df.empty and field in df.index:
        return df.iloc[df.index.get_loc(field)].dropna().values[0]
    return 0

def safe_col(df, field, col):
    if not df.empty and field in df.index and col in df.columns:
        return df.at[field, col]
    return 0

# FRED API setup
API_KEY = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio: Building Materials & Garden Equipment Dealers"}

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
    if df.empty:
        return None
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

    # Historical Close Price
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
        latest = fin.columns[0]

        ry = get_10yr_treasury_yield()
        st.write(f"10-Year Treasury Yield (Risk-Free Rate): {ry:.4f}")

        # Core Metrics
        total_revenue = safe_latest(fin, 'Total Revenue')
        pretax = safe_latest(fin, 'Pretax Income')
        taxprov = safe_latest(fin, 'Tax Provision')
        net_ppe = safe_latest(fin, 'Net PPE')
        gross_ppe = safe_latest(fin, 'Gross PPE')
        capex = safe_latest(cf, 'Capital Expenditure')
        taxrate = (taxprov / pretax) if pretax else 0
        ebit = safe_latest(fin, 'EBIT')
        ebitda = safe_latest(fin, 'EBITDA')
        damo = safe_latest(cf, 'Depreciation Amortization Depletion')
        ppe = abs(safe_latest(cf, 'Net PPE'))
        wcchg = safe_latest(cf, 'Change In Working Capital')

        # NOPAT & FCF
        nopat = ebit * (1 - taxrate)
        fcf = nopat + damo - capex - wcchg

        # Capital Structure
        ltd = safe_latest(bs, 'Long Term Debt')
        std = safe_latest(bs, 'Short Term Debt')
        td = ltd + std
        te = safe_latest(bs, 'Total Equity Gross Minority Interest')
        tic = safe_latest(bs, 'Invested Capital')

        beta = info.get('beta', 1)
        market_risk_premium = 0.05
        credit_spread = 0.01

        er_eq = ry + beta * market_risk_premium
        er_de = ry + credit_spread

        di = td / (td + te) if (td + te) else 0
        ei = te / (td + te) if (td + te) else 0

        wacc = (ei * er_eq) + (di * er_de * (1 - taxrate))

        # ROIC, Growth, Valuation
        roic = nopat / tic if tic else 0
        change_in_invested_capital = ppe + wcchg
        rr = (change_in_invested_capital / nopat) if (nopat and change_in_invested_capital > 0) else 0
        gr = rr * roic if roic else 0

        val_g = nopat / (wacc - gr) if wacc > gr else 0
        val_ng = nopat / wacc if wacc else 0

        # --- Now show all in tables ---
        st.subheader("--- ROIC and Growth Analysis ---")
        roic_growth_data = {
            "Metric": [
                "Return on Invested Capital (ROIC)",
                "Change in Invested Capital (Net PPE + NWC)",
                "Retention Ratio (RR)",
                "Growth Rate (g)"
            ],
            "Value": [
                f"{roic*100:.2f}%",
                f"${change_in_invested_capital/1e6:.2f}M",
                f"{rr*100:.2f}%",
                f"{gr*100:.2f}%"
            ]
        }
        st.table(pd.DataFrame(roic_growth_data))

        st.subheader("--- Cost of Equity and Cost of Debt Calculation ---")
        cost_of_capital_data = {
            "Metric": [
                "Cost of Equity (rₑ)",
                "Cost of Debt (r_d)"
            ],
            "Value": [
                f"{er_eq:.4f}",
                f"{er_de:.4f}"
            ]
        }
        st.table(pd.DataFrame(cost_of_capital_data))

        st.subheader("--- Capital Structure Calculations ---")
        capital_structure_data = {
            "Metric": [
                "Debt to Invested Capital (D/IC)",
                "Equity to Invested Capital (E/IC)",
                "Debt to Equity (D/E)"
            ],
            "Value": [
                f"{td/tic:.4f}" if tic else "N/A",
                f"{te/tic:.4f}" if tic else "N/A",
                f"{td/te:.4f}" if te else "N/A"
            ]
        }
        st.table(pd.DataFrame(capital_structure_data))

        st.subheader("--- WACC Detailed Breakdown ---")
        market_value_equity = info.get('marketCap', 0) / 1e6
        market_value_debt = td / 1e9
        income_tax_expense = safe_latest(fin, 'Income Tax Expense') / 1e6
        ebt = pretax / 1e6
        effective_tax_rate = income_tax_expense / ebt if ebt else 0

        wacc_data = {
            "Metric": [
                "Risk-Free Rate",
                "Beta",
                "Market Risk Premium",
                "Cost of Equity",
                "Market Value of Equity ($M)",
                "Market Value of Debt ($Bn)",
                "Cost of Debt",
                "Income Tax Expense ($M)",
                "Earnings Before Tax (EBT) ($M)",
                "Effective Tax Rate",
                "Weight of Debt (Wd)",
                "Weight of Equity (We)",
                "WACC"
            ],
            "Value": [
                f"{ry:.4f}",
                f"{beta:.2f}",
                f"{market_risk_premium:.4f}",
                f"{er_eq:.4f}",
                f"{market_value_equity:.2f}",
                f"{market_value_debt:.2f}",
                f"{er_de:.4f}",
                f"{income_tax_expense:.2f}",
                f"{ebt:.2f}",
                f"{effective_tax_rate:.4f}",
                f"{di:.4f}",
                f"{ei:.4f}",
                f"{wacc:.4f}"
            ]
        }
        st.table(pd.DataFrame(wacc_data))

        st.subheader("--- Valuation Using Perpetuity Methods ---")
        valuation_data = {
            "Metric": [
                "NOPAT",
                "WACC",
                "Growth Rate",
                "Valuation with Growth",
                "Valuation with No Growth"
            ],
            "Value": [
                f"${nopat/1e6:.2f}M",
                f"{wacc:.4f}",
                f"{gr:.4f}",
                f"${val_g/1e6:.2f}M" if wacc > gr else "N/A",
                f"${val_ng/1e6:.2f}M"
            ]
        }
        st.table(pd.DataFrame(valuation_data))
        
        st.markdown("---")
st.subheader("📈 Forecasting NOPAT with Compounding Growth (Including Period 0)")

# Inputs
g_forecast = st.number_input("Enter Growth Rate (g) for Forecasting (%)", value=5.0) / 100
b_forecast = st.number_input("Enter Reinvestment Rate (b)", value=0.2)
years_forecast = st.selectbox("Select Number of Years to Forecast:", options=[5, 7, 10, 20], index=1)

# Forecasting setup
years = list(range(0, years_forecast + 1))  # <-- Start at Period 0
forecast_years = [datetime.now().year + n for n in years]

# Get Shares Outstanding
shares_outstanding = info.get('sharesOutstanding', 0) / 1e6  # in millions

# Initialize trackers
nopat_series = []
reinvestment_series = []
wacc_series = []
growth_series = []
value_series = []
price_per_share_series = []

current_nopat = nopat  # Start with latest real NOPAT

for n in years:
    if n != 0:
        current_nopat = current_nopat * (1 + g_forecast)  # grow each future year

    nopat_series.append(current_nopat / 1e6)  # NOPAT in millions
    reinvestment_series.append(b_forecast)
    wacc_series.append(wacc)
    growth_series.append(g_forecast)

    if (wacc - g_forecast) > 0:
        forecast_value = (current_nopat * (1 - b_forecast)) / (wacc - g_forecast)
    else:
        forecast_value = 0
    value_series.append(forecast_value / 1e6)  # Value in millions

    # Calculate price per share
    if shares_outstanding > 0:
        price_per_share =  (forecast_value/1e6) / shares_outstanding 
    else:
        price_per_share = 0
    price_per_share_series.append(price_per_share)

# Build the Diagnostics DataFrame
forecast_diag = pd.DataFrame({
    'NOPAT (M)': nopat_series,
    'Reinvestment Rate (b)': reinvestment_series,
    'WACC': wacc_series,
    'Growth Rate (g)': growth_series,
    'Forecasted Value (M)': value_series,
    'Shares Outstanding (M)': [shares_outstanding] * len(years),
    'Forecasted Price per Share ($)': price_per_share_series
}).T

forecast_diag.columns = forecast_years

# Show the full table
st.subheader(f"📊 Forecast Diagnostics (Including Period 0 and Shares)")
st.dataframe(forecast_diag.style.format("{:.2f}"))

# --- Financial Statements Section ---
if not fin.empty:
    ...
    st.table(pd.DataFrame(valuation_data))

    # --- Financial Statements Section ---

    st.subheader("Financial Statements (in Millions)")

    st.markdown("**Income Statement (M) — Last Published**")
    st.dataframe(fin.applymap(format_millions))

    st.markdown("**Balance Sheet (M)**")
    st.dataframe(bs.applymap(format_millions))

    st.markdown("**Cash Flow Statement (M)**")
    st.dataframe(cf.applymap(format_millions))

    # --- Key Financial Metrics (5 Years) ---

    st.subheader("Key Financials (M) — Last 5 Years")
    mets = ["Total Revenue", "Gross Profit", "EBIT", "EBITDA"]
    last5 = fin.columns[:5]
    kdf = fin.reindex(mets).loc[:, last5].applymap(format_millions)
    yrs = [pd.to_datetime(c).year for c in last5][::-1]
    kdf.columns = yrs
    st.table(kdf)

    # --- Year-over-Year Growth ---

    st.subheader("Year‑over‑Year Growth (%)")
    gdf = (kdf.pct_change(axis=1).iloc[:,1:] * 100).round().astype(int)
    gdf.columns = [f"{b} vs {a}" for a,b in zip(yrs[:-1], yrs[1:])]
    st.table(gdf)

    # --- Working Capital & CCC Metrics ---

    st.subheader("Working Capital Metrics (Days) + ΔNWC")
    wc_list = []
    for c in last5:
        inv  = safe_col(bs, 'Inventory', c)
        ar   = safe_col(bs, 'Accounts Receivable', c)
        ap   = safe_col(bs, 'Accounts Payable', c)
        cogs = safe_col(fin, 'Cost Of Revenue', c)
        rev  = safe_col(fin, 'Total Revenue', c)

        dio = int(round(inv / cogs * 365)) if cogs > 0 else None
        dso = int(round(ar / rev * 365)) if rev > 0 else None
        dpo = int(round(ap / cogs * 365)) if cogs > 0 else None
        ccc = int(round((dio or 0) + (dpo or 0) - (dso or 0)))

        nwc = inv + ar - ap
        wc_list.append({
            'Year': pd.to_datetime(c).year,
            'DIO': dio,
            'DSO': dso,
            'DPO': dpo,
            'CCC': ccc,
            'NWC': nwc/1e6  # in millions
        })

    wc_df = pd.DataFrame(wc_list).set_index('Year')
    wc_df['ΔNWC'] = wc_df['NWC'].diff().round(2)
    st.table(wc_df)
