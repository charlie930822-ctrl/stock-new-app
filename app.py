import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json
import os

# --- 設定網頁標題與版面 ---
st.set_page_config(page_title="我的資產儀表板", layout="wide")
st.title("💰 媽媽狩獵者 的資產儀表板")

# --- [新增功能] 讀取與寫入設定檔 (含加密貨幣) ---
DATA_FILE = "cash_data.json"

def load_settings():
    """從檔案讀取設定(現金+加密貨幣)，如果檔案不存在則回傳預設值"""
    default_data = {
        "twd": 50000, 
        "usd": 1000,
        "btc": 0.0,
        "eth": 0.0,
        "sol": 0.0
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                saved = json.load(f)
                # 確保舊檔案也能讀取到新欄位 (合併預設值)
                return {**default_data, **saved}
        except:
            pass
    return default_data

def save_settings(data_dict):
    """將目前的設定寫入檔案"""
    with open(DATA_FILE, "w") as f:
        json.dump(data_dict, f)

# --- 1. 設定持股資料 (股票維持不變) ---
tw_portfolio = [
    {'code': '2317.TW', 'name': '鴻海', 'shares': 342, 'cost': 166.84},
    {'code': '2330.TW', 'name': '台積電', 'shares': 44, 'cost': 1013.12},
    {'code': '3661.TW', 'name': '世芯-KY', 'shares': 8, 'cost': 3675.00},
]

us_portfolio = [
    {'code': 'AVGO', 'shares': 1, 'cost': 341.00},
    {'code': 'NFLX', 'shares': 10.33591, 'cost': 96.75},
    {'code': 'NVDA', 'shares': 8.93633, 'cost': 173.49},
    {'code': 'SGOV', 'shares': 20.99361, 'cost': 100.28},
    {'code': 'SOFI', 'shares': 36.523, 'cost': 27.38},
    {'code': 'SOUN', 'shares': 5, 'cost': 10.93},
    {'code': 'TSLA', 'shares': 2.55341, 'cost': 399.47},
]

# --- 2. 側邊欄：資產設定 (現金 + 加密貨幣) ---
st.sidebar.header("⚙️ 資產設定")

# A. 讀取紀錄
saved_data = load_settings()

# B. 現金設定
st.sidebar.subheader("💵 法幣現金")
cash_twd = st.sidebar.number_input("台幣 (TWD)", value=float(saved_data["twd"]), step=10000.0)
cash_usd = st.sidebar.number_input("美金 (USD)", value=float(saved_data["usd"]), step=100.0)

# C. 加密貨幣設定 (輸入顆數)
st.sidebar.subheader("🪙 加密貨幣 (顆數)")
btc_qty = st.sidebar.number_input("比特幣 (BTC)", value=float(saved_data["btc"]), step=0.001, format="%.4f")
eth_qty = st.sidebar.number_input("以太幣 (ETH)", value=float(saved_data["eth"]), step=0.01, format="%.4f")
sol_qty = st.sidebar.number_input("Solana (SOL)", value=float(saved_data["sol"]), step=0.1, format="%.2f")

# D. 檢查並存檔 (只要有任何變動就存檔)
current_data = {
    "twd": cash_twd, "usd": cash_usd,
    "btc": btc_qty, "eth": eth_qty, "sol": sol_qty
}
if current_data != saved_data:
    save_settings(current_data)

# --- 3. 核心計算函數 ---
@st.cache_data(ttl=300) 
def get_data_and_calculate(btc_q, eth_q, sol_q):
    # 1. 抓匯率
    try:
        usdtwd = yf.Ticker("USDTWD=X").history(period="1d")['Close'].iloc[-1]
    except:
        usdtwd = 32.5 
        
    data_list = []
    
    # 2. 處理台股
    for item in tw_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            
            if len(hist) >= 2:
                price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                change_price = price - prev_close
                change_pct = (change_price / prev_close) * 100
            else:
                price = hist['Close'].iloc[-1]
                change_price = 0
                change_pct = 0

            market_val = price * item['shares']
            cost_val = item['cost'] * item['shares']
            profit = market_val - cost_val
            profit_pct = (profit / cost_val) * 100 if cost_val
