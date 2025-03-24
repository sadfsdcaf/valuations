import yfinance as yf
import streamlit as st

st.title("Last Published Annual Financial Statements with NOPAT and FCF Calculation")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials` and `balance_sheet` attributes and includes a Free Cash Flow (FCF) section with NOPAT and working capital.
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

    if not annual_financials.empty and not balance_sheet.empty:
        latest_column = annual_financials.columns[0]
        previous_column = annual_financials.columns[1] if len(annual_financials.columns) > 1 else latest_column

        total_revenue = annual_financials.loc['Total Revenue', latest_column] if 'Total Revenue' in annual_financials.index else 0
        cost_of_revenue = annual_financials.loc['Cost Of Revenue', latest_column] if 'Cost Of Revenue' in annual_financials.index else 0
        depreciation = annual_financials.loc['Reconciled Depreciation', latest_column] if 'Reconciled Depreciation' in annual_financials.index else 0
        pretax_income = annual_financials.loc['Pretax Income', latest_column] if 'Pretax Income' in annual_financials.index else 0
        tax_provision_reported = annual_financials.loc['Tax Provision', latest_column] if 'Tax Provision' in annual_financials.index else 0
        net_income_to_common = annual_financials.loc['Net Income Common Stockholders', latest_column] if 'Net Income Common Stockholders' in annual_financials.index else 0
        calculated_tax_rate = (tax_provision_reported / pretax_income) if pretax_income != 0 else 0
        nopat = pretax_income * (1 - calculated_tax_rate)
        gross_profit = total_revenue - cost_of_revenue

        current_assets_latest = balance_sheet.loc['Current Assets', latest_column] if 'Current Assets' in balance_sheet.index else 0
        current_liabilities_latest = balance_sheet.loc['Current Liabilities', latest_column] if 'Current Liabilities' in balance_sheet.index else 0
        working_capital_latest = current_assets_latest - current_liabilities_latest

        current_assets_previous = balance_sheet.loc['Current Assets', previous_column] if 'Current Assets' in balance_sheet.index else 0
        current_liabilities_previous = balance_sheet.loc['Current Liabilities', previous_column] if 'Current Liabilities' in balance_sheet.index else 0
        working_capital_previous = current_assets_previous - current_liabilities_previous

        change_in_working_capital = working_capital_latest - working_capital_previous

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
        st.write(f"Depreciation (for FCF, using Reconciled Depreciation): ${depreciation:,.2f}")
        st.write(f"Change in Net Working Capital: ${change_in_working_capital:,.2f}")

    st.subheader("Annual Financial Statements (Last Published)")
    st.write(annual_financials)

    st.subheader("Balance Sheet (Last Published)")
    st.write(balance_sheet)

    st.markdown("""---
These statements are sourced directly from the most recently reported financial filings.
""")
