import streamlit as st
from datetime import date
from thetadata import ThetaClient, OptionReqType, OptionRight, DateRange, SecType, DataType, NoData
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go  # For scatter and candlestick charts

# Initialize the ThetaClient (assuming it doesn't require authentication for simplicity)
client = ThetaClient()

# Function to handle button actions for chart type
def set_chart_type(chart_type):
    st.session_state.chart_data_type = chart_type

# Check if the chart_data_type key exists in session_state, if not, initialize it
if 'chart_data_type' not in st.session_state:
    st.session_state['chart_data_type'] = 'Price'

# Sidebar: Symbol Selection
with client.connect():
    symbols = client.get_roots(SecType.OPTION)
symbol = st.sidebar.selectbox("Select Symbol", symbols)

# Sidebar: Chart Type Selection
chart_type = st.sidebar.selectbox("Select Chart Type", ["Line", "Scatter", "Candlestick"])

# Sidebar: Expiration Date Selection based on selected Symbol
with client.connect():
    expirations = client.get_expirations(symbol).sort_values(ascending=False)
expiration = st.sidebar.selectbox("Select Expiration Date", expirations)

# Sidebar: Strike Price Selection based on selected Symbol and Expiration Date
with client.connect():
    strikes = client.get_strikes(symbol, expiration)
strike = st.sidebar.selectbox("Select Strike Price", strikes)

# Sidebar: Option to add more exercise date data
add_more_data = st.sidebar.radio("Add More Exercise Date Data?", ["No", "Yes"])

# Initialize variable for secondary exercise date selection
secondary_expiration = None
if add_more_data == "Yes":
    secondary_expiration = st.sidebar.selectbox("Select Additional Exercise Date", expirations, key='secondary_expiration')

# Sidebar: Date Range Selection for Historical Data
start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())

# Sidebar: Display Mode Selection for Option Data
display_mode = st.sidebar.radio("Display Mode", ['Chart', 'Table'])

# Fetch Historical Option Data for primary expiration
try:
    with client.connect():
        data_details = client.get_hist_option(
            req=OptionReqType.EOD,
            root=symbol,
            exp=expiration,
            strike=strike,
            right=OptionRight.CALL,
            date_range=DateRange(start_date, end_date)
        )
except NoData:
    st.write("No data available for the selected options.")
    data_details = None
    expiration = None


if expiration is not None:
    data_details['Expiration'] = pd.to_datetime(expiration)
    data_details['Expiration'] = data_details['Expiration'].dt.strftime('%Y-%m-%d')  # Formatting the expiration date

# Fetch for secondary expiration if selected
secondary_data_details = None
if secondary_expiration:
    try:
        with client.connect():
            secondary_data_details = client.get_hist_option(
                req=OptionReqType.EOD,
                root=symbol,
                exp=secondary_expiration,
                strike=strike,
                right=OptionRight.CALL,
                date_range=DateRange(start_date, end_date)
            )
    except NoData:
        st.write("No data available for the selected options.")
        secondary_data_details = None
        secondary_expiration = None

if secondary_expiration is not None:
    secondary_data_details['Expiration'] = pd.to_datetime(secondary_expiration)
    secondary_data_details['Expiration'] = secondary_data_details['Expiration'].dt.strftime('%Y-%m-%d')  # Formatting the expiration date

# Download stock quote data
stock_quote = yf.download(symbol, start=start_date, end=end_date)
stock_quote.reset_index(inplace=True)

ticker = yf.Ticker(symbol)
info = ticker.info
stock_name = info.get("longName", "")

# Main window: Show the symbol name and latest price
if not stock_quote.empty:
    latest_price = stock_quote.iloc[-1]['Close']
else:
    latest_price = 0  # Fallback if stock_quote is empty

st.write(f"Symbol: {symbol} - {stock_name} - Latest Price: {latest_price:.2f}")

# Display the stock price chart based on selected chart type
if chart_type == "Line":
    st.line_chart(stock_quote.set_index('Date')['Close'])
elif chart_type == "Scatter":
    fig_scatter = go.Figure(data=[go.Scatter(x=stock_quote['Date'], y=stock_quote['Close'], mode='markers')])
    st.plotly_chart(fig_scatter)
elif chart_type == "Candlestick":
    fig_candlestick = go.Figure(data=[go.Candlestick(x=stock_quote['Date'],
                                                     open=stock_quote['Open'], high=stock_quote['High'],
                                                     low=stock_quote['Low'], close=stock_quote['Close'])])
    fig_candlestick.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_candlestick)

# Combine data_details and secondary_data_details if both are available
combined_data = pd.DataFrame()
if data_details is not None and not data_details.empty:
    combined_data = pd.concat([data_details, secondary_data_details]) if secondary_data_details is not None else data_details

# Display option data based on selected display mode
if not combined_data.empty:
    combined_data['Date'] = pd.to_datetime(combined_data[DataType.DATE])  # Ensuring 'Date' is in datetime format
    if display_mode == 'Chart':
        # Pivot the combined data for charting
        data_type = DataType.CLOSE if st.session_state.chart_data_type == 'Price' else DataType.VOLUME
        chart_data = combined_data.pivot_table(index='Date', columns='Expiration', values=data_type)
        st.write(f"Option {st.session_state.chart_data_type} Chart")
        st.line_chart(chart_data)
    elif display_mode == 'Table':
        # Show data in a table format
        st.write("Option Data Table")
        st.dataframe(combined_data)
