import streamlit as st
import yfinance as yf
import pandas as pd

# 設定網頁標題與排版
st.set_page_config(page_title="我的動態投資儀表板", layout="wide")
st.title("📈 個人資產即時損益監控")

# ==========================================
# 左側邊欄 (Sidebar) - 設定區
# ==========================================
st.sidebar.header("1. 資產池設定")
st.sidebar.caption("在此輸入代號，用逗號分隔 (例如: AAPL, TSLA)")

# 讓使用者輸入代號字串
input_stocks = st.sidebar.text_input("股票代號列表", value="AAPL, NVDA, 2330.TW")
input_cryptos = st.sidebar.text_input("加密貨幣代號列表", value="BTC-USD, ETH-USD")

# 將字串轉換為 list，並去除空白
stock_list = [x.strip() for x in input_stocks.split(',') if x.strip()]
crypto_list = [x.strip() for x in input_cryptos.split(',') if x.strip()]

# 建立一個用來儲存投資組合數據的 List
portfolio_data = []

st.sidebar.markdown("---")
st.sidebar.header("2. 輸入持有成本與數量")

# --- 處理股票輸入 ---
if stock_list:
    st.sidebar.subheader("🏢 股票持倉")
    for ticker in stock_list:
        with st.sidebar.expander(f"{ticker} 設定", expanded=False):
            # 這裡產生動態輸入框，key 必須唯一，所以加上 ticker 當後綴
            cost = st.number_input(f"{ticker} 平均成本", min_value=0.0, value=0.0, step=1.0, key=f"cost_{ticker}")
            shares = st.number_input(f"{ticker} 持有股數", min_value=0.0, value=0.0, step=1.0, key=f"shares_{ticker}")
            
            if shares > 0: # 只有當持有數大於 0 才加入計算
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
        with st.sidebar.expander(f"{ticker} 設定", expanded=False):
            # 加密貨幣的小數點位數通常較多，format設定為 %.4f
            cost = st.number_input(f"{ticker} 平均成本 (USD)", min_value=0.0, value=0.0, step=0.1, format="%.2f", key=f"cost_{ticker}")
            qty = st.number_input(f"{ticker} 持有顆數", min_value=0.0, value=0.0, step=0.01, format="%.4f", key=f"qty_{ticker}")
            
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
    st.info("👈 請在左側輸入代號，並填寫成本與數量以開始計算。")
else:
    # 轉換成 DataFrame 方便處理
    df_portfolio = pd.DataFrame(portfolio_data)
    
    # 取得所有需要的代號
    all_tickers = df_portfolio["Ticker"].tolist()
    
    # 顯示載入狀態
    with st.spinner('正在從 Yahoo Finance 抓取最新報價...'):
        try:
            # 一次抓取所有資料以節省時間
            tickers_string = " ".join(all_tickers)
            data = yf.Tickers(tickers_string)
            
            # 計算邏輯
            current_prices = []
            market_values = []
            profits = []
            rois = []
            
            for index, row in df_portfolio.iterrows():
                symbol = row['Ticker']
                # 獲取當前價格 (若抓不到則設為 0)
                try:
                    # yfinance 有時回傳結構不同，這裡做個保護
                    ticker_obj = data.tickers[symbol]
                    # 嘗試抓 regularMarketPrice，有些可能是 history
                    price = ticker_obj.history(period="1d")['Close'].iloc[-1]
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
            
            # 將計算結果填回 DataFrame
            df_portfolio["現價"] = current_prices
            df_portfolio["市值"] = market_values
            df_portfolio["損益 ($)"] = profits
            df_portfolio["報酬率 (%)"] = rois
            
            # --- 顯示總覽 ---
            total_market_value = df_portfolio["市值"].sum()
            total_profit = df_portfolio["損益 ($)"].sum()
            total_cost = (df_portfolio["Cost_Price"] * df_portfolio["Quantity"]).sum()
            total_roi = (total_profit / total_cost * 100) if total_cost > 0 else 0

            # 使用 Metrics 顯示大數字
            col1, col2, col3 = st.columns(3)
            col1.metric("總資產市值", f"${total_market_value:,.2f}")
            col2.metric("總損益", f"${total_profit:,.2f}", delta=f"{total_profit:,.2f}")
            col3.metric("總報酬率", f"{total_roi:.2f}%", delta=f"{total_roi:.2f}%")
            
            st.divider()

            # --- 顯示詳細表格 ---
            st.subheader("詳細持倉清單")
            
            # 格式化表格顯示
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
            st.error(f"發生錯誤，請檢查代號是否正確或網路連線: {e}")
