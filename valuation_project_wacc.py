import yfinance as yf
import streamlit as st
import pandas as pd
import numpy as np
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
ticker = st.text_input("Enter Ticker:", "DOCN")
if ticker:
    tk = fetch_ticker(ticker)
    info = tk.info

    # Live Price
    live = info.get('currentPrice') or info.get('regularMarketPrice')
    if live:
        st.metric("Live Price", f"${live:.0f}")

    # Historical Price
    st.subheader("Historical Price (Close)")
    hist = tk.history(period="max")
    if not hist.empty:
        st.line_chart(hist['Close'])
    else:
        st.warning("No historical price.")

    # Annual data
    # Annual Financials
    tk_fin = tk.financials
    tk_bs = tk.balance_sheet
    tk_cf = tk.cashflow
    
    if tk_fin.empty:
        print("No annual financials found.")
    else:
        latest = tk_fin.columns[0]
    
        # Pull and display live 10yr Treasury yield
        ry = get_10yr_treasury_yield()
        print(f"10-Year Treasury Yield (Risk-Free Rate): {ry:.4f}")
    
        # Metrics
        total_revenue = safe_latest(tk_fin, 'Total Revenue')
        pretax = safe_latest(tk_fin, 'Pretax Income')
        taxprov = safe_latest(tk_fin, 'Tax Provision')
        net_ppe = safe_latest(tk_fin, 'Net PPE')
        gross_ppe = safe_latest(tk_fin, 'Gross PPE')
        capex = safe_latest(tk_cf, 'Capital Expenditure')
        taxrate = (taxprov / pretax) if pretax else 0
        ebit = safe_latest(tk_fin, 'EBIT')
        ebitda = safe_latest(tk_fin, 'EBITDA')
        damo = safe_latest(tk_cf, 'Depreciation Amortization Depletion')
        ppe = abs(safe_latest(tk_cf, 'Net PPE'))
        wcchg = safe_latest(tk_cf, 'Change In Working Capital')
    
        # NOPAT and FCF
        nopat = ebit * (1 - taxrate)
        fcf = nopat + damo - capex - wcchg
    
        # Debt & Equity
        ltd = safe_latest(tk_bs, 'Long Term Debt')
        std = safe_latest(tk_bs, 'Short Term Debt')
        td = ltd + std
        te = safe_latest(tk_bs, 'Total Equity Gross Minority Interest')
        tic = safe_latest(tk_bs, 'Invested Capital')
    
        # Cost of Capital Inputs
        market_risk_premium = 0.05
        credit_spread = 0.01
    
        beta = info.get('beta', 1)
    
        er_eq = ry + beta * market_risk_premium
        er_de = ry + credit_spread
    
        print("\n--- Cost of Equity and Cost of Debt Calculation ---")
        print(f"Cost of Equity (rₑ) = Risk-Free Rate + Beta × Market Risk Premium")
        print(f"                  = {ry:.4f} + {beta:.2f} × {market_risk_premium:.4f}")
        print(f"                  = {er_eq:.4f}")
        print()
        print(f"Cost of Debt (r_d) = Risk-Free Rate + Credit Spread")
        print(f"                 = {ry:.4f} + {credit_spread:.4f}")
        print(f"                 = {er_de:.4f}")
    
        print("\n--- Capital Structure Calculations ---")
        print(f"Debt to Invested Capital (D/IC) = Total Debt / Invested Capital")
        print(f"                               = {td:.2f} / {tic:.2f}")
        print(f"                               = {td / tic:.4f}" if tic else "                               = N/A")
        print(f"\nEquity to Invested Capital (E/IC) = Total Equity / Invested Capital")
        print(f"                                 = {te:.2f} / {tic:.2f}")
        print(f"                                 = {te / tic:.4f}" if tic else "                                 = N/A")
        print(f"\nDebt to Equity (D/E) = Total Debt / Total Equity")
        print(f"                    = {td:.2f} / {te:.2f}")
        print(f"                    = {td / te:.4f}" if te else "                    = N/A")
    
        di = td / (td + te) if (td + te) else 0
        ei = te / (td + te) if (td + te) else 0
    
        wacc = (ei * er_eq) + (di * er_de * (1 - taxrate))
    
        # ROIC and Growth
        roic = nopat / tic if tic else 0
        change_in_invested_capital = ppe + wcchg
        if change_in_invested_capital <= 0:
            rr = 0
            gr = 0
        else:
            rr = change_in_invested_capital / nopat if nopat else 0
            gr = rr * roic if roic else 0
    
        # Valuations
        val_g = nopat / (wacc - gr) if wacc > gr else 0
        val_ng = nopat / wacc if wacc else 0
    
        # EBIT-based FCF
        ebit_nopat = ebit * (1 - taxrate)
        fcf_ebit = ebit_nopat + damo - ppe - wcchg
    
        # Summary Table
        df_sum = pd.DataFrame({
            'Metric': [
                'EBITDA',
                'EBIT',
                'NOPAT (M)',
                'Capital Expenditure',
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
                ebitda/1e6,
                ebit/1e6,
                nopat/1e6,
                capex/1e6,
                td/1e6,
                te/1e6,
                tic/1e6,
                wacc*100,
                beta,
                roic*100,
                gr*100,
                val_g/1e6,
                val_ng/1e6,
                info.get('marketCap', 0)/1e6
            ]
        })
    
        print("\n--- Financial Summary ---")
        display(df_sum)
    
        # ROIC and Growth Section
        print("\n--- ROIC and Growth Analysis ---")
        print(f"Return on Invested Capital (ROIC): {roic*100:.2f}%")
        print(f"Change in Invested Capital (Net PPE + NWC): ${change_in_invested_capital/1e6:.2f}M")
        print(f"Change in Invested Capital over NOPAT (RR): {rr*100:.2f}%")
        print(f"Growth Rate (g): {gr*100:.2f}%")
    
        # Detailed WACC Section
        market_value_equity = info.get('marketCap', 0) / 1e6
        market_value_debt = td / 1e9
        income_tax_expense = safe_latest(tk_fin, 'Income Tax Expense') / 1e6
        ebt = pretax / 1e6
        effective_tax_rate = income_tax_expense / ebt if ebt else 0
    
        print("\n--- WACC Detailed Breakdown ---")
        print(f"Risk-Free Rate: {ry:.4f}")
        print(f"Beta: {beta:.2f}")
        print(f"Market Risk Premium: {market_risk_premium:.4f}")
        print(f"Cost of Equity: {er_eq:.4f}")
        print(f"Market Value of Equity ($M): {market_value_equity:.2f}")
        print(f"Market Value of Debt ($Bn): {market_value_debt:.2f}")
        print(f"Cost of Debt: {er_de:.4f}")
        print(f"Income Tax Expense ($M): {income_tax_expense:.2f}")
        print(f"Earnings Before Tax (EBT) ($M): {ebt:.2f}")
        print(f"Effective Tax Rate: {taxrate:.4f}")
        print(f"Weight of Debt (Wd): {di:.4f}")
        print(f"Weight of Equity (We): {ei:.4f}")
        print(f"WACC: {wacc:.4f}")
        df_sum['Value'] = df_sum['Value'].replace([np.inf, -np.inf], np.nan).fillna(0).round().astype(int)
        st.table(df_sum)

        # Free Cash Flow by year
        st.subheader("Free Cash Flow by Year")
        fcf_rows = []
        for period in fin.columns:
            ebit = safe_col(fin, 'EBIT', period)
            tax_rate = safe_latest(fin, 'Tax Rate For Calcs')
            nopat = ebit * (1 - taxrate)
            capex = safe_col(cf, 'Capital Expenditure', period)  # Corrected here
            damo = safe_col(fin, 'Reconciled Depreciation', period)
            
            wcchg = safe_col(cf, 'Change In Working Capital', period)

            fcf = nopat + damo - capex - wcchg

            fcf_rows.append({
                'Year': pd.to_datetime(period).year,
                'EBIT (M)': ebit/1e6,
                'NOPAT (M)': nopat/1e6,
                'Depreciation (M)': damo/1e6,
                'Capex (M)': capex/1e6,
                'ΔNWC (M)': wcchg/1e6,
                'Free Cash Flow (M)': fcf/1e6
            })

        df_fcf = pd.DataFrame(fcf_rows).set_index('Year')
        df_fcf = df_fcf.replace([np.inf, -np.inf], np.nan).fillna(0).round().astype(int)
        st.table(df_fcf)

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
        # (1) Define safe_col once, _before_ you start looping
        def safe_col(df, field, col):
            if field in df.index and col in df.columns:
                val = df.at[field, col]
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return 0.0
            return 0.0
        
        st.subheader("Working Capital Metrics (Days) + ΔNWC")
        wc_list = []
        for c in last5:
            inv  = safe_col(bs, 'Inventory', c)
            ar   = safe_col(bs, 'Accounts Receivable', c)
            ap   = safe_col(bs, 'Accounts Payable', c)
            cogs = safe_col(fin, 'Cost Of Revenue', c)
            rev  = safe_col(fin, 'Total Revenue', c)
        
            # now your days metrics — these _are_ inside the loop
            dio = int(round(inv  / cogs * 365)) if cogs > 0 else None
            dso = int(round(ar   / rev  * 365)) if rev  > 0 else None
            dpo = int(round(ap   / cogs * 365)) if cogs > 0 else None
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
        
        # once the loop is done, build your DataFrame as before
        wc_df = pd.DataFrame(wc_list).set_index('Year')
        wc_df['ΔNWC'] = wc_df['NWC'].diff().round(2)
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
