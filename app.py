import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime

# --- 設定網頁標題與版面 ---
st.set_page_config(page_title="我的資產儀表板", layout="wide")
st.title("💰 媽媽狩獵者 的資產儀表板")

# --- [新增功能] 讀取與寫入設定檔 (改為紀錄台幣成本) ---
DATA_FILE = "cash_data.json"

def load_settings():
    """從檔案讀取設定，如果檔案不存在則回傳預設值"""
    default_data = {
        "twd": 50000, 
        "usd": 1000,
        # 你的預設持倉與台幣成本
        "btc": 0.0, "btc_cost_twd": 2911966.1,
        "eth": 0.0, "eth_cost_twd": 93579.1,
        "sol": 0.0, "sol_cost_twd": 3922.8
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                saved = json.load(f)
                # 確保舊檔案也能讀取到新欄位
                return {**default_data, **saved}
        except:
            pass
    return default_data

def save_settings(data_dict):
    """將目前的設定寫入檔案"""
    with open(DATA_FILE, "w") as f:
        json.dump(data_dict, f)

# --- 1. 設定持股資料 ---
tw_portfolio = [
    {'code': '2317.TW', 'name': '鴻海', 'shares': 342, 'cost': 166.84},
    {'code': '2330.TW', 'name': '台積電', 'shares': 44, 'cost': 1013.12},
    {'code': '3661.TW', 'name': '世芯-KY', 'shares': 8, 'cost': 3675.00},
]

# [更新] 根據你的最新截圖填入精確數據
us_portfolio = [
    {'code': 'AVGO', 'shares': 1, 'cost': 341.00},
    {'code': 'GRAB', 'shares': 50, 'cost': 5.125},  # 新增 GRAB
    {'code': 'NFLX', 'shares': 10.33591, 'cost': 96.75007},
    {'code': 'NVDA', 'shares': 8.93633, 'cost': 173.48509},
    {'code': 'SGOV', 'shares': 16.00807, 'cost': 100.28004}, # 更新股數
    {'code': 'SOFI', 'shares': 36.523, 'cost': 27.38001},
    {'code': 'SOUN', 'shares': 5, 'cost': 10.93},
    {'code': 'TSLA', 'shares': 2.55341, 'cost': 399.46581},
]

# --- 2. 側邊欄：資產設定 ---
st.sidebar.header("⚙️ 資產設定")

saved_data = load_settings()

st.sidebar.subheader("💵 法幣現金")
cash_twd = st.sidebar.number_input("台幣 (TWD)", value=float(saved_data["twd"]), step=10000.0)
cash_usd = st.sidebar.number_input("美金 (USD)", value=float(saved_data["usd"]), step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 加密貨幣設定")
st.sidebar.caption("請輸入持有數量與 **台幣平均成本**")

# BTC
c1, c2 = st.sidebar.columns(2)
btc_qty = c1.number_input("BTC 顆數", value=float(saved_data["btc"]), step=0.001, format="%.4f")
# key值換成 _twd 避免跟舊的衝突
btc_cost_twd = c2.number_input("BTC 均價(NT)", value=float(saved_data.get("btc_cost_twd", 2911966.1)), step=1000.0, format="%.1f")

# ETH
c3, c4 = st.sidebar.columns(2)
eth_qty = c3.number_input("ETH 顆數", value=float(saved_data["eth"]), step=0.01, format="%.4f")
eth_cost_twd = c4.number_input("ETH 均價(NT)", value=float(saved_data.get("eth_cost_twd", 93579.1)), step=100.0, format="%.1f")

# SOL
c5, c6 = st.sidebar.columns(2)
sol_qty = c5.number_input("SOL 顆數", value=float(saved_data["sol"]), step=0.1, format="%.2f")
sol_cost_twd = c6.number_input("SOL 均價(NT)", value=float(saved_data.get("sol_cost_twd", 3922.8)), step=10.0, format="%.1f")

# 存檔
current_data = {
    "twd": cash_twd, "usd": cash_usd,
    "btc": btc_qty, "btc_cost_twd": btc_cost_twd,
    "eth": eth_qty, "eth_cost_twd": eth_cost_twd,
    "sol": sol_qty, "sol_cost_twd": sol_cost_twd
}
if current_data != saved_data:
    save_settings(current_data)

# --- 3. 核心計算函數 ---
@st.cache_data(ttl=300) 
def get_data_and_calculate(btc_d, eth_d, sol_d):
    # 傳入的 *_d 包含 'qty' 和 'cost_twd'
    try:
        usdtwd = yf.Ticker("USDTWD=X").history(period="1d")['Close'].iloc[-1]
    except:
        usdtwd = 32.5 
        
    data_list = []
    today_date = pd.Timestamp.now().date()

    # 台股 (邏輯不變)
    for item in tw_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            hist = hist.dropna()
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    change_price = price - prev_close
                    change_pct = (change_price / prev_close) * 100
                else:
                    change_price = 0
                    change_pct = 0

                market_val = price * item['shares']
                cost_val = item['cost'] * item['shares']
                profit = market_val - cost_val
                profit_pct = (profit / cost_val) * 100 if cost_val != 0 else 0
                
                data_list.append({
                    "代號": item['name'],
                    "類型": "台股",
                    "現價": price,
                    "漲跌": change_price,
                    "幅度%": change_pct,
                    "今日損益": change_price * item['shares'],
                    "市值": market_val,
                    "總損益": profit,
                    "總報酬%": profit_pct
                })
        except:
            pass

    # 美股 (週一不顯示波動邏輯不變)
    for item in us_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            hist = hist.dropna()
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                data_date = hist.index[-1].date()
                is_today_data = (data_date == today_date)

                if is_today_data and len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    change_price = price - prev_close
                    change_pct = (change_price / prev_close) * 100
                else:
                    change_price = 0
                    change_pct = 0
                
                market_val_usd = price * item['shares']
                cost_val_usd = item['cost'] * item['shares']
                profit_usd = market_val_usd - cost_val_usd
                profit_pct = (profit_usd / cost_val_usd) * 100 if cost_val_usd != 0 else 0
                
                data_list.append({
                    "代號": item['code'],
                    "類型": "美股",
                    "現價": price,
                    "漲跌": change_price,        
                    "幅度%": change_pct,
                    "今日損益": (change_price * item['shares']) * usdtwd,
                    "市值": market_val_usd * usdtwd,
                    "總損益": profit_usd * usdtwd,
                    "總報酬%": profit_pct
                })
        except:
            pass

    # 加密貨幣 (改用台幣成本計算)
    crypto_map = {
        'BTC-USD': {'name': 'BTC', 'qty': btc_d['qty'], 'cost_twd': btc_d['cost_twd']},
        'ETH-USD': {'name': 'ETH', 'qty': eth_d['qty'], 'cost_twd': eth_d['cost_twd']},
        'SOL-USD': {'name': 'SOL', 'qty': sol_d['qty'], 'cost_twd': sol_d['cost_twd']}
    }
    
    for code, info in crypto_map.items():
        if info['qty'] > 0:
            try:
                ticker = yf.Ticker(code)
                hist = ticker.history(period="5d")
                hist = hist.dropna()
                
                if not hist.empty:
                    # 這是美金現價
                    price_usd = hist['Close'].iloc[-1]
                    
                    if len(hist) >= 2:
                        prev_usd = hist['Close'].iloc[-2]
                        change_usd = price_usd - prev_usd
                        change_pct = (change_usd / prev_usd) * 100
                    else:
                        change_usd = 0
                        change_pct = 0
                    
                    # --- 關鍵換算 ---
                    # 1. 計算台幣現價 (美金現價 * 匯率)
                    price_twd = price_usd * usdtwd
                    
                    # 2. 市值 (台幣)
                    market_val_twd = price_twd * info['qty']
                    
                    # 3. 總成本 (台幣成本 * 顆數)
                    total_cost_twd = info['cost_twd'] * info['qty']
                    
                    # 4. 總損益 (台幣)
                    profit_twd = market_val_twd - total_cost_twd
                    
                    profit_pct = (profit_twd / total_cost_twd * 100) if total_cost_twd > 0 else 0
                    
                    data_list.append({
                        "代號": info['name'],
                        "類型": "Crypto",
                        "現價": price_usd, # 表格還是顯示美金報價比較習慣
                        "漲跌": change_usd,
                        "幅度%": change_pct,
                        "今日損益": (change_usd * info['qty']) * usdtwd,
                        "市值": market_val_twd,
                        "總損益": profit_twd, # 這是準確的台幣損益
                        "總報酬%": profit_pct
                    })
            except:
                pass
            
    return pd.DataFrame(data_list), usdtwd

# --- 4. 樣式設定函數 ---
def color_tw_style(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #FF4B4B; font-weight: bold'
        elif val < 0: return 'color: #00C853; font-weight: bold'
        elif val == 0: return 'color: white; opacity: 0.5'
    return ''

# --- 5. 執行與計算 ---
st.write("🔄 正在取得最新報價 (含加密貨幣)...")

# 包裝參數 (改成 cost_twd)
btc_data = {'qty': btc_qty, 'cost_twd': btc_cost_twd}
eth_data = {'qty': eth_qty, 'cost_twd': eth_cost_twd}
sol_data = {'qty': sol_qty, 'cost_twd': sol_cost_twd}

df, rate = get_data_and_calculate(btc_data, eth_data, sol_data)

crypto_df = df[df['類型'] == 'Crypto']
stock_df = df[df['類型'] != 'Crypto']

crypto_total_val = crypto_df['市值'].sum() if not crypto_df.empty else 0
stock_total_val = stock_df['市值'].sum() if not stock_df.empty else 0
cash_total_val = cash_twd + (cash_usd * rate)

total_assets = stock_total_val + crypto_total_val + cash_total_val
total_profit = df['總損益'].sum() 

# 投資報酬率計算
total_return_rate = 0 
invested_capital = (stock_total_val + crypto_total_val) - total_profit
if invested_capital > 0:
    total_return_rate = (total_profit / invested_capital) * 100

today_change_total = df['今日損益'].sum()
today_change_pct = (today_change_total / total_assets) * 100 if total_assets != 0 else 0

df['佔比%'] = (df['市值'] / total_assets) * 100

# --- 6. 顯示上方大數據 ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🏆 總資產 (TWD)", f"${total_assets:,.0f}")
col2.metric("💰 總獲利 (TWD)", f"${total_profit:,.0f}", delta=f"{total_return_rate
