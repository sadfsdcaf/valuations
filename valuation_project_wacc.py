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
def format_millions(x):
    # divide by 1e6 and convert to whole number
    return int(round(x/1e6)) if pd.notnull(x) else 0

def get_10yr_treasury_yield():
    hist = yf.Ticker("^TNX").history(period="1mo")
    return hist["Close"].iloc[-1] / 100 if not hist.empty else 0

API_KEY = "26c01b09f8083e30a1ee9cb929188a74"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {"MRTSIR444USS": "Industry Inv/Sales Ratio: Building Materials & Garden Equipment Dealers"}

# Fetch ticker (no cache)
def fetch_ticker(t): return yf.Ticker(t)

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

# ——— Main Section ———
ticker = st.text_input("Enter Ticker:", "HD")
if ticker:
    tk = fetch_ticker(ticker)
    info = tk.info

    # Live Price
    live = info.get('currentPrice') or info.get('regularMarketPrice')
    if live:
        # show as whole number
        st.metric("Live Price", f"${live:.0f}")

    # Historical Price
    st.subheader("Historical Price (Close)")
    hist = tk.history(period="max")
    if not hist.empty:
        st.line_chart(hist['Close'])
    else:
        st.warning("No historical price.")

    # Annual data
    fin = tk.financials
    bs  = tk.balance_sheet
    cf  = tk.cashflow
    if fin.empty:
        st.warning("No annual financials found.")
    else:
        latest = fin.columns[0]
        # Safe getters
        def safe_latest(df, field): return df.at[field, latest] if field in df.index else 0
        def safe_col(df, field, col): return df.at[field, col] if field in df.index else 0

        # Compute metrics
        total_revenue = safe_latest(fin, 'Total Revenue')
        pretax         = safe_latest(fin, 'Pretax Income')
        taxprov        = safe_latest(fin, 'Tax Provision')
        net_ppe        = safe_latest(fin, 'Net PPE')
        gross_ppe      = safe_latest(fin, 'Gross PPE')
        taxrate        = (taxprov / pretax) if pretax else 0
        ebit           = safe_latest(fin, 'EBIT')
        nopat          = safe_latest(fin, 'EBIT') * (1 - taxrate)
        damo           = safe_latest(cf, 'Depreciation Amortization Depletion')
        ppe            = abs(safe_latest(cf, 'Net PPE Purchase And Sale'))
        wcchg          = safe_latest(cf, 'Change In Working Capital')
        fcf            = nopat + damo - ppe - wcchg

        # Debt & Equity
        ltd = safe_latest(bs, 'Long Term Debt')
        std = safe_latest(bs, 'Short Term Debt')
        td  = ltd + std
        te  = safe_latest(bs, 'Total Equity Gross Minority Interest')
        tic = td + te

        # WACC inputs
        beta  = info.get('beta', 1)
        ry    = get_10yr_treasury_yield()
        er_eq = ry + beta * 0.05
        er_de = ry + 0.01
        di    = td / tic if tic else 0
        ei    = te / tic if tic else 0
        wacc  = (ei * er_eq) + (di * er_de * (1 - taxrate))

        # ROIC & growth
        rr   = ((ppe - damo) + wcchg) / nopat if nopat else 0
        roic = nopat / tic if tic else 0
        gr   = rr / roic if roic else 0

        # Valuations
        val_g  = nopat / (wacc - gr) if wacc > gr else 0
        val_ng = nopat / wacc if wacc else 0

        # EBIT-based FCF

        ebit_nopat = safe_latest(fin, 'EBIT') * (1 - taxrate)
        fcf_ebit   = ebit_nopat + damo - ppe - wcchg

        # Summary Table
        st.subheader("Summary Table")
        df_sum = pd.DataFrame({
            'Metric': [
                'NOPAT (M)',
                'FCF (pretax NOPAT, M)',
                'FCF (EBIT basis, M)',
                'Total Debt (M)',
                'Total Equity (M)',
                'Invested Capital (M)',
                'WACC',
                'Beta',
                'ROIC',
                'Growth Rate',
                'Valuation (Growth)',
                'Valuation (No Growth)',
                'Market Cap (M)'
            ],
            'Value': [
                nopat/1e6,
                fcf/1e6,
                fcf_ebit/1e6,
                td/1e6,
                te/1e6,
                tic/1e6,
                wacc,
                beta,
                roic,
                gr,
                val_g/1e6,
                val_ng/1e6,
                info.get('marketCap', 0)/1e6
            ]
        })
        # round all to integers
        df_sum['Value'] = df_sum['Value'].round().astype(int)
        st.table(df_sum)
       
        
        # First, verify your field names
        st.write("Available PPE fields:", [i for i in fin.index if 'PPE' in i])
        
        # Then pull with the exact names:
        gross_ppe = safe_latest(fin, "Property, Plant & Equipment, Gross")
        net_ppe   = safe_latest(fin, "Property, Plant & Equipment, Net")
        
        # Build & display
        metrics = {
            "Gross PPE (M)": gross_ppe/1e6,
            "Net   PPE (M)": net_ppe/1e6
        }
        st.subheader("PPE on the Balance Sheet")
        df_ppe = pd.DataFrame({
            "Metric": list(metrics.keys()),
            "Value": [round(v) for v in metrics.values()]
        })
        st.table(df_ppe)
        
        # Free Cash Flow
        st.subheader("Free Cash Flow")
        metrics = {
            "EBIT": safe_latest(fin, "EBIT"),
            "NOPAT": nopat,
            "Depreciation": demo,
            "Capex": net_ppe,
            "Change in NWC": wcchg
            "Free Cash Flow": ffc 

        }
        for name, val in metrics.items():
            st.write(f"**{name}**: {val/1e6:.0f}M")

        # Financial Statement (M)
        st.subheader("Income Statement (M) — Last Published")
        st.dataframe(fin.applymap(format_millions))
        st.subheader("Balance Sheet (M)")
        st.dataframe(bs.applymap(format_millions))
        st.subheader("Cash Flow (M)")
        st.dataframe(cf.applymap(format_millions))

        # Key Financials last 5 yrs
        st.subheader("Key Financials (M) — Last 5 Years")
        mets = ["Total Revenue", "Gross Profit", "EBIT", "EBITDA"]
        last5 = fin.columns[:5]
        kdf = fin.reindex(mets).loc[:, last5].applymap(format_millions)
        yrs = [pd.to_datetime(c).year for c in last5][::-1]
        kdf.columns = yrs
        st.table(kdf)

        # YoY Growth
        st.subheader("Year‑over‑Year Growth (%)")
        gdf = (kdf.pct_change(axis=1).iloc[:,1:] * 100).round().astype(int)
        gdf.columns = [f"{b} vs {a}" for a,b in zip(yrs[:-1], yrs[1:])]
        st.table(gdf)

        # Working Capital & CCC
        st.subheader("Working Capital Metrics (Days) + ΔNWC")
        wc_list = []
        for c in last5:
            inv  = safe_col(bs, 'Inventory', c) or 0
            ar   = safe_col(bs, 'Accounts Receivable', c) or 0
            ap   = safe_col(bs, 'Accounts Payable', c) or 0
            cogs = safe_col(fin, 'Cost Of Revenue', c) or 0
            rev  = safe_col(fin, 'Total Revenue', c) or 0
        
            # days metrics
            dio  = int(round(inv  / cogs * 365)) if cogs else None
            dso  = int(round(ar   / rev  * 365)) if rev  else None
            dpo  = int(round(ap   / cogs * 365)) if cogs else None
            ccc  = int(round((dio or 0) + (dpo or 0) - (dso or 0)))
        
            # NWC and its year‑over‑year change placeholder
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
        
        # compute ΔNWC (absolute change in millions)
        wc_df['ΔNWC'] = wc_df['NWC'].diff().round(2)
        
        # display as table
        st.table(wc_df)


# ——— Overlay ———
st.markdown("---")
st.subheader("Inventory/Sales Overlay")
col1, col2 = st.columns(2)
with col1:
    sd = st.date_input("FRED Start", pd.to_datetime("2000-01-01"))
with col2:
    ed = st.date_input("FRED End", pd.to_datetime("2025-12-31"))
if st.button("Plot Inv/Sales Overlay"):
    sid,_ = next(iter(FRED_SERIES.items()))
    df_f  = get_fred_data(sid, sd.strftime('%Y-%m-%d'), ed.strftime('%Y-%m-%d'))
    if df_f is None:
        st.warning('No FRED data.')
    else:
        tk_hd = fetch_ticker('HD')
        f_hd, b_hd = tk_hd.financials, tk_hd.balance_sheet
        per = [c for c in f_hd.columns if c in b_hd.columns]
        dates  = [pd.to_datetime(c) for c in per]
        invs   = [safe_col(b_hd, 'Inventory', c) for c in per]
        revs   = [safe_col(f_hd, 'Total Revenue', c) for c in per]
        ratios = [round(i/r*100/12,2) if r else None for i,r in zip(invs,revs)]
        hd_df  = pd.DataFrame({'InvSales%': ratios}, index=dates)
        st.dataframe(hd_df)
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(df_f['date'], df_f['value'], label='Industry')
        ax.plot(hd_df.index, hd_df['InvSales%'], marker='o', label='Home Depot')
        ax.set_xlabel('Date')
        ax.set_ylabel('Inv/Sales %')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

st.markdown("Data from Yahoo Finance & FRED.")
