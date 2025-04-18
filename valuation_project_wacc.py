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
3. Home Depot’s Inventory/Sales ratio from its annual statements.
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

        # Compute core metrics
        def safe_get(df, field):
            return df.at[field, latest] if field in df.index else 0

        total_revenue = format_millions(safe_get(fin, 'Total Revenue'))
        cost_of_revenue = format_millions(safe_get(fin, 'Cost Of Revenue'))
        pretax_income = format_millions(safe_get(fin, 'Pretax Income'))
        tax_prov = format_millions(safe_get(fin, 'Tax Provision'))
        dep = format_millions(safe_get(fin, 'Reconciled Depreciation'))

        tax_rate = (tax_prov / pretax_income) if pretax_income else 0
        nopat = pretax_income * (1 - tax_rate)

        dep_amort = format_millions(safe_get(cf, 'Depreciation Amortization Depletion'))
        ppe = abs(format_millions(safe_get(cf, 'Net PPE Purchase And Sale')))
        chg_wc = format_millions(safe_get(cf, 'Change In Working Capital'))
        fcf = nopat + dep_amort - ppe - chg_wc

        ltd = format_millions(safe_get(bs, 'Long Term Debt'))
        curr_d = format_millions(safe_get(bs, 'Current Debt'))
        td = ltd + curr_d
        te = format_millions(safe_get(bs, 'Total Equity Gross Minority Interest'))
        tic = td + te

        beta = info.get('beta', 1)
        ry = get_fred_data  # placeholder to avoid confusion
        # skip WACC for brevity

        # Summary table
        with st.expander("Summary Table", expanded=True):
            summary = pd.DataFrame({
                'Metric': ['NOPAT (M)','FCF (M)','Total Debt (M)','Total Equity (M)','Market Cap (M)'],
                'Value': [nopat, fcf, td, te, format_millions(info.get('marketCap',0))]
            })
            st.table(summary)

        # GAAP structured view
        display_gaap_income_statement(fin, latest)

        # Balance & Cash Flow
        st.subheader("Balance Sheet")
        st.dataframe(bs.applymap(lambda x: to_millions(x)))
        st.subheader("Cash Flow Statement")
        st.dataframe(cf.applymap(lambda x: to_millions(x)))

        # Key Financials last 3 years
        metrics = ["Total Revenue","Gross Profit","EBITDA","EBIT"]
        recent = fin.columns[:3]
        key_df = fin.reindex(metrics).loc[:, recent].applymap(to_millions)
        years = [pd.to_datetime(c).year for c in recent][::-1]
        key_df.columns = years
        st.subheader("Key Financials (M) — Last 3 Years")
        st.table(key_df)

        # YoY Growth
        grow = key_df.pct_change(axis=1).iloc[:,1:] * 100
        grow.columns = [f"{y2} vs {y1}" for y1,y2 in zip(years[:-1], years[1:])]
        st.subheader("Year‑over‑Year Growth (%)")
        st.table(grow)

        # Working capital & CCC
        def sv(df, idx, col):
            try: return df.at[idx, col]
            except: return 0

        raw, wc = {}, {}
        for col in recent:
            yr = pd.to_datetime(col).year
            inv = sv(bs, "Inventory", col)
            ar  = sv(bs, "Accounts Receivable", col)
            ap  = sv(bs, "Accounts Payable", col)
            cogs = sv(fin, "Cost Of Revenue", col)
            rev  = sv(fin, "Total Revenue", col)

            inv_m, ar_m = to_millions(inv), to_millions(ar)
            ap_m, cogs_m = to_millions(ap), to_millions(cogs)
            rev_m = to_millions(rev)

            dio = round((inv/cogs)*365,1) if cogs else None
            dso = round((ar/rev)*365,1) if rev else None
            dpo = round((ap/cogs)*365,1) if cogs else None
            ccc = round((dio or 0)+(dpo or 0)-(dso or 0),1)

            raw[yr] = [inv_m, ar_m, ap_m, cogs_m, rev_m]
            wc[yr]  = [dio, dso, dpo, ccc]

        raw_df = pd.DataFrame(raw, index=["Inventory (M)","Accounts Receivable (M)","Accounts Payable (M)","COGS (M)","Revenue (M)"])
        st.subheader("Working Capital Raw Inputs (M)")
        st.table(raw_df)

        wc_df = pd.DataFrame(wc, index=["DIO","DSO","DPO","CCC"])
        st.subheader("Working Capital Metrics (Days)")
        st.table(wc_df)

# ——— FRED + Home Depot Overlay ———
st.markdown("---")
st.subheader("Inventory/Sales Ratio: Industry vs. Home Depot (2000–Present)")
col1, col2 = st.columns(2)
with col1:
    sd = st.date_input("FRED Start Date", pd.to_datetime("2000-01-01"))
with col2:
    ed = st.date_input("FRED End Date",   pd.to_datetime("2025-12-31"))

if st.button("Fetch & Plot Historical Inv/Sales Overlay"):
    # 1) Fetch Industry series from FRED
    sid, desc = next(iter(FRED_SERIES.items()))
    df_f = get_fred_data(sid, sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
    if df_f is None:
        st.warning("No FRED data.")
    else:
        # Display FRED raw data
        st.subheader("FRED Industry Inv/Sales Raw Data")
        st.dataframe(df_f.set_index("date"))

        # 2) Fetch Home Depot annual fundamentals via Alpha Vantage for full history
        from alpha_vantage.fundamentaldata import FundamentalData
        ALPHA_KEY = "059VKV2VPORKW7KA"
        fd_av = FundamentalData(key=ALPHA_KEY, output_format="json")
        bs_json, _ = fd_av.get_balance_sheet_annual(symbol="HD")
        is_json, _ = fd_av.get_income_statement_annual(symbol="HD")
        bs_reports = bs_json.get("annualReports", [])
        is_reports = is_json.get("annualReports", [])

        # Build historical DataFrame
        hist_data = []
        for bs_r, is_r in zip(bs_reports, is_reports):
            date = pd.to_datetime(bs_r.get("fiscalDateEnding"))
            inv  = float(bs_r.get("inventory", 0))
            rev  = float(is_r.get("totalRevenue", 0))
            ratio = (inv / rev * 100) if rev else None
            hist_data.append({"date": date, "Inv/Sales (%)": ratio})
        hd_hist_df = pd.DataFrame(hist_data).set_index("date").sort_index()

        # Display Home Depot historical ratio
        st.subheader("Home Depot Annual Inv/Sales Ratio (%) — Historical")
        st.dataframe(hd_hist_df)

        # 3) Plot overlay
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_f["date"], df_f["value"], label="Industry Inv/Sales (FRED)")
        ax.plot(hd_hist_df.index, hd_hist_df['Inv/Sales (%)'], marker='o', linestyle='-', label="Home Depot Inv/Sales (Annual)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Inv/Sales Ratio (%)")
        ax.set_title("Industry vs. Home Depot Inventory/Sales Ratio (2000–Present)")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

st.markdown("Data sourced from Yahoo Finance, FRED & Alpha Vantage.")



