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

        df_sum = pd.DataFrame({
            'Metric': [
                'EBITDA', 'EBIT', 'NOPAT (M)', 'Capital Expenditure',
                'Total Debt (M)', 'Total Equity (M)', 'Invested Capital (M)',
                'WACC', 'Beta', 'ROIC', 'Growth Rate',
                'Valuation (Growth)', 'Valuation (No Growth)', 'Market Cap (M)'
            ],
            'Value': [
                ebitda/1e6, ebit/1e6, nopat/1e6, capex/1e6,
                td/1e6, te/1e6, tic/1e6,
                wacc*100, beta, roic*100, gr*100,
                val_g/1e6, val_ng/1e6, info.get('marketCap', 0)/1e6
            ]
        })

        st.subheader("--- Financial Summary ---")
        st.dataframe(df_sum)

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
        st.subheader("--- ROIC and Growth Analysis ---")
        st.table(pd.DataFrame(roic_growth_data))


        st.subheader("--- Cost of Equity and Cost of Debt Calculation ---")
        st.text(f"Cost of Equity (rₑ) = Risk-Free Rate + Beta × Market Risk Premium")
        st.text(f"                  = {ry:.4f} + {beta:.2f} × {market_risk_premium:.4f}")
        st.text(f"                  = {er_eq:.4f}")
        
        st.text("")
        st.text(f"Cost of Debt (r_d) = Risk-Free Rate + Credit Spread")
        st.text(f"                 = {ry:.4f} + {credit_spread:.4f}")
        st.text(f"                 = {er_de:.4f}")
        
        st.subheader("--- Capital Structure Calculations ---")
        st.text(f"Debt to Invested Capital (D/IC) = Total Debt / Invested Capital")
        st.text(f"                               = {td:.2f} / {tic:.2f}")
        st.text(f"                               = {td / tic:.4f}" if tic else "                               = N/A")
        
        st.text("")
        st.text(f"Equity to Invested Capital (E/IC) = Total Equity / Invested Capital")
        st.text(f"                                 = {te:.2f} / {tic:.2f}")
        st.text(f"                                 = {te / tic:.4f}" if tic else "                                 = N/A")
        
        st.text("")
        st.text(f"Debt to Equity (D/E) = Total Debt / Total Equity")
        st.text(f"                    = {td:.2f} / {te:.2f}")
        st.text(f"                    = {td / te:.4f}" if te else "                    = N/A")

        st.subheader("--- WACC Detailed Breakdown ---")
        st.text(f"Risk-Free Rate: {ry:.4f}")
        st.text(f"Beta: {beta:.2f}")
        st.text(f"Market Risk Premium: {market_risk_premium:.4f}")
        st.text(f"Cost of Equity: {er_eq:.4f}")
        
        market_value_equity = info.get('marketCap', 0) / 1e6  # Market Cap in millions
        market_value_debt = td / 1e9  # Debt in billions
        
        income_tax_expense = safe_latest(fin, 'Income Tax Expense') / 1e6
        ebt = pretax / 1e6
        effective_tax_rate = income_tax_expense / ebt if ebt else 0
        
        st.text(f"Market Value of Equity ($M): {market_value_equity:.2f}")
        st.text(f"Market Value of Debt ($Bn): {market_value_debt:.2f}")
        st.text(f"Cost of Debt: {er_de:.4f}")
        st.text(f"Income Tax Expense ($M): {income_tax_expense:.2f}")
        st.text(f"Earnings Before Tax (EBT) ($M): {ebt:.2f}")
        st.text(f"Effective Tax Rate: {effective_tax_rate:.4f}")
        st.text(f"Weight of Debt (Wd): {di:.4f}")
        st.text(f"Weight of Equity (We): {ei:.4f}")
        st.text(f"WACC: {wacc:.4f}")
        
        st.subheader("--- Valuation Using Perpetuity Methods ---")
        st.text(f"NOPAT: {nopat/1e6:.2f}M")
        st.text(f"WACC: {wacc:.4f}")
        st.text(f"Growth Rate: {gr:.4f}")
        
        if wacc > gr:
            st.text(f"Valuation with Growth = NOPAT / (WACC - Growth Rate)")
            st.text(f"                     = {nopat/1e6:.2f}M / ({wacc:.4f} - {gr:.4f})")
            st.text(f"                     = {val_g/1e6:.2f}M")
        else:
            st.warning("WACC is less than or equal to Growth Rate — cannot calculate Valuation with Growth.")
        
        st.text("")
        
        st.text(f"Valuation with No Growth = NOPAT / WACC")
        st.text(f"                      = {nopat/1e6:.2f}M / {wacc:.4f}")
        st.text(f"                      = {val_ng/1e6:.2f}M")
# --- Overlay ---
st.markdown("---")
st.subheader("Inventory/Sales Overlay")
col1, col2 = st.columns(2)
with col1:
    sd = st.date_input("FRED Start", pd.to_datetime("2000-01-01"))
with col2:
    ed = st.date_input("FRED End", pd.to_datetime("2025-12-31"))
if st.button("Plot Inv/Sales Overlay"):
    sid, _ = next(iter(FRED_SERIES.items()))
    df_f = get_fred_data(sid, sd.strftime('%Y-%m-%d'), ed.strftime('%Y-%m-%d'))
    if df_f is None:
        st.warning('No FRED data.')
    else:
        tk_hd = fetch_ticker('HD')
        f_hd, b_hd = tk_hd.financials, tk_hd.balance_sheet
        per = [c for c in f_hd.columns if c in b_hd.columns]
        dates = [pd.to_datetime(c) for c in per]
        invs = [safe_col(b_hd, 'Inventory', c) for c in per]
        revs = [safe_col(f_hd, 'Total Revenue', c) for c in per]
        ratios = [round(i/r*100/12,2) if r else None for i,r in zip(invs,revs)]
        hd_df = pd.DataFrame({'InvSales%': ratios}, index=dates)

        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(df_f['date'], df_f['value'], label='Industry')
        ax.plot(hd_df.index, hd_df['InvSales%'], marker='o', label='Home Depot')
        ax.set_xlabel('Date')
        ax.set_ylabel('Inv/Sales %')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

st.markdown("Data from Yahoo Finance & FRED.")
