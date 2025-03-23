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

st.title("Valuation Calculator with WACC and Cashflow Assumptions")

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock, hist = fetch_stock_data(ticker)
    st.write(f"Company Info: {stock.info['longName']}")

    st.subheader("Assumptions")
    debt = st.number_input("Total Debt ($M)", min_value=0.0, value=10000.0)
    equity = st.number_input("Total Equity ($M)", min_value=0.0, value=200000.0)
    cost_of_debt = st.number_input("Cost of Debt (%)", min_value=0.0, max_value=100.0, value=3.0) / 100
    cost_of_equity = st.number_input("Cost of Equity (%)", min_value=0.0, max_value=100.0, value=8.0) / 100
    tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=21.0) / 100

    wacc = calculate_wacc(debt, equity, cost_of_debt, cost_of_equity, tax_rate)
    st.write(f"Calculated WACC: {wacc * 100:.2f}%")

    st.subheader("Cashflow Projections")
    cashflows = []
    for year in range(1, 6):
        cf = st.number_input(f"Cashflow for Year {year} ($M)", value=5000.0 * (1 + 0.05)**(year - 1))
        cashflows.append(cf)

    present_value = present_value_cashflows(cashflows, wacc)
    st.write(f"Present Value of Cashflows: ${present_value:,.2f}M")

    st.subheader("Market Valuation vs. Cashflow Valuation")
    current_market_cap = stock.info.get("marketCap", 0) / 1_000_000  # Convert to $M
    st.write(f"Current Market Valuation: ${current_market_cap:,.2f}M")

    valuation_difference = current_market_cap - present_value
    st.write(f"Difference (Market Valuation - Cashflow Valuation): ${valuation_difference:,.2f}M")

    st.subheader("Historical Price Data")
    st.line_chart(hist['Close'])
