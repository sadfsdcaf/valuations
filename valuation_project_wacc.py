import yfinance as yf
import streamlit as st

st.title("Last Published Annual Financial Statements with NOPAT and FCF Calculation")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials`, `balance_sheet`, and `cashflow` attributes and includes a Free Cash Flow (FCF) section with NOPAT and working capital.

**Reference metadata fields, balance sheet fields, income statement fields, and cash flow fields have been noted for this conversation.**
""")

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)

    st.subheader("Key Financial Metrics from Last Published Financials")
    annual_financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow

    if not annual_financials.empty and not balance_sheet.empty and not cashflow.empty:
        latest_column = annual_financials.columns[0]

        total_revenue = annual_financials.loc['Total Revenue', latest_column] if 'Total Revenue' in annual_financials.index else 0
        cost_of_revenue = annual_financials.loc['Cost Of Revenue', latest_column] if 'Cost Of Revenue' in annual_financials.index else 0
        depreciation = annual_financials.loc['Reconciled Depreciation', latest_column] if 'Reconciled Depreciation' in annual_financials.index else 0
        pretax_income = annual_financials.loc['Pretax Income', latest_column] if 'Pretax Income' in annual_financials.index else 0
        tax_provision_reported = annual_financials.loc['Tax Provision', latest_column] if 'Tax Provision' in annual_financials.index else 0
        net_income_to_common = annual_financials.loc['Net Income Common Stockholders', latest_column] if 'Net Income Common Stockholders' in annual_financials.index else 0
        calculated_tax_rate = (tax_provision_reported / pretax_income) if pretax_income != 0 else 0
        nopat = pretax_income * (1 - calculated_tax_rate)
        gross_profit = total_revenue - cost_of_revenue

        depreciation_amortization_depletion = cashflow.loc['Depreciation Amortization Depletion', latest_column] if 'Depreciation Amortization Depletion' in cashflow.index else 0
        net_ppe_purchase_and_sale = cashflow.loc['Net PPE Purchase And Sale', latest_column] if 'Net PPE Purchase And Sale' in cashflow.index else 0
        change_in_working_capital = cashflow.loc['Change In Working Capital', latest_column] if 'Change In Working Capital' in cashflow.index else 0

        fcf = nopat + depreciation_amortization_depletion - net_ppe_purchase_and_sale - change_in_working_capital

        st.write(f"Revenues: ${total_revenue:,.2f}")
        st.write(f"Cost of Revenues: ${cost_of_revenue:,.2f}")
        st.write(f"Gross Profit: ${gross_profit:,.2f}")
        st.write(f"Net Income to Common Stockholders: ${net_income_to_common:,.2f}")
        st.write(f"Depreciation (Reconciled): ${depreciation:,.2f}")
        st.write(f"EBIT: ${pretax_income:,.2f}")

        st.write("### Tax Section")
        st.write(f"Tax Provision (Reported): ${tax_provision_reported:,.2f}")
        st.write(f"Calculated Tax Rate (Tax Provision / Pretax Income): {calculated_tax_rate * 100:.2f}%")

        st.subheader("Free Cash Flow (FCF) Calculation")
        st.write(f"NOPAT (Pretax Income * (1 - Tax Rate)): ${nopat:,.2f}")
        st.write(f"Depreciation Amortization Depletion: ${depreciation_amortization_depletion:,.2f}")
        st.write(f"Net PPE Purchase And Sale: ${net_ppe_purchase_and_sale:,.2f}")
        st.write(f"Change in Net Working Capital (from Cash Flow Statement): ${change_in_working_capital:,.2f}")
        st.write(f"Free Cash Flow (FCF = NOPAT + Depreciation Amortization Depletion - Net PPE Purchase And Sale - Change in Working Capital): ${fcf:,.2f}")

    st.subheader("Annual Financial Statements (Last Published)")
    st.write(annual_financials)

    st.subheader("Balance Sheet (Last Published)")
    st.write(balance_sheet)

    st.subheader("Cash Flow Statement (Last Published) - All Available Fields")
    st.write(cashflow)

    st.markdown("""---
These statements are sourced directly from the most recently reported financial filings.
""")
