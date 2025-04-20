import yfinance as yf
import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")
st.title("Annual Financials with NOPAT, FCF, Inv/Sales + Live & Historical Price")

st.markdown("""
This dashboard:
1. Pulls financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital, and Working Capital metrics.
2. Fetches Inventory/Sales ratio for Building Materials & Garden Equipment Dealers from FRED.
3. Displays the live stock price and historical price chart.
""")

# ─── Helper Functions ──────────────────────────────────────────────────────
def fetch_ticker(ticker: str) -> yf.Ticker:
    return yf.Ticker(ticker)

@st.cache_data
def get_10yr_treasury_yield() -> float:
    tnx = yf.Ticker("^TNX")
    hist = tnx.history(period="5d")
    if hist.empty:
        return 0.04
    return hist['Close'].dropna().iloc[-1] / 100

@st.cache_data
def get_fred_data(series_id: str, start: str, end: str) -> pd.DataFrame:
    API_KEY = "26c01b09f8083e30a1ee9cb929188a74"
    URL = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end
    }
    resp = requests.get(URL, params=params)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json().get("observations", []))
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.set_index("date")

@st.cache_data
def format_millions(df: pd.DataFrame) -> pd.DataFrame:
    return df.applymap(lambda x: round(x/1e6, 2) if pd.notnull(x) else 0)

def safe_value(df: pd.DataFrame, field: str, col=None) -> float:
    try:
        if col is None:
            return df.loc[field].dropna().values[0]
        return df.at[field, col]
    except Exception:
        return 0.0

# ─── Main ────────────────────────────────────────────────────────────────────
ticker = st.text_input("Enter Ticker:", "DOCN")
if ticker:
    tk = fetch_ticker(ticker)
    info = tk.info or {}

    # Live Price
    live_price = info.get('currentPrice') or info.get('regularMarketPrice')
    if live_price:
        st.metric("Live Price", f"${live_price:.2f}")

    # Historical Price Chart
    st.subheader("Historical Close Price")
    history = tk.history(period="max")
    if not history.empty:
        st.line_chart(history['Close'])
    else:
        st.warning("No historical price data available.")

    # Load statements
    fin = tk.financials
    bs = tk.balance_sheet
    cf = tk.cashflow

    if fin is not None and not fin.empty:
        # Treasury Rate
        rf_rate = get_10yr_treasury_yield()

        # Financial Metrics (latest year)
        pretax = safe_value(fin, 'Pretax Income')
        taxprov = safe_value(fin, 'Tax Provision')
        ebit = safe_value(fin, 'EBIT')
        damo = safe_value(cf, 'Depreciation Amortization Depletion')
        capex = safe_value(cf, 'Capital Expenditure')
        wcchg = safe_value(cf, 'Change In Working Capital')

        # NOPAT & FCF
        tax_rate = safe_value(fin, 'Tax Rate For Calcs')
        nopat = ebit * (1 - tax_rate)
        fcf = nopat + damo - capex - wcchg

        # Capital Structure
        ltd = safe_value(bs, 'Long Term Debt')
        std = safe_value(bs, 'Short Term Debt')
        td = ltd + std
        te = safe_value(bs, 'Total Equity Gross Minority Interest')
        tic = safe_value(bs, 'Invested Capital')

        # Betas and Cost of Capital
        beta_e = info.get('beta', 1.0)
        mkt_rp = 0.0443
        credit_spread = 0.026
        beta_d = credit_spread / mkt_rp

        # Unlevered Asset Beta
        levered_base = td * (1 - tax_rate) + te
        beta_a = ((td * (1 - tax_rate)) / levered_base) * beta_d + (te / levered_base) * beta_e if levered_base else 0

        # Costs
        r_e = rf_rate + beta_e * mkt_rp
        r_d = rf_rate + credit_spread * beta_d

        # Weights
        w_d = td / (td + te) if (td + te) else 0
        w_e = te / (td + te) if (td + te) else 0

        # WACC
        wacc = w_e * r_e + w_d * r_d * (1 - tax_rate)

        # ROIC & Growth
        roic = nopat / tic if tic else 0
        reinvest = safe_value(cf, 'Net PPE Purchase And Sale') * -1 + wcchg
        retention = reinvest / nopat if nopat else 0
        growth = roic * retention

        # Valuation
        val_with = nopat / (wacc - growth) if wacc > growth else np.nan
        val_no = nopat / wacc if wacc else np.nan

        # Display Key Metrics
        st.subheader("Key Financial Metrics")
        st.table(pd.DataFrame(
            {
                "Metric": ["NOPAT (M)", "FCF (M)", "ROIC", "Retention", "Growth", "WACC", "Asset Beta"],
                "Value": [
                    f"${nopat/1e6:.2f}M",
                    f"${fcf/1e6:.2f}M",
                    f"{roic:.2%}",
                    f"{retention:.2%}",
                    f"{growth:.2%}",
                    f"{wacc:.2%}",
                    f"{beta_a:.4f}"
                ]
            }
        ))

        # FRED: Industry Inv/Sales
        fred = get_fred_data("MRTSIR444USS", "2000-01-01", datetime.today().strftime('%Y-%m-%d'))
        if fred is not None and not fred.empty:
            st.subheader("Industry Inv/Sales Ratio (Building Materials & Garden Equipment)")
            st.line_chart(fred['value'])

        # Raw Statements (M)
        st.subheader("Raw Financials (Millions)")
        st.dataframe(format_millions(fin))
        st.dataframe(format_millions(bs))
        st.dataframe(format_millions(cf))

        # Working Capital Metrics
        wc_metrics = []
        for col in fin.columns[:5]:
            yr = pd.to_datetime(col).year
            inv = safe_value(bs, 'Inventory', col)
            ar = safe_value(bs, 'Accounts Receivable', col)
            ap = safe_value(bs, 'Accounts Payable', col)
            cogs = safe_value(fin, 'Cost Of Revenue', col)
            rev = safe_value(fin, 'Total Revenue', col)
            dio = (inv / cogs * 365) if cogs else np.nan
            dso = (ar / rev * 365) if rev else np.nan
            dpo = (ap / cogs * 365) if cogs else np.nan
            ccc = dio + dpo - dso
            nwc = (inv + ar - ap) / 1e6
            wc_metrics.append({"Year": yr, "DIO": round(dio), "DSO": round(dso), "DPO": round(dpo),
                                "CCC": round(ccc), "NWC (M)": round(nwc,2)})
        wc_df = pd.DataFrame(wc_metrics).set_index("Year")
        st.subheader("Working Capital Metrics")
        st.table(wc_df)
```
