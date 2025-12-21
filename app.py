import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 👇 請在這裡填入您實際購入的股票與加密貨幣 👇
# ==========================================
# 格式： "代號": {"cost": 平均成本, "qty": 持有數量}
MY_PORTFOLIO = {
    # --- 股票範例 (台股記得加 .TW) ---
    "2330.TW": {"cost": 580.0,  "qty": 2000},   # 台積電: 成本580, 2張(2000股)
    "0050.TW": {"cost": 130.5,  "qty": 500},    # 0050: 成本130.5, 500股
    "NVDA":    {"cost": 480.0,  "qty": 20},     # 輝達: 成本480, 20股
    
    # --- 加密貨幣範例 ---
    "BTC-USD": {"cost": 42000.0, "qty": 0.05},  # 比特幣
    "ETH-USD": {"cost": 2500.0,  "qty": 1.5},   # 以太幣
}
# ==========================================

st.set_page_config(page_title="我的動態投資儀表板", layout="wide")
st.title("📈 個人資產即時損益監控")

# ==========================================
# 左側邊欄 (Sidebar) - 設定區
# ==========================================
st.sidebar.header("1. 資產池設定")

# 自動從上方的 MY_PORTFOLIO 產生預設字串
default_stock_str = ", ".join([k for k in MY_PORTFOLIO.keys() if ".TW" in k or "-" not in k])
default_crypto_str = ", ".join([k for k in MY_PORTFOLIO.keys() if "-" in k])

# 讓使用者輸入代號 (預設值會帶入上面的設定)
input_stocks = st.sidebar.text_input("股票代號列表", value=default_stock_str)
input_cryptos = st.sidebar.text_input("加密貨幣代號列表", value=default_crypto_str)

# 將字串轉換為 list
stock_list = [x.strip() for x in input_stocks.split(',') if x.strip()]
crypto_list = [x.strip() for x in input_cryptos.split(',') if x.strip()]

portfolio_data = []

st.sidebar.markdown("---")
st.sidebar.header("2. 持有成本與數量 (可微調)")

# --- 處理股票輸入 ---
if stock_list:
    st.sidebar.subheader("🏢 股票持倉")
    for ticker in stock_list:
        # 嘗試從預設設定中抓取數值，如果沒有則為 0
        default_cost = MY_PORTFOLIO.get(ticker, {}).get("cost", 0.0)
        default_qty = float(MY_PORTFOLIO.get(ticker, {}).get("qty", 0.0))

        with st.sidebar.expander(f"{ticker} 設定", expanded=False):
            cost = st.number_input(f"{ticker} 平均成本", min_value=0.0, value=default_cost, step=1.0, key=f"cost_{ticker}")
            shares = st.number_input(f"{ticker} 持有股數", min_value=0.0, value=default_qty, step=1.0, key=f"shares_{ticker}")
            
            if shares > 0:
                portfolio_data.append({
                    "Type": "Stock",
                    "Ticker": ticker,
                    "Cost_Price": cost,
                    "Quantity": shares
                })

# --- 處理加密貨幣輸入 ---
if crypto_list:
    st.sidebar.subheader("🪙 加密貨幣持倉")
    for ticker in crypto_list:
        # 嘗試從預設設定中抓取數值
        default_cost = MY_PORTFOLIO.get(ticker, {}).get("cost", 0.0)
        default_qty = float(MY_PORTFOLIO.get(ticker, {}).get("qty", 0.0))

        with st.sidebar.expander(f"{ticker} 設定", expanded=False):
            cost = st.number_input(f"{ticker} 平均成本 (USD)", min_value=0.0, value=default_cost, step=0.1, format="%.2f", key=f"cost_{ticker}")
            qty = st.number_input(f"{ticker} 持有顆數", min_value=0.0, value=default_qty, step=0.0001, format="%.4f", key=f"qty_{ticker}")
            
            if qty > 0:
                portfolio_data.append({
                    "Type": "Crypto",
                    "Ticker": ticker,
                    "Cost_Price": cost,
                    "Quantity": qty
                })

# ==========================================
# 主畫面邏輯
# ==========================================

if not portfolio_data:
    st.info("👈 請在左側確認您的持倉資訊。")
else:
    df_portfolio = pd.DataFrame(portfolio_data)
    all_tickers = df_portfolio["Ticker"].tolist()
    
    with st.spinner('正在從 Yahoo Finance 抓取最新報價...'):
        try:
            tickers_string = " ".join(all_tickers)
            data = yf.Tickers(tickers_string)
            
            current_prices = []
            market_values = []
            profits = []
            rois = []
            
            for index, row in df_portfolio.iterrows():
                symbol = row['Ticker']
                try:
                    # 針對台股或美股不同結構的容錯
                    ticker_obj = data.tickers[symbol]
                    hist = ticker_obj.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                    else:
                        price = 0.0 # 抓不到資料時
                except:
                    price = 0.0
                
                current_value = price * row['Quantity']
                cost_value = row['Cost_Price'] * row['Quantity']
                profit = current_value - cost_value
                roi = (profit / cost_value * 100) if cost_value > 0 else 0
                
                current_prices.append(price)
                market_values.append(current_value)
                profits.append(profit)
                rois.append(roi)
            
            df_portfolio["現價"] = current_prices
            df_portfolio["市值"] = market_values
            df_portfolio["損益 ($)"] = profits
            df_portfolio["報酬率 (%)"] = rois
            
            # 總計
            total_market_value = df_portfolio["市值"].sum()
            total_profit = df_portfolio["損益 ($)"].sum()
            total_cost = (df_portfolio["Cost_Price"] * df_portfolio["Quantity"]).sum()
            total_roi = (total_profit / total_cost * 100) if total_cost > 0 else 0

            # 顯示
            col1, col2, col3 = st.columns(3)
            col1.metric("總資產市值", f"${total_market_value:,.2f}")
            col2.metric("總損益", f"${total_profit:,.2f}", delta=f"{total_profit:,.2f}")
            col3.metric("總報酬率", f"{total_roi:.2f}%", delta=f"{total_roi:.2f}%")
            
            st.divider()

            st.subheader("詳細持倉清單")
            st.dataframe(
                df_portfolio.style.format({
                    "Cost_Price": "{:.2f}",
                    "Quantity": "{:.4f}",
                    "現價": "{:.2f}",
                    "市值": "{:.2f}",
                    "損益 ($)": "{:.2f}",
                    "報酬率 (%)": "{:.2f}%"
                }).applymap(lambda v: 'color: green;' if v > 0 else 'color: red;', subset=['損益 ($)', '報酬率 (%)']),
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"發生錯誤: {e}")
