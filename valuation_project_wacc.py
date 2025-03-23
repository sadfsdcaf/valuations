import yfinance as yf
import streamlit as st

st.title("Last Published Annual Financial Statements with NOPAT Calculation")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials` attribute and calculates NOPAT in the order: EBIT → Tax Rate → NOPAT.
""")

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)

    st.subheader("Key Financial Metrics")
    total_revenue = stock.info.get("totalRevenue", 0)
    cost_of_revenue = stock.info.get("costOfRevenue", 0)
    depreciation = stock.info.get("depreciation", 0)
    st.write(f"Revenues: ${total_revenue:,.2f}")
    st.write(f"Cost of Revenues: ${cost_of_revenue:,.2f}")
    st.write(f"Depreciation: ${depreciation:,.2f}")

    st.subheader("Annual Financial Statements (Last Published)")
    annual_financials = stock.financials
    st.write(annual_financials)

    st.subheader("NOPAT Calculation")
    ebit = stock.info.get("ebit", 0)
    tax_provision = stock.info.get("incomeTaxExpense", 0)
    if ebit > 0:
        tax_rate = tax_provision / ebit
        nopat = ebit * (1 - tax_rate)
    else:
        tax_rate = 0.21
        nopat = ebit * (1 - tax_rate)

    st.write(f"EBIT: ${ebit:,.2f}")
    st.write(f"Calculated Tax Rate (Tax Provision / EBIT): {tax_rate * 100:.2f}%")
    st.write(f"NOPAT (EBIT * (1 - Tax Rate)): ${nopat:,.2f}")

    st.markdown("""---
These statements are sourced directly from the most recently reported financial filings.
""")
