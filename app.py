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

# --- [功能] 讀取與寫入設定檔 ---
DATA_FILE = "cash_data.json"

def load_settings():
    """從檔案讀取設定，如果檔案不存在則回傳預設值"""
    default_data = {
        # 銀行、實體、以及 MAX交易所現金
        "twd_bank": 50000, 
        "twd_physical": 0,
        "twd_max": 0,
        "usd": 1000,
        
        # 加密貨幣設定
        "btc": 0.0, "btc_cost_twd": 2911966.1,
        "eth": 0.0, "eth_cost_twd": 93579.1,
        "sol": 0.0, "sol_cost_twd": 3922.8
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                saved = json.load(f)
                if "twd" in saved and "twd_bank" not in saved:
                    saved["twd_bank"] = saved["twd"]
                return {**default_data, **saved}
        except:
            pass
    return default_data

def save_settings(data_dict):
    """將目前的設定寫入檔案"""
    with open(DATA_FILE, "w") as f:
        json.dump(data_dict, f)

# --- 1. 設定持股資料 (台股維持不變) ---
tw_portfolio = [
    {'code': '2317.TW', 'name': '鴻海', 'shares': 342, 'cost': 166.84},
    {'code': '2330.TW', 'name': '台積電', 'shares': 44, 'cost': 1013.12},
    {'code': '3661.TW', 'name': '世芯-KY', 'shares': 8, 'cost': 3675.00},
]

# --- [更新] 美股資料 (維持您最新的精確持倉) ---
us_portfolio = [
    {'code': 'AVGO', 'shares': 1, 'cost': 341.00},
    {'code': 'GRAB', 'shares': 50, 'cost': 5.125},
    {'code': 'NFLX', 'shares': 10.33591, 'cost': 96.75007},
    {'code': 'NVDA', 'shares': 8.93654, 'cost': 173.48549},
    {'code': 'SGOV', 'shares': 13.44337, 'cost': 100.28736},
    {'code': 'SOFI', 'shares': 36.523, 'cost': 27.38001},
    {'code': 'SOUN', 'shares': 5, 'cost': 10.93},
    {'code': 'TSLA', 'shares': 4.42199, 'cost': 423.40823}, 
]

# --- 2. 側邊欄：資產設定 ---
st.sidebar.header("⚙️ 資產設定")

saved_data = load_settings()

# 法幣現金區塊
st.sidebar.subheader("💵 法幣現金")
cash_twd_bank = st.sidebar.number_input("🏦 銀行存款 (TWD)", value=float(saved_data.get("twd_bank", 50000)), step=10000.0)
cash_twd_physical = st.sidebar.number_input("🧧 實體現鈔 (TWD)", value=float(saved_data.get("twd_physical", 0)), step=1000.0)
cash_twd_max = st.sidebar.number_input("🟣 MAX 交易所 (TWD)", value=float(saved_data.get("twd_max", 0)), step=1000.0)
cash_usd = st.sidebar.number_input("🇺🇸 美金 (USD)", value=float(saved_data["usd"]), step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 加密貨幣設定")
st.sidebar.caption("請輸入持有數量與 **台幣平均成本**")

# BTC
c1, c2 = st.sidebar.columns(2)
btc_qty = c1.number_input("BTC 顆數", value=float(saved_data["btc"]), step=0.00000001, format="%.8f")
btc_cost_twd = c2.number_input("BTC 均價(NT)", value=float(saved_data.get("btc_cost_twd", 2911966.1)), step=1000.0, format="%.1f")

# ETH
c3, c4 = st.sidebar.columns(2)
eth_qty = c3.number_input("ETH 顆數", value=float(saved_data["eth"]), step=0.00000001, format="%.8f")
eth_cost_twd = c4.number_input("ETH 均價(NT)", value=float(saved_data.get("eth_cost_twd", 93579.1)), step=100.0, format="%.1f")

# SOL
c5, c6 = st.sidebar.columns(2)
sol_qty = c5.number_input("SOL 顆數", value=float(saved_data["sol"]), step=0.00000001, format="%.8f")
sol_cost_twd = c6.number_input("SOL 均價(NT)", value=float(saved_data.get("sol_cost_twd", 3922.8)), step=10.0, format="%.1f")

# 存檔
current_data = {
    "twd_bank": cash_twd_bank, 
    "twd_physical": cash_twd_physical,
    "twd_max": cash_twd_max,
    "usd": cash_usd,
    "btc": btc_qty, "btc_cost_twd": btc_cost_twd,
    "eth": eth_qty, "eth_cost_twd": eth_cost_twd,
    "sol": sol_qty, "sol_cost_twd": sol_cost_twd
}
if current_data != saved_data:
    save_settings(current_data)

# --- 3. 核心計算函數 ---
@st.cache_data(ttl=30) 
def get_data_and_calculate(btc_d, eth_d, sol_d):
    try:
        usdtwd = yf.Ticker("USDTWD=X").history(period="1d")['Close'].iloc[-1]
    except:
        usdtwd = 32.5 
        
    data_list = []
    
    # 台股
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

    # 美股 (修改重點：移除 is_today_data 判斷，直接抓最新兩筆比對)
    for item in us_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            hist = hist.dropna()
            
            if not hist.empty:
                # 抓最後一筆 (如果是週末，這就是週五收盤價)
                price = hist['Close'].iloc[-1]
                
                # 直接跟前一筆交易日比較
                if len(hist) >= 2:
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

    # 加密貨幣
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
                    price_usd = hist['Close'].iloc[-1]
                    
                    if len(hist) >= 2:
                        prev_usd = hist['Close'].iloc[-2]
                        change_usd = price_usd - prev_usd
                        change_pct = (change_usd / prev_usd) * 100
                    else:
                        change_usd = 0
                        change_pct = 0
                    
                    price_twd = price_usd * usdtwd
                    market_val_twd = price_twd * info['qty']
                    total_cost_twd = info['cost_twd'] * info['qty']
                    profit_twd = market_val_twd - total_cost_twd
                    profit_pct = (profit_twd / total_cost_twd * 100) if total_cost_twd > 0 else 0
                    
                    data_list.append({
                        "代號": info['name'],
                        "類型": "Crypto",
                        "現價": price_usd,
                        "漲跌": change_usd,
                        "幅度%": change_pct,
                        "今日損益": (change_usd * info['qty']) * usdtwd,
                        "市值": market_val_twd,
                        "總損益": profit_twd,
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

btc_data = {'qty': btc_qty, 'cost_twd': btc_cost_twd}
eth_data = {'qty': eth_qty, 'cost_twd': eth_cost_twd}
sol_data = {'qty': sol_qty, 'cost_twd': sol_cost_twd}

df, rate = get_data_and_calculate(btc_data, eth_data, sol_data)

crypto_df = df[df['類型'] == 'Crypto']
stock_df = df[df['類型'] != 'Crypto']

crypto_total_val = crypto_df['市值'].sum() if not crypto_df.empty else 0
stock_total_val = stock_df['市值'].sum() if not stock_df.empty else 0

# 計算總現金
total_cash_twd_only = cash_twd_bank + cash_twd_physical + cash_twd_max
cash_total_val = total_cash_twd_only + (cash_usd * rate)

total_assets = stock_total_val + crypto_total_val + cash_total_val
total_profit = df['總損益'].sum() 

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
col2.metric("💰 總獲利 (TWD)", f"${total_profit:,.0f}", delta=f"{total_return_rate:.2f}%")
col3.metric("📅 今日變動 (TWD)", f"${today_change_total:,.0f}", delta=f"{today_change_pct:.2f}%")
col4.metric("💵 現金部位 (TWD)", f"${cash_total_val:,.0f}")
col5.metric("🪙 加密貨幣 (TWD)", f"${crypto_total_val:,.0f}")

st.caption(f"註：美股與幣圈損益已自動依匯率 (1:{rate:.2f}) 換算為台幣。")
st.divider()

# --- 7. 圖表與詳細表格 ---
col_chart, col_table = st.columns([0.35, 0.65])

with col_chart:
    st.subheader("📊 資產配置")
    chart_df = df[['代號', '市值']].copy()
    
    # 顯示現金細項
    if cash_twd_bank > 0:
        new_row = pd.DataFrame([{'代號': '銀行存款', '市值': cash_twd_bank}])
        chart_df = pd.concat([chart_df, new_row], ignore_index=True)
        
    if cash_twd_physical > 0:
        new_row = pd.DataFrame([{'代號': '實體現鈔', '市值': cash_twd_physical}])
        chart_df = pd.concat([chart_df, new_row], ignore_index=True)

    if cash_twd_max > 0:
        new_row = pd.DataFrame([{'代號': 'MAX 交易所', '市值': cash_twd_max}])
        chart_df = pd.concat([chart_df, new_row], ignore_index=True)
        
    if cash_usd > 0:
        new_row = pd.DataFrame([{'代號': '美金存款', '市值': cash_usd * rate}])
        chart_df = pd.concat([chart_df, new_row], ignore_index=True)
    
    fig = px.pie(chart_df, values='市值', names='代號', hole=0.4, 
                 title=f"總資產: ${total_assets:,.0f}")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.subheader("📋 持股與幣圈詳細行情")
    
    display_df = df[['代號', '類型', '現價', '漲跌', '幅度%', '市值', '佔比%', '今日損益', '總報酬%', '總損益']].copy()
    
    styled_df = display_df.style.map(color_tw_style, subset=['漲跌', '幅度%', '今日損益', '總報酬%', '總損益']) \
        .format({
            '現價': '{:.2f}', 
            '漲跌': '{:+.2f}',
            '幅度%': '{:+.2f}%',
            '市值': '${:,.0f}',
            '今日損益': '${:,.0f}',
            '佔比%': '{:.1f}%',        
            '總報酬%': '{:+.2f}%',
            '總損益': '${:,.0f}' 
        })

    st.dataframe(
        styled_df,
        height=500,
        use_container_width=True,
        hide_index=True,
        column_config={
            "代號": st.column_config.TextColumn("代號"),
            "現價": st.column_config.NumberColumn("現價 (USD)"), 
            "佔比%": st.column_config.ProgressColumn(
                "佔總資產 %", 
                format="%.1f%%", 
                min_value=0, 
                max_value=100
            ),
        }
    )
