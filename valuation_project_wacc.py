import yfinance as yf
import streamlit as st

st.title("All Available yFinance Fields Display")

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock

ticker = st.text_input("Enter Ticker:", "AAPL")

if ticker:
    stock = fetch_stock_data(ticker)
    info = stock.info

    fields = [
        "address1", "algorithm", "annualHoldingsTurnover", "annualReportExpenseRatio", "ask", "askSize",
        "averageDailyVolume10Day", "averageVolume", "averageVolume10days", "beta", "bid", "bidSize", "bookValue",
        "category", "circulatingSupply", "city", "companyOfficers", "compensationAsOfEpochDate", "country",
        "currency", "currentPrice", "currentRatio", "dateShortInterest", "dayHigh", "dayLow", "debtToEquity",
        "dividendRate", "dividendYield", "earningsGrowth", "earningsQuarterlyGrowth", "ebitda", "ebitdaMargins",
        "enterpriseToEbitda", "enterpriseToRevenue", "enterpriseValue", "exDividendDate", "exchange",
        "exchangeTimezoneName", "exchangeTimezoneShortName", "fiftyDayAverage", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
        "financialCurrency", "floatShares", "forwardEps", "forwardPE", "freeCashflow", "fundFamily",
        "fundInceptionDate", "gmtOffSetMilliseconds", "grossMargins", "grossProfits", "heldPercentInsiders",
        "heldPercentInstitutions", "industry", "isEsgPopulated", "lastCapGain", "lastDividendDate", "lastDividendValue",
        "lastFiscalYearEnd", "lastSplitDate", "lastSplitFactor", "longBusinessSummary", "longName", "market",
        "marketCap", "maxAge", "maxSupply", "morningStarOverallRating", "morningStarRiskRating", "netIncomeToCommon",
        "nextFiscalYearEnd", "numberOfAnalystOpinions", "open", "openInterest", "operatingCashflow", "operatingMargins",
        "payoutRatio", "pegRatio", "phone", "previousClose", "priceHint", "priceToBook", "priceToSalesTrailing12Months",
        "profitMargins", "quickRatio", "quoteType", "recommendationKey", "recommendationMean", "regularMarketDayHigh",
        "regularMarketDayLow", "regularMarketOpen", "regularMarketPreviousClose", "regularMarketPrice",
        "regularMarketVolume", "revenueGrowth", "revenuePerShare", "returnOnAssets", "returnOnEquity", "sector",
        "sharesOutstanding", "sharesPercentSharesOut", "sharesShort", "sharesShortPreviousMonthDate", "sharesShortPriorMonth",
        "shortName", "shortPercentOfFloat", "shortRatio", "startDate", "state", "symbol", "targetHighPrice",
        "targetLowPrice", "targetMeanPrice", "targetMedianPrice", "threeYearAverageReturn", "totalAssets", "totalCash",
        "totalCashPerShare", "totalDebt", "totalRevenue", "tradeable", "trailingAnnualDividendRate",
        "trailingAnnualDividendYield", "trailingEps", "trailingPE", "twoHundredDayAverage", "volume", "website", "yield",
        "zip"
    ]

    st.subheader("Key yFinance Fields")
    for field in fields:
        value = info.get(field, "Not Available")
        st.write(f"{field}: {value}")
