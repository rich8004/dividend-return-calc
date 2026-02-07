import streamlit as st
import yfinance as yf
import pandas as pd
from pandas.tseries.offsets import BDay
import datetime

# Page Configuration
st.set_page_config(page_title="Dividend Total Return Calculator", layout="wide")
st.title("📈 Dividend Total Return & DRIP Simulator")
st.markdown("This app simulates a DRIP strategy, reinvesting dividends at **noon ET** on the first trading day after payment.")

# Sidebar Inputs
st.sidebar.header("Investment Parameters")
ticker_symbol = st.sidebar.text_input("Trading Symbol", value="SCHD").upper()
start_date = st.sidebar.date_input("Initial Purchase Date", value=datetime.date(2020, 1, 1))
end_date = st.sidebar.date_input("Evaluation End Date", value=datetime.date.today())
initial_shares = st.sidebar.number_input("Initial Share Quantity", value=100.0, step=1.0)
initial_price = st.sidebar.number_input("Initial Purchase Price ($)", value=0.0, help="If 0, will use market open on start date.")

if st.sidebar.button("Calculate Total Return"):
    with st.spinner('Fetching market data...'):
        try:
            # 1. Fetch Ticker Data
            ticker = yf.Ticker(ticker_symbol)
            hist_daily = ticker.history(start=start_date, end=end_date, actions=True)
            
            if hist_daily.empty:
                st.error("No data found for this ticker and date range.")
            else:
                # Resolve Initial Price if set to 0
                if initial_price == 0:
                    initial_price = hist_daily.iloc[0]['Open']
                
                # Filter for Dividends
                dividends = hist_daily[hist_daily['Dividends'] > 0]['Dividends']
                
                # Simulation Variables
                current_shares = initial_shares
                transaction_log = []
                
                # 2. Process Dividend Reinvestments
                for div_date, div_amount in dividends.items():
                    # Total dividend cash received based on current holdings
                    total_div_cash = div_amount * current_shares
                    
                    # Target Reinvestment Date: 1st Business Day after Payment
                    reinvest_date = div_date + BDay(1)
                    
                    # Ensure reinvest_date is not beyond end_date or current date
                    if reinvest_date > pd.Timestamp(end_date).tz_localize(div_date.tz):
                        continue

                    # Fetch Noon Price for Reinvestment Date
                    # We fetch 1h data for that specific day to get the 12:00 (noon) bar
                    reinvest_date_str = reinvest_date.strftime('%Y-%m-%d')
                    reinvest_end_str = (reinvest_date + BDay(1)).strftime('%Y-%m-%d')
                    
                    hour_data = ticker.history(start=reinvest_date_str, end=reinvest_end_str, interval="1h")
                    
                    # Try to find the 12:00 or 12:30 bar. Fallback to daily close if hour data fails.
                    try:
                        # Find bar closest to 12:00 PM
                        noon_price = hour_data.between_time('12:00', '13:00')['Open'].iloc[0]
                    except:
                        noon_price = hist_daily.loc[reinvest_date.normalize()]['Close'] if reinvest_date in hist_daily.index else hist_daily.asof(reinvest_date)['Close']

                    # DRIP Transaction
                    shares_bought = total_div_cash / noon_price
                    current_shares += shares_bought
                    
                    transaction_log.append({
                        "Dividend Date": div_date.date(),
                        "Dividend/Share": f"${div_amount:.4f}",
                        "Total Div Amount": f"${total_div_cash:.2f}",
                        "Reinvest Price (Noon)": f"${noon_price:.2f}",
                        "Shares Purchased": f"{shares_bought:.4f}",
                        "New Share Total": f"{current_shares:.4f}",
                        "Total Value ($)": f"${(current_shares * noon_price):.2f}"
                    })

                # 3. Final Summary Calculations
                final_price = hist_daily.iloc[-1]['Close']
                final_value = current_shares * final_price
                initial_investment = initial_shares * initial_price
                total_return_dollars = final_value - initial_investment
                total_return_pct = (total_return_dollars / initial_investment) * 100

                # --- UI OUTPUT ---
                
                # Summary Tiles
                st.subheader("📊 Investment Summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Initial Investment", f"${initial_investment:,.2f}")
                col2.metric("Ending Share Value", f"${final_value:,.2f}")
                col3.metric("Total Return ($)", f"${total_return_dollars:,.2f}")
                col4.metric("Total Return (%)", f"{total_return_pct:.2f}%")

                # Input Parameters Table
                st.markdown("---")
                st.markdown("### 📋 Input Parameters")
                summary_data = {
                    "Parameter": ["Ticker", "Start Date", "End Date", "Initial Shares", "Initial Buy Price", "Final Share Balance"],
                    "Value": [ticker_symbol, start_date, end_date, initial_shares, f"${initial_price:.2f}", f"{current_shares:.4f} shares"]
                }
                st.table(pd.DataFrame(summary_data))

                # Transaction Table
                st.markdown("### 💸 Dividend Reinvestment Log (DRIP)")
                if transaction_log:
                    st.dataframe(pd.DataFrame(transaction_log), use_container_width=True)
                else:
                    st.info("No dividends found for this period.")

        except Exception as e:
            st.error(f"An error occurred: {e}")