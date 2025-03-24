import yfinance as yf
import streamlit as st
import pandas as pd

st.title("Last Published Annual Financial Statements with NOPAT, FCF, and Invested Capital Breakdown")

st.markdown("""
This tool displays the last published annual financial statements using yFinance's `financials`, `balance_sheet`, and `cashflow` attributes and includes a Free Cash Flow (FCF) section with NOPAT and working capital.
""")

def fetch_stock_data(ticker):
    return yf.Ticker(ticker)

def format_millions(value):
    return round(value / 1_000_000, 2) if value else 0

def display_gaap_income_statement_as_table(financials, latest_column):
    gaap_order = [
        {"parent": "Total Revenue", "children": ["Operating Revenue"]},
        {"parent": "Cost Of Revenue"},
        {"parent": "Gross Profit"},
        {"parent": "Operating Expense", "children": ["Selling General and Administrative", "Research & Development"]},
        {"parent": "Operating Income"},
        {"parent": "Net Non Operating Interest Income Expense", "children": ["Interest Income Non Operating", "Interest Expense Non Operating"]},
        {"parent": "Other Income Expense", "children": ["Other Non Operating Income (Expense)"]},
        {"parent": "Pretax Income"},
        {"parent": "Tax Provision"},
        {"parent": "Net Income Common Stockholders", "children": ["Net Income", "Net Income Including Noncontrolling Interests", "Net Income Continuous Operations"]},
        {"parent": "Diluted NI Available to Common Stockholders"},
        {"parent": "Basic EPS"},
        {"parent": "Diluted EPS"},
        {"parent": "Basic Average Shares"},
        {"parent": "Diluted Average Shares"},
        {"parent": "Total Operating Income as Reported"},
        {"parent": "Total Expenses"},
        {"parent": "Net Income from Continuing & Discontinued Operation"},
        {"parent": "Normalized Income"},
        {"parent": "Interest Income"},
        {"parent": "Interest Expense"},
        {"parent": "Net Interest Income"},
        {"parent": "EBIT"},
        {"parent": "EBITDA"},
        {"parent": "Reconciled Cost of Revenue"},
        {"parent": "Reconciled Depreciation"},
        {"parent": "Net Income from Continuing Operation Net Minority Interest"},
        {"parent": "Normalized EBITDA"},
        {"parent": "Tax Rate for Calcs"}
    ]

    data = []
    for item in gaap_order:
        parent = item["parent"]
        if parent in financials.index:
            val = format_millions(financials.loc[parent, latest_column])
            data.append({"Metric": parent, "Value (M)": val})

            if "children" in item:
                for child in item["children"]:
                    if child in financials.index:
                        c_val = format_millions(financials.loc[child, latest_column])
                        indented_child = f"   ↳ {child}"
                        data.append({"Metric": indented_child, "Value (M)": c_val})

    df = pd.DataFrame(data)
    st.table(df)

def get_10yr_treasury_yield():
    treasury_ticker = yf.Ticker("^TNX")
    history = treasury_ticker.history(period="1mo")
    if not history.empty:
        return history['Close'].iloc[-1] / 100
    return 0

# Main

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)
    market_cap = stock.info.get('marketCap', 0)
    market_cap_millions = format_millions(market_cap)

    annual_financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow

    if not annual_financials.empty:
        latest_column = annual_financials.columns[0]

        st.subheader("Annual Financial Statements (GAAP Structured Table View with Indentation)")
        display_gaap_income_statement_as_table(annual_financials, latest_column)

        st.subheader("Balance Sheet (Last Published)")
        st.write(balance_sheet)

        st.subheader("Cash Flow Statement (Last Published)")
        st.write(cashflow)
