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

us_portfolio = [
    {'code': 'AVGO', 'shares': 1, 'cost': 341.00},
    {'code': 'NFLX', 'shares': 10.33591, 'cost': 96.75},
    {'code': 'NVDA', 'shares': 8.93633, 'cost': 173.49},
    {'code': 'SGOV', 'shares': 20.99361, 'cost': 100.28},
    {'code': 'SOFI', 'shares': 36.523, 'cost': 27.38},
    {'code': 'SOUN', 'shares': 5, 'cost': 10.93},
    {'code': 'TSLA', 'shares': 2.55341, 'cost': 399.47},
]

# --- 2. 側邊欄：資產設定 ---
st.sidebar.header("⚙️ 資產設定")

saved_data = load_settings()

st.sidebar.subheader("💵 法幣現金")
cash_twd = st.sidebar.number_input("台幣 (TWD)", value=float(saved_data["twd"]), step=10000.0)
cash_usd = st.sidebar.number_input("美金 (USD)", value=float(saved_data["usd"]), step=100.0)

st.sidebar.subheader("🪙 加密貨幣 (顆數)")
btc_qty = st.sidebar.number_input("比特幣 (BTC)", value=float(saved_data["btc"]), step=0.001, format="%.4f")
eth_qty = st.sidebar.number_input("以太幣 (ETH)", value=float(saved_data["eth"]), step=0.01, format="%.4f")
sol_qty = st.sidebar.number_input("Solana (SOL)", value=float(saved_data["sol"]), step=0.1, format="%.2f")

current_data = {
    "twd": cash_twd, "usd": cash_usd,
    "btc": btc_qty, "eth": eth_qty, "sol": sol_qty
}
if current_data != saved_data:
    save_settings(current_data)

# --- 3. 核心計算函數 ---
@st.cache_data(ttl=300) 
def get_data_and_calculate(btc_q, eth_q, sol_q):
    try:
        usdtwd = yf.Ticker("USDTWD=X").history(period="1d")['Close'].iloc[-1]
    except:
        usdtwd = 32.5 
        
    data_list = []
    
    # 取得系統當前日期 (用於判斷是否為當日數據)
    today_date = pd.Timestamp.now().date()

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

    # 美股 (修改重點區)
    for item in us_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            hist = hist.dropna()
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                
                # [關鍵修改] 判斷這筆資料的日期是否為「今天」
                # 因為美股在台灣週一白天時，最新資料仍是「上週五」
                # 如果資料日期 != 今天，代表今日尚未開盤，強制將漲跌設為 0
                data_date = hist.index[-1].date()
                is_today_data = (data_date == today_date)

                if is_today_data and len(hist) >= 2:
                    # 如果是今天的資料 (開盤後)，正常計算漲跌
                    prev_close = hist['Close'].iloc[-2]
                    change_price = price - prev_close
                    change_pct = (change_price / prev_close) * 100
                else:
                    # 如果是舊資料 (尚未開盤)，顯示 0
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
                    # 今日損益會因為 change_price 為 0 而變為 0
                    "今日損益": (change_price * item['shares']) * usdtwd,
                    "市值": market_val_usd * usdtwd,
                    "總損益": profit_usd * usdtwd,
                    "總報酬%": profit_pct
                })
        except:
            pass

    # 加密貨幣 (維持不變，因為它是 24 小時交易)
    crypto_map = {
        'BTC-USD': {'name': 'BTC', 'qty': btc_q},
        'ETH-USD': {'name': 'ETH', 'qty': eth_q},
        'SOL-USD': {'name': 'SOL', 'qty': sol_q}
    }
    
    for code, info in crypto_map.items():
        if info['qty'] > 0:
            try:
                ticker = yf.Ticker(code)
                hist = ticker.history(period="5d")
                hist = hist.dropna()
                
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    if len(hist) >= 2:
                        prev = hist['Close'].iloc[-2]
                        change_p = price - prev
                        change_pct = (change_p / prev) * 100
                    else:
                        change_p = 0
                        change_pct = 0
                    
                    market_val_usd = price * info['qty']
                    
                    data_list.append({
                        "代號": info['name'],
                        "類型": "Crypto",
                        "現價": price,
                        "漲跌": change_p,
                        "幅度%": change_pct,
                        "今日損益": (change_p * info['qty']) * usdtwd,
                        "市值": market_val_usd * usdtwd,
                        "總損益": 0,
                        "總報酬%": 0
                    })
            except:
                pass
            
    return pd.DataFrame(data_list), usdtwd

# --- 4. 樣式設定函數 ---
def color_tw_style(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #FF4B4B; font-weight: bold'
        elif val < 0: return 'color: #00C853; font-weight: bold'
        elif val == 0: return 'color: white; opacity: 0.5' # 0 的時候顯示稍微透明的白色
    return ''

# --- 5. 執行與計算 ---
st.write("🔄 正在取得最新報價 (含加密貨幣)...")
df, rate = get_data_and_calculate(btc_qty, eth_qty, sol_qty)

crypto_df = df[df['類型'] == 'Crypto']
stock_df = df[df['類型'] != 'Crypto']

crypto_total_val = crypto_df['市值'].sum() if not crypto_df.empty else 0
stock_total_val = stock_df['市值'].sum() if not stock_df.empty else 0
cash_total_val = cash_twd + (cash_usd * rate)

total_assets = stock_total_val + crypto_total_val + cash_total_val
total_profit = df['總損益'].sum() 

total_return_rate = 0 
if stock_total_val != 0: 
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
    if cash_total_val > 0:
        new_row = pd.DataFrame([{'代號': '現金 (Cash)', '市值': cash_total_val}])
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
            "佔比%": st.column_config.ProgressColumn(
                "佔總資產 %", 
                format="%.1f%%", 
                min_value=0, 
                max_value=100
            ),
        }
    )
