import yfinance as yf
import streamlit as st
import pandas as pd
import requests

# ——— Page config (must be first) ———
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")

st.title("Last Published Annual Financial Statements with NOPAT, FCF, and Invested Capital Breakdown")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials`, `balance_sheet`, and `cashflow` attributes,
computes NOPAT, FCF, Invested Capital, Working‑Capital metrics (DIO, DSO, DPO, CCC),
and fetches the Inventory/Sales ratio from FRED.
""")

# ——— Constants & Helpers ———
API_KEY     = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL    = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {
    "MRTSIR444USS": "Inventory/Sales Ratio: Building Materials & Garden Equipment Dealers"
}

def format_millions(v):
    return round(v / 1_000_000, 2) if v else 0

def to_millions(x):
    return round(x / 1e6, 2) if pd.notnull(x) else 0

@st.cache_data
def fetch_stock_data(ticker):
    return yf.Ticker(ticker)

@st.cache_data
def get_fred_data(series_id, start_date, end_date):
    params = {
        "series_id":         series_id,
        "api_key":           API_KEY,
        "file_type":         "json",
        "observation_start": start_date,
        "observation_end":   end_date,
    }
    resp = requests.get(FRED_URL, params=params)
    if resp.status_code != 200:
        st.error(f"Error fetching {series_id}: {resp.status_code}")
        return None
    data = resp.json().get("observations", [])
    if not data:
        return None
    df = pd.DataFrame(data)
    df["date"]  = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df

def display_gaap_income_statement(financials, latest_column):
    gaap_order = [
        "Total Revenue", "Operating Revenue", "Cost Of Revenue", "Gross Profit",
        "Operating Expense", "Selling General and Administrative", "Research & Development",
        "Operating Income", "Net Non Operating Interest Income Expense", "Interest Income Non Operating",
        "Interest Expense Non Operating", "Other Income Expense", "Other Non Operating Income (Expense)",
        "Pretax Income", "Tax Provision", "Net Income Common Stockholders", "Net Income",
        "Net Income Including Noncontrolling Interests", "Net Income Continuous Operations",
        "Diluted NI Available to Common Stockholders", "Basic EPS", "Diluted EPS",
        "Basic Average Shares", "Diluted Average Shares", "Total Operating Income as Reported",
        "Total Expenses", "Net Income from Continuing & Discontinued Operation", "Normalized Income",
        "Interest Income", "Interest Expense", "Net Interest Income", "EBIT", "EBITDA",
        "Reconciled Cost of Revenue", "Reconciled Depreciation",
        "Net Income from Continuing Operation Net Minority Interest", "Normalized EBITDA", "Tax Rate for Calcs"
    ]
    for item in gaap_order:
        if item in financials.index:
            val = format_millions(financials.at[item, latest_column])
            st.write(f"**{item}**: {val}M")

# ——— Main Financials Section ———

ticker = st.text_input("Enter Ticker:", "AAPL")
if ticker:
    tk   = fetch_stock_data(ticker)
    fin  = tk.financials
    bs   = tk.balance_sheet
    cf   = tk.cashflow
    info = tk.info

    if not fin.empty:
        latest = fin.columns[0]

        # 1) Summary Table
        total_revenue = format_millions(fin.at.get("Total Revenue", {}).get(latest, 0))
        # (or compute via safe_get when needed)
        # ... compute NOPAT, FCF, etc. using existing logic ...
        # For brevity, assume you retain your original summary logic here
        st.subheader("Summary Table")
        # st.table(...)  # keep your original summary_table code

        # 2) GAAP Structured View
        st.subheader("Annual Financial Statements (GAAP Structured View)")
        display_gaap_income_statement(fin, latest)

        # 3) Balance Sheet & Cash Flow
        st.subheader("Balance Sheet (Last Published)")
        st.write(bs)
        st.subheader("Cash Flow Statement (Last Published)")
        st.write(cf)

        # 4) Key Financials (M) — Last 3 Years
        metrics = ["Total Revenue","Gross Profit","EBITDA","EBIT"]
        last3   = fin.columns[:3]
        key_df  = fin.reindex(metrics).loc[:, last3].applymap(to_millions)
        years   = [pd.to_datetime(c).year for c in last3][::-1]
        key_df.columns = years
        st.subheader("Key Financials (M) — Last 3 Years")
        st.table(key_df)

        # 5) Year‑over‑Year Growth (%)
        grow = key_df.pct_change(axis=1).iloc[:,1:] * 100
        grow.columns = [f"{c2} vs {c1}" for c1,c2 in zip(years[:-1], years[1:])]
        st.subheader("Year‑over‑Year Growth (%)")
        st.table(grow)

        # 6) Working Capital & CCC
        def sv(df, idx, col):
            try: return df.at[idx, col]
            except: return 0

        raw, wc = {}, {}
        for col in last3:
            yr  = pd.to_datetime(col).year
            inv = sv(bs, "Inventory", col)
            ar  = sv(bs, "Accounts Receivable", col)
            ap  = sv(bs, "Accounts Payable", col)
            cogs= sv(fin, "Cost Of Revenue", col)
            rev = sv(fin, "Total Revenue", col)

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

# ——— FRED Section ———

st.markdown("---")
st.subheader("FRED: Inventory/Sales Ratio")
col1, col2 = st.columns(2)
with col1:
    start = st.date_input("Start Date", pd.to_datetime("2000-01-01"))
with col2:
    end   = st.date_input("End Date",   pd.to_datetime("2025-12-31"))

if st.button("Fetch FRED Data"):
    sid, desc = next(iter(FRED_SERIES.items()))
    df_f = get_fred_data(sid, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    if df_f is not None:
        st.subheader(f"{desc} ({sid})")
        st.dataframe(df_f.set_index("date"))
        st.line_chart(df_f.set_index("date")["value"])
    else:
        st.warning("No data for that range.")

st.markdown("Data sourced from Yahoo Finance & FRED.")
