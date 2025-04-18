import yfinance as yf
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# ——— Page config ———
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")

st.title("Annual Financials with NOPAT, FCF, and Invested Capital + Inv/Sales Overlay")

st.markdown("""
This dashboard:
1. Pulls annual financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital,
   and Working‑Capital metrics (DIO, DSO, DPO, CCC).
2. Fetches the Industry Inventory/Sales ratio (Building Materials & Garden Equipment Dealers) from FRED.
3. Calculates and plots Home Depot’s Inventory/Sales ratio based on the same periods provided by yFinance.
""")

# ——— Constants & Helpers ———
API_KEY     = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL    = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio: Building Materials & Garden Equipment Dealers"}

def format_millions(x):
    return round(x/1e6,2) if pd.notnull(x) else 0

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
    if r.status_code!=200:
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
    fin = tk.financials
    bs  = tk.balance_sheet
    cf  = tk.cashflow
    info= tk.info

    if fin.empty:
        st.warning("No annual financials found for this ticker.")
    else:
        latest = fin.columns[0]
        # Safe getter
        def sv(df, field, col):
            return df.at[field, col] if field in df.index else 0

        # Compute core metrics
        revenue = sv(fin, 'Total Revenue', latest)
        pretax  = sv(fin, 'Pretax Income', latest)
        taxprov = sv(fin, 'Tax Provision', latest)
        dep     = sv(fin, 'Reconciled Depreciation', latest)
        taxrate = (taxprov/pretax) if pretax else 0
        nopat   = (pretax * (1-taxrate))/1e6
        damo    = sv(cf, 'Depreciation Amortization Depletion', latest)
        ppe     = abs(sv(cf, 'Net PPE Purchase And Sale', latest))
        wcchg   = sv(cf, 'Change In Working Capital', latest)
        fcf     = (nopat + damo - ppe - wcchg)/1e6
        ltd     = sv(bs, 'Long Term Debt', latest)
        currd   = sv(bs, 'Current Debt', latest)
        totald  = (ltd+currd)/1e6
        teq     = sv(bs, 'Total Equity Gross Minority Interest', latest)/1e6

        # Summary
        st.subheader("Summary")
        df_sum = pd.DataFrame({
            'Metric':['NOPAT (M)','FCF (M)','Total Debt (M)','Total Equity (M)','Market Cap (M)'],
            'Value':[nopat, fcf, totald, teq, format_millions(info.get('marketCap',0))]
        })
        st.table(df_sum)

        # GAAP expander
        st.subheader("GAAP Income Statement")
        for item in ["Total Revenue","Cost Of Revenue","Gross Profit","EBIT","EBITDA"]:
            if item in fin.index:
                st.write(f"**{item}**: {format_millions(sv(fin,item,latest))}M")

        # Balance & Cashflow
        st.subheader("Balance Sheet (M)")
        st.dataframe(bs.applymap(format_millions))
        st.subheader("Cash Flow (M)")
        st.dataframe(cf.applymap(format_millions))

        # Key Financials (Last 3 years)
        st.subheader("Key Financials (M) — Last 3 Years")
        metrics = ["Total Revenue","Gross Profit","EBIT","EBITDA"]
        cols3 = fin.columns[:3]
        kdf = fin.reindex(metrics).loc[:,cols3].applymap(format_millions)
        yrs = [pd.to_datetime(c).year for c in cols3][::-1]
        kdf.columns=yrs
        st.table(kdf)

        # YoY Growth
        st.subheader("YoY Growth (%)")
        gdf = kdf.pct_change(axis=1).iloc[:,1:]*100
        gdf.columns=[f"{y2} vs {y1}" for y1,y2 in zip(yrs[:-1],yrs[1:])]
        st.table(gdf)

        # Working Capital & CCC
        st.subheader("Working Capital Metrics (Days)")
        wdata=[]
        for c in cols3:
            inv=sv(bs,"Inventory",c)
            ar=sv(bs,"Accounts Receivable",c)
            ap=sv(bs,"Accounts Payable",c)
            cogs=sv(fin,"Cost Of Revenue",c)
            rev=sv(fin,"Total Revenue",c)
            dio=round(inv/cogs*365,1) if cogs else None
            dso=round(ar/rev*365,1) if rev else None
            dpo=round(ap/cogs*365,1) if cogs else None
            ccc=round((dio or 0)+(dpo or 0)-(dso or 0),1)
            wdata.append({"Year":pd.to_datetime(c).year,
                          "DIO":dio,"DSO":dso,"DPO":dpo,"CCC":ccc})
        wdf=pd.DataFrame(wdata).set_index("Year")
        st.table(wdf)

# ——— Overlay ———
st.markdown("---")
st.subheader("Inventory/Sales Overlay")
col1,col2=st.columns(2)
with col1:
    sd=st.date_input("FRED Start",pd.to_datetime("2000-01-01"))
with col2:
    ed=st.date_input("FRED End",pd.to_datetime("2025-12-31"))
if st.button("Plot Inv/Sales Overlay"):
    # FRED
    sid,_=next(iter(FRED_SERIES.items()))
    df_f=get_fred_data(sid,sd.strftime("%Y-%m-%d"),ed.strftime("%Y-%m-%d"))
    if df_f is None:
        st.warning("No FRED data.")
    else:
        # HD annual
        tk=fetch_ticker("HD")
        fin_hd,bs_hd = tk.financials,tk.balance_sheet
        periods=[c for c in fin_hd.columns if c in bs_hd.columns]
        dates=[pd.to_datetime(c) for c in periods]
        invs=[sv(bs_hd,"Inventory",c) for c in periods]
        revs=[sv(fin_hd,"Total Revenue",c) for c in periods]
        ratios=[round(i/r*100/12,2) if r else None for i,r in zip(invs,revs)]
        hd_df=pd.DataFrame({"InvSales%":ratios},index=dates)
        st.dataframe(hd_df)
        fig,ax=plt.subplots(figsize=(10,5))
        ax.plot(df_f["date"],df_f["value"],label="Industry")
        ax.plot(hd_df.index,hd_df["InvSales%"],marker='o',label="Home Depot")
        ax.set_xlabel("Date");ax.set_ylabel("Inv/Sales %")
        ax.legend();ax.grid(True)
        st.pyplot(fig)

st.markdown("Data from Yahoo Finance & FRED.")
