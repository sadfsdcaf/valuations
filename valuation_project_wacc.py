import yfinance as yf
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# ——— Page config ———
st.set_page_config(page_title="Financial + FRED Dashboard", layout="wide")

st.title("Annual Financials with NOPAT, FCF, Inv/Sales + Live & Historical Price")

st.markdown("""
This dashboard:
1. Pulls annual financial statements from Yahoo Finance to compute NOPAT, FCF, Invested Capital, and Working‑Capital metrics (DIO, DSO, DPO, CCC).
2. Fetches the Industry Inventory/Sales ratio (Building Materials & Garden Equipment Dealers) from FRED.
3. Calculates and plots Home Depot’s Inventory/Sales ratio based on the same periods provided by yFinance.
4. Displays the live stock price and historical price chart for the selected ticker.
""")

# ——— Helpers ———
def format_millions(x): return round(x/1e6,2) if pd.notnull(x) else 0

def get_10yr_treasury_yield():
    hist = yf.Ticker("^TNX").history(period="1mo")
    return hist["Close"].iloc[-1]/100 if not hist.empty else 0

API_KEY = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio: Building Materials & Garden Equipment Dealers"}

# Fetch ticker (no cache)
def fetch_ticker(t): return yf.Ticker(t)

@st.cache_data
def get_fred_data(series_id, start, end):
    r=requests.get(FRED_URL, params={"series_id":series_id,"api_key":API_KEY,"file_type":"json","observation_start":start,"observation_end":end})
    if r.status_code!=200: st.error(f"Error fetching FRED: {r.status_code}"); return None
    df=pd.DataFrame(r.json().get("observations",[]))
    if df.empty: return None
    df["date"]=pd.to_datetime(df["date"])
    df["value"]=pd.to_numeric(df["value"],errors="coerce")
    return df

# ——— Main Section ———
ticker=st.text_input("Enter Ticker:","AAPL")
if ticker:
    tk=fetch_ticker(ticker)
    info=tk.info

    # Live Price
    live=info.get('currentPrice') or info.get('regularMarketPrice')
    if live: st.metric("Live Price", f"${live:.2f}")

    # Historical Price
    st.subheader("Historical Price (Close)")
    hist=tk.history(period="max")
    if not hist.empty: st.line_chart(hist['Close'])
    else: st.warning("No historical price.")

    # Annual data
    fin=tk.financials; bs=tk.balance_sheet; cf=tk.cashflow
    if fin.empty:
        st.warning("No annual financials found.")
    else:
        latest=fin.columns[0]
        def sv(df,field): return df.at[field,latest] if field in df.index else 0

        # Compute metrics
        total_revenue=sv(fin,'Total Revenue')
        pretax=sv(fin,'Pretax Income'); taxprov=sv(fin,'Tax Provision')
        taxrate=(taxprov/pretax) if pretax else 0
        nopat=pretax*(1-taxrate)
        damo=sv(cf,'Depreciation Amortization Depletion')
        ppe=abs(sv(cf,'Net PPE Purchase And Sale'))
        wcchg=sv(cf,'Change In Working Capital')
        fcf=nopat+damo-ppe-wcchg
        ltd=sv(bs,'Long Term Debt'); cd=sv(bs,'Current Debt')
        td=ltd+cd; te=sv(bs,'Total Equity Gross Minority Interest')
        tic=td+te
        beta=info.get('beta',1)
        ry=get_10yr_treasury_yield()
        er_eq=ry+beta*0.05; er_de=ry+0.01
        di=td/tic if tic else 0; ei=te/tic if tic else 0
        wacc=(ei*er_eq)+(di*er_de*(1-taxrate))
        rr=((ppe-damo)+wcchg)/nopat if nopat else 0
        roic=nopat/tic if tic else 0
        gr=rr/roic if roic else 0
        val_g=nopat/(wacc-gr) if wacc>gr else 0
        val_ng=nopat/wacc if wacc else 0

        # Summary Table
        st.subheader("Summary Table")
        df_sum=pd.DataFrame({
            'Metric':['NOPAT (M)','FCF (M)','Total Debt (M)','Total Equity (M)','WACC','ROIC','Growth Rate','Valuation (Growth)','Valuation (No Growth)','Market Cap (M)'],
            'Value':[nopat/1e6,fcf/1e6,td/1e6,te/1e6,wacc,roic,gr,val_g,val_ng,format_millions(info.get('marketCap',0))]
        })
        st.table(df_sum)

        # GAAP Income
        st.subheader("GAAP Income Statement")
        for itm in ["Total Revenue","Cost Of Revenue","Gross Profit","EBIT","EBITDA"]:
            if itm in fin.index: st.write(f"**{itm}**: {sv(fin,itm)/1e6:.2f}M")

        # Balance & Cashflow
        st.subheader("Balance Sheet (M)")
        st.dataframe(bs.applymap(format_millions))
        st.subheader("Cash Flow (M)")
        st.dataframe(cf.applymap(format_millions))

        # Key Financials last 3 yrs
        st.subheader("Key Financials (M) — Last 3 Years")
        mets=["Total Revenue","Gross Profit","EBIT","EBITDA"]
        c3=fin.columns[:3]
        kdf=fin.reindex(mets).loc[:,c3].applymap(format_millions)
        yrs=[pd.to_datetime(c).year for c in c3][::-1]
        kdf.columns=yrs; st.table(kdf)

        # YoY Growth
        st.subheader("YoY Growth (%)")
        gdf=kdf.pct_change(axis=1).iloc[:,1:]*100
        gdf.columns=[f"{b} vs {a}" for a,b in zip(yrs[:-1],yrs[1:])]
        st.table(gdf)

        # Working Capital & CCC
        st.subheader("Working Capital Metrics (Days)")
        wc_list=[]
        for c in c3:
            inv=sv(bs,'Inventory'); ar=sv(bs,'Accounts Receivable'); ap=sv(bs,'Accounts Payable')
            cog=sv(fin,'Cost Of Revenue'); rev=sv(fin,'Total Revenue')
            dio=round(inv/cog*365,1) if cog else None
            dso=round(ar/rev*365,1) if rev else None
            dpo=round(ap/cog*365,1) if cog else None
            ccc=round((dio or 0)+(dpo or 0)-(dso or 0),1)
            wc_list.append({'Year':pd.to_datetime(c).year,'DIO':dio,'DSO':dso,'DPO':dpo,'CCC':ccc})
        wc_df=pd.DataFrame(wc_list).set_index('Year'); st.table(wc_df)

# ——— Overlay ———
st.markdown("---")
st.subheader("Inventory/Sales Overlay")
col1,col2=st.columns(2)
with col1: sd=st.date_input("FRED Start",pd.to_datetime("2000-01-01"))
with col2: ed=st.date_input("FRED End",pd.to_datetime("2025-12-31"))
if st.button("Plot Inv/Sales Overlay"):
    sid,_=next(iter(FRED_SERIES.items()))
    df_f=get_fred_data(sid,sd.strftime('%Y-%m-%d'),ed.strftime('%Y-%m-%d'))
    if df_f is None: st.warning('No FRED data.')
    else:
        tk_hd=fetch_ticker('HD'); f_hd, b_hd=tk_hd.financials,tk_hd.balance_sheet
        per=[c for c in f_hd.columns if c in b_hd.columns]
        dt=[pd.to_datetime(c) for c in per]
        invs=[sv(b_hd,'Inventory') for c in per]
        revs=[sv(f_hd,'Total Revenue') for c in per]
        r=[round(i/r*100/12,2) if r else None for i,r in zip(invs,revs)]
        hd_df=pd.DataFrame({'InvSales%':r},index=dt); st.dataframe(hd_df)
        fig,ax=plt.subplots(figsize=(10,5))
        ax.plot(df_f['date'],df_f['value'],label='Industry')
        ax.plot(hd_df.index,hd_df['InvSales%'],marker='o',label='Home Depot')
        ax.set_xlabel('Date'); ax.set_ylabel('Inv/Sales %'); ax.legend(); ax.grid(True)
        st.pyplot(fig)

st.markdown("Data from Yahoo Finance & FRED.")
