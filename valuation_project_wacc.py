import yfinance as yf
import streamlit as st

st.title("Last Published Financial Statements Viewer")

st.markdown("""
This tool displays the last published annual and quarterly financial statements using yFinance's `financials` and `quarterly_financials` attributes.
""")

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)

    st.subheader("Annual Financial Statements (Last Published)")
    annual_financials = stock.financials
    st.write(annual_financials)

    st.subheader("Quarterly Financial Statements (Last Published)")
    quarterly_financials = stock.quarterly_financials
    st.write(quarterly_financials)

    st.markdown("""---
These statements are sourced directly from the most recently reported financial filings.
""")
