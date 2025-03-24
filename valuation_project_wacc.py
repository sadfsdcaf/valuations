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

    st.subheader("Key Financial Metrics from Last Published Financials")
    annual_financials = stock.financials
    if not annual_financials.empty:
        latest_column = annual_financials.columns[0]
        total_revenue = annual_financials.loc['Total Revenue', latest_column] if 'Total Revenue' in annual_financials.index else 0
        cost_of_revenue = annual_financials.loc['Cost Of Revenue', latest_column] if 'Cost Of Revenue' in annual_financials.index else 0
        depreciation = annual_financials.loc['Depreciation', latest_column] if 'Depreciation' in annual_financials.index else 0
        operating_expense = annual_financials.loc['Total Operating Expenses', latest_column] if 'Total Operating Expenses' in annual_financials.index else 0
        pretax_income = annual_financials.loc['Pretax Income', latest_column] if 'Pretax Income' in annual_financials.index else 0
        tax_provision_reported = annual_financials.loc['Tax Provision', latest_column] if 'Tax Provision' in annual_financials.index else 0
        net_income_to_common = annual_financials.loc['Net Income Common Stockholders', latest_column] if 'Net Income Common Stockholders' in annual_financials.index else 0
        calculated_tax_rate = (tax_provision_reported / pretax_income) if pretax_income != 0 else 0
        gross_profit = total_revenue - cost_of_revenue

        st.write(f"Revenues: ${total_revenue:,.2f}")
        st.write(f"Cost of Revenues: ${cost_of_revenue:,.2f}")
        st.write(f"Gross Profit: ${gross_profit:,.2f}")
        st.write(f"Operating Expense: ${operating_expense:,.2f}")
        st.write(f"Depreciation: ${depreciation:,.2f}")
        st.write(f"Pretax Income: ${pretax_income:,.2f}")
        st.write(f"Tax Provision (Reported): ${tax_provision_reported:,.2f}")
        st.write(f"Calculated Tax Rate (Tax Provision / Pretax Income): {calculated_tax_rate * 100:.2f}%")
        st.write(f"Net Income to Common Stockholders: ${net_income_to_common:,.2f}")

    st.subheader("Annual Financial Statements (Last Published)")
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

