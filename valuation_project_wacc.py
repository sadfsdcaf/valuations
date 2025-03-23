import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5y")
    return stock, hist

st.title("Automated Valuation Based on yFinance Data")

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock, hist = fetch_stock_data(ticker)
    st.write(f"Company Info: {stock.info['longName']}")

    market_cap = stock.info.get("marketCap", 0) / 1_000_000
    total_debt = stock.info.get("totalDebt", 0) / 1_000_000
    cash_and_investments = stock.info.get("totalCash", 0) / 1_000_000
    ebit = stock.info.get("ebit", 0) / 1_000_000
    depreciation = stock.info.get("depreciation", 0) / 1_000_000
    capex = stock.info.get("capitalExpenditures", 0) / 1_000_000
    total_revenue = stock.info.get("totalRevenue", 0) / 1_000_000
    change_in_nwc = 0  # Placeholder — ideally sourced from financial statements or calculated from balance sheet changes.
    tax_rate = 0.21  # Default tax rate; could be estimated or sourced.

    enterprise_value = market_cap + total_debt - cash_and_investments
    st.subheader("Valuation Summary from yFinance")
    st.write(f"Market Capitalization: ${market_cap:,.2f}M")
    st.write(f"Total Debt: ${total_debt:,.2f}M")
    st.write(f"Cash & Short-Term Investments: ${cash_and_investments:,.2f}M")
    st.write(f"Enterprise Value (Market Cap + Debt - Cash): ${enterprise_value:,.2f}M")
    st.write(f"Total Revenue: ${total_revenue:,.2f}M")

    st.subheader("Free Cash Flow (FCF) Calculation")
    nopat = ebit * (1 - tax_rate)
    fcf = nopat + depreciation - capex - change_in_nwc

    st.write(f"EBIT: ${ebit:,.2f}M")
    st.write(f"NOPAT (EBIT * (1 - T)): ${nopat:,.2f}M")
    st.write(f"Depreciation: ${depreciation:,.2f}M")
    st.write(f"Capital Expenditures: ${capex:,.2f}M")
    st.write(f"ΔNWC (Placeholder): ${change_in_nwc:,.2f}M")
    st.write(f"Calculated Free Cash Flow (FCF): ${fcf:,.2f}M")

    st.subheader("Historical Price Data")
    st.line_chart(hist['Close'])
