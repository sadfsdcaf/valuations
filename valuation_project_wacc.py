import yfinance as yf
import streamlit as st
import pandas as pd

st.title("Last Published Annual Financial Statements with NOPAT, FCF, and Invested Capital Breakdown")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials`, `balance_sheet`, and `cashflow` attributes and includes a Free Cash Flow (FCF) section with NOPAT and working capital.
""")

def fetch_stock_data(ticker):
    return yf.Ticker(ticker)

def format_millions(value):
    return round(value / 1_000_000, 2) if value else 0

def display_hierarchy(financials, latest_column):
    data = []
    for metric, row in financials.iterrows():
        value = format_millions(row[latest_column])
        data.append({"Metric": metric, "Value (M)": value})
    return pd.DataFrame(data)

def get_10yr_treasury_yield():
    treasury_ticker = yf.Ticker("^TNX")
    history = treasury_ticker.history(period="1mo")
    if not history.empty:
        return history['Close'].iloc[-1] / 100
    return 0

# Main

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)
    market_cap = stock.info.get('marketCap', 0)
    market_cap_millions = format_millions(market_cap)

    annual_financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow

    if not annual_financials.empty:
        latest_column = annual_financials.columns[0]

        # Financial metric retrieval with safety
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

        equity_beta = stock.info.get('beta', 1)
        treasury_yield = get_10yr_treasury_yield()

        asset_beta = equity_beta * (1 / (1 + (1 - calculated_tax_rate) * (total_debt / total_equity))) if total_equity else 0

        expected_return_equity = treasury_yield + equity_beta * 0.05
        expected_return_debt = treasury_yield + 0.01

        d_ic_ratio = (total_debt / total_invested_capital) if total_invested_capital else 0
        e_ic_ratio = (total_equity / total_invested_capital) if total_invested_capital else 0

        wacc = ((e_ic_ratio * expected_return_equity) + (d_ic_ratio * expected_return_debt * (1 - calculated_tax_rate)))

        # Growth calculation
        reinvestment_rate = (net_ppe_purchase_and_sale + change_in_working_capital) / nopat if nopat else 0
        roic = nopat / total_invested_capital if total_invested_capital else 0
        growth_rate = reinvestment_rate * roic

        valuation_growth = nopat / (wacc - growth_rate) if wacc > growth_rate else 0
        valuation_no_growth = nopat / wacc if wacc else 0

        st.subheader("Summary Table")
        summary_table = pd.DataFrame({
            'Metric': ['NOPAT (M)', 'FCF (M)', 'Total Debt (M)', 'Total Equity (M)', 'WACC', 'ROIC', 'Growth Rate', 'Valuation (Growth)', 'Valuation (No Growth)', 'Market Cap (M)'],
            'Value': [nopat, fcf, total_debt, total_equity, wacc, roic, growth_rate, valuation_growth, valuation_no_growth, market_cap_millions]
        })

        st.table(summary_table)

        st.subheader("Annual Financial Statements (Hierarchical View)")
        st.table(display_hierarchy(annual_financials, latest_column))

        st.subheader("Balance Sheet (Last Published)")
        st.write(balance_sheet)

        st.subheader("Cash Flow Statement (Last Published)")
        st.write(cashflow)
