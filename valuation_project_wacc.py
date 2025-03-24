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

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)

    st.subheader("Key Financial Metrics from Last Published Financials")
    annual_financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow

    if not annual_financials.empty and not balance_sheet.empty and not cashflow.empty:
        latest_column = annual_financials.columns[0]

        total_revenue = format_millions(annual_financials.loc['Total Revenue', latest_column]) if 'Total Revenue' in annual_financials.index else 0
        cost_of_revenue = format_millions(annual_financials.loc['Cost Of Revenue', latest_column]) if 'Cost Of Revenue' in annual_financials.index else 0
        depreciation = format_millions(annual_financials.loc['Reconciled Depreciation', latest_column]) if 'Reconciled Depreciation' in annual_financials.index else 0
        pretax_income = format_millions(annual_financials.loc['Pretax Income', latest_column]) if 'Pretax Income' in annual_financials.index else 0
        tax_provision_reported = format_millions(annual_financials.loc['Tax Provision', latest_column]) if 'Tax Provision' in annual_financials.index else 0
        net_income_to_common = format_millions(annual_financials.loc['Net Income Common Stockholders', latest_column]) if 'Net Income Common Stockholders' in annual_financials.index else 0
        calculated_tax_rate = (tax_provision_reported / pretax_income) if pretax_income != 0 else 0
        nopat = pretax_income * (1 - calculated_tax_rate)
        gross_profit = total_revenue - cost_of_revenue

        depreciation_amortization_depletion = format_millions(cashflow.loc['Depreciation Amortization Depletion', latest_column]) if 'Depreciation Amortization Depletion' in cashflow.index else 0
        net_ppe_purchase_and_sale = abs(format_millions(cashflow.loc['Net PPE Purchase And Sale', latest_column])) if 'Net PPE Purchase And Sale' in cashflow.index else 0
        change_in_working_capital = format_millions(cashflow.loc['Change In Working Capital', latest_column]) if 'Change In Working Capital' in cashflow.index else 0

        accounts_receivable = format_millions(cashflow.loc['Change In Receivables', latest_column]) if 'Change In Receivables' in cashflow.index else 0
        inventories = format_millions(cashflow.loc['Change In Inventory', latest_column]) if 'Change In Inventory' in cashflow.index else 0
        other_assets = format_millions(cashflow.loc['Change In Other Current Assets', latest_column]) if 'Change In Other Current Assets' in cashflow.index else 0
        accounts_payable = format_millions(cashflow.loc['Change In Payable', latest_column]) if 'Change In Payable' in cashflow.index else 0
        other_liabilities = format_millions(cashflow.loc['Change In Other Current Liabilities', latest_column]) if 'Change In Other Current Liabilities' in cashflow.index else 0

        fcf = nopat + depreciation_amortization_depletion - net_ppe_purchase_and_sale - change_in_working_capital

        income_table = pd.DataFrame({
            'Metric': ['Revenues (M)', 'Cost of Revenues (M)', 'Gross Profit (M)', 'Net Income to Common (M)', 'Depreciation (M)', 'EBIT (M)'],
            'Value': [total_revenue, cost_of_revenue, gross_profit, net_income_to_common, depreciation, pretax_income]
        })

        st.table(income_table)

        tax_table = pd.DataFrame({
            'Metric': ['Tax Provision (M)', 'Calculated Tax Rate (%)'],
            'Value': [tax_provision_reported, round(calculated_tax_rate * 100, 2)]
        })

        st.subheader("Tax Section")
        st.table(tax_table)

        fcf_table = pd.DataFrame({
            'Metric': ['NOPAT (M)', 'Depreciation Amortization Depletion (M)', 'Net PPE Purchase And Sale (M)', 'Change in Net Working Capital (M)', 'Free Cash Flow (M)'],
            'Value': [nopat, depreciation_amortization_depletion, net_ppe_purchase_and_sale, change_in_working_capital, fcf]
        })

        st.subheader("Free Cash Flow (FCF) Calculation")
        st.table(fcf_table)

        wc_breakdown_table = pd.DataFrame({
            'Metric': ['Change in Receivables (M)', 'Change in Inventory (M)', 'Change in Other Current Assets (M)', 'Change in Payables (M)', 'Change in Other Current Liabilities (M)'],
            'Value': [accounts_receivable, inventories, other_assets, accounts_payable, other_liabilities]
        })

        st.subheader("Breakdown of Changes in Working Capital")
        st.table(wc_breakdown_table)

        total_debt = format_millions(balance_sheet.loc['Total Debt', latest_column]) if 'Total Debt' in balance_sheet.index else 0
        total_equity = format_millions(balance_sheet.loc['Total Equity Gross Minority Interest', latest_column]) if 'Total Equity Gross Minority Interest' in balance_sheet.index else 0

        invested_capital_table = pd.DataFrame({
            'Metric': ['Total Debt (M)', 'Total Equity (M)', 'Total Invested Capital (M)'],
            'Value': [total_debt, total_equity, total_debt + total_equity]
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
""")
