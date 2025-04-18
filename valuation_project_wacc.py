import yfinance as yf
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# ——— Page config ———
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")

st.title("Annual Financials with NOPAT, FCF, Inv/Sales Overlay + Live & Historical Price")

st.markdown("""
This dashboard:
1. Pulls annual financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital,
   and Working‑Capital metrics (DIO, DSO, DPO, CCC).
2. Fetches the Industry Inventory/Sales ratio (Building Materials & Garden Equipment Dealers) from FRED.
3. Calculates and plots Home Depot’s Inventory/Sales ratio based on the same periods provided by yFinance.
4. Displays the live stock price and historical price chart for the selected ticker.
""")

# ——— Constants & Helpers ———

# Fetch the current 10-year Treasury yield (as a decimal, e.g. 0.035 for 3.5%)
def get_10yr_treasury_yield():
    hist = yf.Ticker("^TNX").history(period="1mo")
    return hist["Close"].iloc[-1] / 100 if not hist.empty else 0

API_KEY     = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL    = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio: Building Materials & Garden Equipment Dealers"}

def format_millions(x):
    return round(x/1e6,2) if pd.notnull(x) else 0

# Fetch function (no caching to avoid serialization issues)
def fetch_ticker(ticker):
    return yf.Ticker(ticker)

@st.cache_data
def get_fred_data(series_id, start_date, end_date):
    params = {
        "series_id": series_id,
        "api_key":   API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end":   end_date
    }
    r = requests.get(FRED_URL, params=params)
    if r.status_code != 200:
        st.error(f"Error fetching FRED: {r.status_code}")
        return None
    df = pd.DataFrame(r.json().get("observations", []))
    if df.empty: return None
    df["date"]  = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df

# ——— Main Section ———
ticker = st.text_input("Enter Ticker:", "AAPL")
if ticker:
    tk = fetch_ticker(ticker)
    info = tk.info

    # Live Price
    live_price = info.get('currentPrice') or info.get('regularMarketPrice')
    if live_price:
        st.metric(label="Live Price", value=f"${live_price:.2f}")

    # Historical Price
    st.subheader("Historical Price (Close)")
    hist = tk.history(period="max")
    if not hist.empty:
        st.line_chart(hist['Close'])
    else:
        st.warning("No historical price data available.")

        # Annual fundamentals
    annual_financials = tk.financials
    balance_sheet = tk.balance_sheet
    cashflow = tk.cashflow

    if not annual_financials.empty:
        latest_column = annual_financials.columns[0]

        # helper
        def safe_get(df, field):
            return format_millions(df.loc[field, latest_column]) if field in df.index else 0

        total_revenue = safe_get(annual_financials, 'Total Revenue')
        cost_of_revenue = safe_get(annual_financials, 'Cost Of Revenue')
        pretax_income = safe_get(annual_financials, 'Pretax Income')
        tax_provision_reported = safe_get(annual_financials, 'Tax Provision')
        depreciation = safe_get(annual_financials, 'Reconciled Depreciation')

        calculated_tax_rate = (tax_provision_reported / pretax_income) if pretax_income else 0
        nopat = pretax_income * (1 - calculated_tax_rate)

        depreciation_amortization_depletion = safe_get(cashflow, 'Depreciation Amortization Depletion')
        net_ppe_purchase_and_sale = abs(safe_get(cashflow, 'Net PPE Purchase And Sale'))
        change_in_working_capital = safe_get(cashflow, 'Change In Working Capital')

        fcf = nopat + depreciation_amortization_depletion - net_ppe_purchase_and_sale - change_in_working_capital

        long_term_debt = safe_get(balance_sheet, 'Long Term Debt')
        current_debt = safe_get(balance_sheet, 'Current Debt')
        total_debt = long_term_debt + current_debt

        total_equity = safe_get(balance_sheet, 'Total Equity Gross Minority Interest')
        total_invested_capital = total_debt + total_equity

        equity_beta = info.get('beta', 1)
                treasury_yield = get_10yr_treasury_yield()

        asset_beta = equity_beta * (1 / (1 + (1 - calculated_tax_rate) * (total_debt / total_equity))) if total_equity else 0

        expected_return_equity = treasury_yield + equity_beta * 0.05
        expected_return_debt = treasury_yield + 0.01

        d_ic_ratio = (total_debt / total_invested_capital) if total_invested_capital else 0
        e_ic_ratio = (total_equity / total_invested_capital) if total_invested_capital else 0

        wacc = ((e_ic_ratio * expected_return_equity) + (d_ic_ratio * expected_return_debt * (1 - calculated_tax_rate)))

        reinvestment_rate = ((net_ppe_purchase_and_sale - depreciation_amortization_depletion) + change_in_working_capital) / nopat if nopat else 0
        roic = nopat / total_invested_capital if total_invested_capital else 0
        growth_rate = reinvestment_rate / roic if roic else 0

        valuation_growth = nopat / (wacc - growth_rate) if wacc > growth_rate else 0
        valuation_no_growth = nopat / wacc if wacc else 0

        st.subheader("Summary Table")
        summary_table = pd.DataFrame({
            'Metric': ['NOPAT (M)', 'FCF (M)', 'Total Debt (M)', 'Total Equity (M)', 'WACC', 'ROIC', 'Growth Rate', 'Valuation (Growth)', 'Valuation (No Growth)', 'Market Cap (M)'],
            'Value': [nopat, fcf, total_debt, total_equity, wacc, roic, growth_rate, valuation_growth, valuation_no_growth, format_millions(info.get('marketCap', 0))]
        })
        st.table(summary_table)
    else:
        st.warning("No annual financials found for this ticker.")
        st.subheader("Summary")
        df_sum = pd.DataFrame({
            'Metric':['NOPAT (M)','FCF (M)','Total Debt (M)','Total Equity (M)','Market Cap (M)'],
            'Value':[nopat, fcf, totald, teq, format_millions(info.get('marketCap', 0))]
        })
        st.table(df_sum)

        # GAAP Income Statement
        st.subheader("GAAP Income Statement")
        for item in ["Total Revenue","Cost Of Revenue","Gross Profit","EBIT","EBITDA"]:
            if item in fin.index:
                st.write(f"**{item}**: {sv(fin, item, latest)/1e6:.2f}M")

        # Balance & Cash Flow
        st.subheader("Balance Sheet (M)")
        st.dataframe(bs.applymap(lambda x: x/1e6 if pd.notnull(x) else 0))
        st.subheader("Cash Flow (M)")
        st.dataframe(cf.applymap(lambda x: x/1e6 if pd.notnull(x) else 0))

        # Key Financials (Last 3 years)
        st.subheader("Key Financials (M) — Last 3 Years")
        metrics = ["Total Revenue","Gross Profit","EBIT","EBITDA"]
        cols3 = fin.columns[:3]
        kdf = fin.reindex(metrics).loc[:,cols3].applymap(lambda x: x/1e6 if pd.notnull(x) else 0)
        yrs = [pd.to_datetime(c).year for c in cols3][::-1]
        kdf.columns = yrs
        st.table(kdf)

        # YoY Growth
        st.subheader("YoY Growth (%)")
        gdf = kdf.pct_change(axis=1).iloc[:,1:]*100
        gdf.columns = [f"{y2} vs {y1}" for y1,y2 in zip(yrs[:-1],yrs[1:])]
        st.table(gdf)

        # Working Capital & CCC
        st.subheader("Working Capital Metrics (Days)")
        wdata=[]
        for c in cols3:
            inv = sv(bs,"Inventory",c)
            ar  = sv(bs,"Accounts Receivable",c)
            ap  = sv(bs,"Accounts Payable",c)
            cogs= sv(fin,"Cost Of Revenue",c)
            rev = sv(fin,"Total Revenue",c)
            dio = round(inv/cogs*365,1) if cogs else None
            dso = round(ar/rev*365,1) if rev else None
            dpo = round(ap/cogs*365,1) if cogs else None
            ccc = round((dio or 0)+(dpo or 0)-(dso or 0),1)
            wdata.append({"Year":pd.to_datetime(c).year,
                          "DIO":dio,"DSO":dso,"DPO":dpo,"CCC":ccc})
        wdf = pd.DataFrame(wdata).set_index("Year")
        st.table(wdf)

# ——— Overlay ———
st.markdown("---")
st.subheader("Inventory/Sales Overlay")
col1, col2 = st.columns(2)
with col1:
    sd = st.date_input("FRED Start", pd.to_datetime("2000-01-01"))
with col2:
    ed = st.date_input("FRED End",   pd.to_datetime("2025-12-31"))
if st.button("Plot Inv/Sales Overlay"):
    sid,_ = next(iter(FRED_SERIES.items()))
    df_f = get_fred_data(sid, sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
    if df_f is None:
        st.warning("No FRED data.")
    else:
        tk_hd = fetch_ticker("HD")
        fin_hd, bs_hd = tk_hd.financials, tk_hd.balance_sheet
        periods = [c for c in fin_hd.columns if c in bs_hd.columns]
        dates = [pd.to_datetime(c) for c in periods]
        invs = [sv(bs_hd, "Inventory", c) for c in periods]
        revs = [sv(fin_hd, "Total Revenue", c) for c in periods]
        ratios = [round(i/r*100/12,2) if r else None for i,r in zip(invs,revs)]
        hd_df = pd.DataFrame({"InvSales%": ratios}, index=dates)
        st.dataframe(hd_df)
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(df_f["date"], df_f["value"], label="Industry")
        ax.plot(hd_df.index, hd_df["InvSales%"], marker='o', label="Home Depot")
        ax.set_xlabel("Date")
        ax.set_ylabel("Inv/Sales %")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

st.markdown("Data from Yahoo Finance & FRED.")
