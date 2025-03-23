import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

def calculate_wacc(debt, equity, cost_of_debt, cost_of_equity, tax_rate):
    total = debt + equity
    wacc = (equity / total) * cost_of_equity + (debt / total) * cost_of_debt * (1 - tax_rate)
    return wacc

def present_value_cashflows(cashflows, discount_rate):
    return sum(cf / (1 + discount_rate) ** i for i, cf in enumerate(cashflows, start=1))

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5y")
    return stock, hist

st.title("Valuation Calculator Recreated from Debt, Equity, NOA, and PVGO")

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock, hist = fetch_stock_data(ticker)
    st.write(f"Company Info: {stock.info['longName']}")

    if 'financials' in stock.info:
        st.write(f"Financial Statement Date: {stock.info.get('financialCurrency', 'N/A')} (Check most recent 10-K/10-Q for accuracy)")
    else:
        st.write("Financial statement date information not available via yfinance. Please refer to the company’s latest reports.")

    st.subheader("Assumptions")
    debt = st.number_input("Current Total Debt ($M)", min_value=0.0, value=10000.0)
    equity = st.number_input("Current Total Equity / Book Value ($M)", min_value=0.0, value=200000.0)
    cash_and_investments = st.number_input("Cash & Short Term Investments ($M)", min_value=0.0, value=5000.0)
    noa = st.number_input("Net Operating Assets (NOA) ($M)", min_value=0.0, value=250000.0)
    pvgo = st.number_input("Present Value of Growth Opportunities (PVGO) ($M)", min_value=0.0, value=50000.0)

    cost_of_debt = st.number_input("Cost of Debt (%)", min_value=0.0, max_value=100.0, value=3.0) / 100
    cost_of_equity = st.number_input("Cost of Equity (%)", min_value=0.0, max_value=100.0, value=8.0) / 100
    tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=21.0) / 100

    wacc = calculate_wacc(debt, equity, cost_of_debt, cost_of_equity, tax_rate)
    st.write(f"Calculated WACC: {wacc * 100:.2f}%")

    st.subheader("Finance View Valuation")
    total_assets = noa + pvgo

    st.write(f"Net Operating Assets (NOA): ${noa:,.2f}M")
    st.write(f"Present Value of Growth Opportunities (PVGO): ${pvgo:,.2f}M")
    st.write(f"Total Reconstructed Assets (NOA + PVGO): ${total_assets:,.2f}M")
    st.write(f"Current Total Debt: ${debt:,.2f}M")
    st.write(f"Current Total Equity: ${equity:,.2f}M")

    enterprise_value_reconstructed = debt + equity
    st.write(f"Reconstructed Enterprise Value (Debt + Equity): ${enterprise_value_reconstructed:,.2f}M")

    current_market_cap = stock.info.get("marketCap", 0) / 1_000_000
    enterprise_value_market = current_market_cap + debt - cash_and_investments

    st.write(f"Market Capitalization: ${current_market_cap:,.2f}M")
    st.write(f"Market Enterprise Value (Market Cap + Debt - Cash): ${enterprise_value_market:,.2f}M")

    valuation_diff = enterprise_value_market - enterprise_value_reconstructed
    st.write(f"Difference (Market Enterprise Value - Reconstructed Enterprise Value): ${valuation_diff:,.2f}M")

    st.subheader("Historical Price Data")
    st.line_chart(hist['Close'])
