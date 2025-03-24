import yfinance as yf
import streamlit as st
import pandas as pd

st.title("Last Published Annual Financial Statements with NOPAT, FCF, and Invested Capital Breakdown")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials`, `balance_sheet`, and `cashflow` attributes and includes a Free Cash Flow (FCF) section with NOPAT and working capital.

**Reference metadata fields, balance sheet fields, income statement fields, and cash flow fields have been noted for this conversation.**
""")

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock

def format_millions(value):
    return round(value / 1_000_000, 2)

def get_10yr_treasury_yield():
    treasury_ticker = yf.Ticker("^TNX")  # ^TNX represents the CBOE 10-Year Treasury Note Yield Index
    history = treasury_ticker.history(period="1y")
    latest_yield = history['Close'].iloc[-1] / 100  # Convert from percent to decimal
    return latest_yield

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)

    st.subheader("Key Financial Metrics from Last Published Financials")
    annual_financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow

    if not annual_financials.empty and not balance_sheet.empty and not cashflow.empty:
        latest_column = annual_financials.columns[0]

        long_term_debt = format_millions(balance_sheet.loc['Long Term Debt', latest_column]) if 'Long Term Debt' in balance_sheet.index else 0
        current_debt = format_millions(balance_sheet.loc['Current Debt', latest_column]) if 'Current Debt' in balance_sheet.index else 0
        total_debt = long_term_debt + current_debt

        total_equity = format_millions(balance_sheet.loc['Total Equity Gross Minority Interest', latest_column]) if 'Total Equity Gross Minority Interest' in balance_sheet.index else 0
        total_invested_capital = total_debt + total_equity
        d_ic_ratio = (total_debt / total_invested_capital) * 100 if total_invested_capital != 0 else 0
        e_ic_ratio = (total_equity / total_invested_capital) * 100 if total_invested_capital != 0 else 0

        invested_capital_table = pd.DataFrame({
            'Metric': [
                'Total Debt (M)',
                '   - Long Term Debt (M)',
                '   - Current Debt (M)',
                'Total Equity (M)',
                'Total Invested Capital (M)',
                'Debt / Invested Capital (%)',
                'Equity / Invested Capital (%)'
            ],
            'Value': [
                total_debt,
                long_term_debt,
                current_debt,
                total_equity,
                total_invested_capital,
                d_ic_ratio,
                e_ic_ratio
            ]
        })

        st.subheader("Invested Capital Breakdown (Debt and Equity)")
        st.table(invested_capital_table)

    st.subheader("Annual Financial Statements (Last Published)")
    st.write(annual_financials)

    st.subheader("Balance Sheet (Last Published)")
    st.write(balance_sheet)

    st.subheader("Cash Flow Statement (Last Published) - All Available Fields")
    st.write(cashflow)

    st.markdown("""---
These statements are sourced directly from the most recently reported financial filings.
"")
