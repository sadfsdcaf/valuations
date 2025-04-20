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
        ppe = abs(safe_latest(cf, 'Net PPE'))
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
        
        di = td / (td + te) if (td + te) else 0
        ei = te / (td + te) if (td + te) else 0
        de = td / te if te else 0

        beta = info.get('beta', 1)
        market_risk_premium = 0.0443
        credit_spread = 0.026
        debt_beta = credit_spread / market_risk_premium        
        levered_denom = td * (1 - tax_rate) + te
        beta_a = ((td * (1 - tax_rate)) / levered_denom) * debt_beta + (te / levered_denom) * beta if levered_denom else 0

        # Re-lever Equity Beta (β_E)
        # Formula: β_E = β_A + (β_A - β_D) × (D/E) × (1 - T)

        beta_e_relevered = beta_a + (beta_a - debt_beta) * de_ratio * (1 - tax_rate)

        # Cost of Capital - Relevered
        r_e = ry + beta_e_relevered * market_risk_premium
        r_d = ry + credit_spread * beta_d
        
      
        er_eq = ry + beta * market_risk_premium
        er_de = ry + credit_spread * debt_beta


        wacc = (ei * er_eq) + (di * er_de * (1 - tax_rate))

        # Display Summary
        st.subheader("Key Financial Metrics")
        st.table(pd.DataFrame({
            'Metric': [
                'Asset Beta (β_A)',
                'Observed Equity Beta (β_E_obs)',
                'Re-levered Equity Beta (β_E)',
                'Debt/Equity',
                'WACC'
            ],
            'Value': [
                f"{beta_a:.4f}",
                f"{beta_e_obs:.4f}",
                f"{beta_e_relevered:.4f}",
                f"{de_ratio:.2f}",
                f"{wacc:.2%}"
            ]
        }))

        # ROIC, Growth, Valuation
        roic = nopat / tic if tic else 0
        change_in_invested_capital = ppe + wcchg
        rr = (change_in_invested_capital / nopat) if (nopat and change_in_invested_capital > 0) else 0
        gr = rr * roic if roic else 0

        val_g = nopat / (wacc - gr) if wacc > gr else 0
        val_ng = nopat / wacc if wacc else 0

        # --- Display Tables ---
        st.subheader("--- ROIC and Growth Analysis ---")
        st.table(pd.DataFrame({
            "Metric": ["ROIC", "Change in Invested Capital", "Retention Ratio", "Growth Rate"],
            "Value": [f"{roic*100:.2f}%", f"${change_in_invested_capital/1e6:.2f}M", f"{rr*100:.2f}%", f"{gr*100:.2f}%"]
        }))

        st.subheader("--- Cost of Equity and Cost of Debt Calculation ---")
        st.table(pd.DataFrame({
            "Metric": ["Cost of Equity (rₑ)", "Cost of Debt (r_d)"],
            "Value": [f"{er_eq:.4f}", f"{er_de:.4f}"]
        }))

        st.subheader("--- Capital Structure Calculations ---")
        st.table(pd.DataFrame({
            "Metric": ["Debt/Invested Capital", "Equity/Invested Capital", "Debt/Equity"],
            "Value": [f"{td/tic:.4f}" if tic else "N/A", f"{te/tic:.4f}" if tic else "N/A", f"{td/te:.4f}" if te else "N/A"]
        }))

        st.subheader("--- WACC Detailed Breakdown ---")
        st.table(pd.DataFrame({
            "Metric": ["Risk-Free Rate", "Beta", "Market Risk Premium", "Cost of Equity", "Market Cap ($M)", "Debt ($Bn)",
                       "Cost of Debt", "Tax Rate", "Effective Tax Rate", "WACC"],
            "Value": [f"{ry:.4f}", f"{beta:.2f}", f"{market_risk_premium:.4f}", f"{er_eq:.4f}",
                      f"{info.get('marketCap',0)/1e6:.2f}", f"{td/1e9:.2f}",
                      f"{er_de:.4f}", f"{tax_rate:.2f}", f"{taxprov/pretax if pretax else 0:.4f}", f"{wacc:.4f}"]
        }))

        st.subheader("--- Valuation Using Perpetuity Methods ---")
        st.table(pd.DataFrame({
            "Metric": ["NOPAT", "WACC", "Growth Rate", "Valuation (With Growth)", "Valuation (No Growth)"],
            "Value": [f"${nopat/1e6:.2f}M", f"{wacc:.4f}", f"{gr:.4f}",
                      f"${val_g/1e6:.2f}M" if wacc > gr else "N/A", f"${val_ng/1e6:.2f}M"]
        }))

        # --- Forecast Section ---
        st.subheader("📈 Forecasting NOPAT with Compounding Growth")
        g_forecast = st.number_input("Enter Growth Rate (g) (%)", value=5.0) / 100
        b_forecast = st.number_input("Enter Reinvestment Rate (b)", value=0.2)
        years_forecast = st.selectbox("Years to Forecast", options=[5, 7, 10, 20], index=1)

        years = list(range(0, years_forecast + 1))
        forecast_years = [datetime.now().year + n for n in years]
        shares_outstanding = info.get('sharesOutstanding', 0) / 1e6

        nopat_series, reinvestment_series, wacc_series, growth_series, value_series, price_per_share_series = [], [], [], [], [], []

        current_nopat = nopat
        for n in years:
            if n != 0:
                current_nopat *= (1 + g_forecast)
            nopat_series.append(current_nopat / 1e6)
            reinvestment_series.append(b_forecast)
            wacc_series.append(wacc)
            growth_series.append(g_forecast)
            if (wacc - g_forecast) > 0:
                forecast_value = (current_nopat * (1 - b_forecast)) / (wacc - g_forecast)
            else:
                forecast_value = 0
            value_series.append(forecast_value / 1e6)
            price_per_share_series.append((forecast_value / shares_outstanding) if shares_outstanding > 0 else 0)

        forecast_diag = pd.DataFrame({
            'NOPAT (M)': nopat_series,
            'Reinvestment Rate (b)': reinvestment_series,
            'WACC': wacc_series,
            'Growth Rate (g)': growth_series,
            'Forecasted Value (M)': value_series,
            'Shares Outstanding (M)': [shares_outstanding] * len(years),
            'Forecasted Price per Share ($)': price_per_share_series
        }, index=forecast_years).T

        st.subheader("📊 Forecast Diagnostics")
        st.dataframe(forecast_diag.style.format("{:.2f}"))

        # --- Financials ---
        st.subheader("Financial Statements (M)")
        st.dataframe(fin.applymap(format_millions))
        st.dataframe(bs.applymap(format_millions))
        st.dataframe(cf.applymap(format_millions))

        mets = ["Total Revenue", "Gross Profit", "EBIT", "EBITDA"]
        kdf = fin.reindex(mets).iloc[:, :5].applymap(format_millions)
        yrs = [pd.to_datetime(c).year for c in fin.columns[:5]]
        kdf.columns = yrs[::-1]
        st.table(kdf)

        gdf = (kdf.pct_change(axis=1).iloc[:,1:] * 100).round().astype(int)
        gdf.columns = [f"{b} vs {a}" for a, b in zip(yrs[:-1], yrs[1:])]
        st.subheader("YoY Growth")
        st.table(gdf)

        wc_list = []
        for c in fin.columns[:5]:
            inv = safe_col(bs, 'Inventory', c)
            ar = safe_col(bs, 'Accounts Receivable', c)
            ap = safe_col(bs, 'Accounts Payable', c)
            cogs = safe_col(fin, 'Cost Of Revenue', c)
            rev = safe_col(fin, 'Total Revenue', c)
            dio = int(round(inv / cogs * 365)) if cogs else None
            dso = int(round(ar / rev * 365)) if rev else None
            dpo = int(round(ap / cogs * 365)) if cogs else None
            ccc = (dio or 0) + (dpo or 0) - (dso or 0)
            wc_list.append({'Year': pd.to_datetime(c).year, 'DIO': dio, 'DSO': dso, 'DPO': dpo, 'CCC': ccc, 'NWC': (inv+ar-ap)/1e6})
        wc_df = pd.DataFrame(wc_list).set_index('Year')
        wc_df['ΔNWC'] = wc_df['NWC'].diff().round(2)
        st.subheader("Working Capital Metrics")
        st.table(wc_df)
