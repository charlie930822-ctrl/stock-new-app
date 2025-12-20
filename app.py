
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json
import os

# --- 設定網頁標題與版面 ---
st.set_page_config(page_title="我的資產儀表板", layout="wide")
st.title("💰 媽媽狩獵者 的資產儀表板")

# --- [新增功能] 讀取與寫入設定檔 ---
DATA_FILE = "cash_data.json"

def load_cash_settings():
    """從檔案讀取現金設定，如果檔案不存在則回傳預設值"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"twd": 50000, "usd": 1000}

def save_cash_settings(twd, usd):
    """將目前的現金設定寫入檔案"""
    with open(DATA_FILE, "w") as f:
        json.dump({"twd": twd, "usd": usd}, f)

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

# --- 2. 側邊欄：具備記憶功能的輸入框 ---
st.sidebar.header("💵 現金資產設定")

# A. 先讀取上次的紀錄
saved_data = load_cash_settings()

# B. 建立輸入框
cash_twd = st.sidebar.number_input("台幣現金餘額 (TWD)", value=saved_data["twd"], step=10000)
cash_usd = st.sidebar.number_input("美金現金餘額 (USD)", value=saved_data["usd"], step=100)

# C. 檢查並存檔
if cash_twd != saved_data["twd"] or cash_usd != saved_data["usd"]:
    save_cash_settings(cash_twd, cash_usd)

# --- 3. 核心計算函數 ---
@st.cache_data(ttl=300) 
def get_data_and_calculate():
    try:
        usdtwd = yf.Ticker("USDTWD=X").history(period="1d")['Close'].iloc[-1]
    except:
        usdtwd = 32.5 
        
    data_list = []
    
    # --- 處理台股 ---
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

    # --- 處理美股 ---
    for item in us_portfolio:
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
            
    return pd.DataFrame(data_list), usdtwd

# --- 4. 樣式設定函數 (紅漲綠跌) ---
def color_tw_style(val):
    if isinstance(val, (int, float)):
        if val > 0:
            return 'color: #FF4B4B; font-weight: bold'  # 紅色
        elif val < 0:
            return 'color: #00C853; font-weight: bold'  # 綠色
    return ''

# --- 5. 執行與計算 ---
st.write("🔄 正在取得最新報價...")
df, rate = get_data_and_calculate()

stock_total = df['市值'].sum()
cash_total = cash_twd + (cash_usd * rate)
total_assets = stock_total + cash_total 

total_profit = df['總損益'].sum() 
total_return_rate = (total_profit / (stock_total - total_profit)) * 100 if stock_total != 0 else 0

today_change_total = df['今日損益'].sum()
today_change_pct = (today_change_total / (stock_total - today_change_total)) * 100 if stock_total != 0 else 0

df['佔比%'] = (df['市值'] / total_assets) * 100

# --- 6. 顯示上方大數據 ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏆 總資產 (TWD)", f"${total_assets:,.0f}")
col2.metric("💰 總獲利 (TWD)", f"${total_profit:,.0f}", delta=f"{total_return_rate:.2f}%")
col3.metric("📅 今日變動 (TWD)", f"${today_change_total:,.0f}", delta=f"{today_change_pct:.2f}%")
col4.metric("💵 現金部位 (TWD)", f"${cash_total:,.0f}")

st.caption(f"註：美股損益已自動依匯率 (1:{rate:.2f}) 換算為台幣。")
st.divider()

# --- 7. 圖表與詳細表格 ---
col_chart, col_table = st.columns([0.35, 0.65])

with col_chart:
    st.subheader("📊 資產配置 (含現金)")
    chart_df = df[['代號', '市值']].copy()
    if cash_total > 0:
        new_row = pd.DataFrame([{'代號': '現金 (Cash)', '市值': cash_total}])
        chart_df = pd.concat([chart_df, new_row], ignore_index=True)
    
    fig = px.pie(chart_df, values='市值', names='代號', hole=0.4, 
                 title=f"總資產: ${total_assets:,.0f}")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.subheader("📋 持股詳細行情")
    display_df = df[['代號', '現價', '漲跌', '幅度%', '今日損益', '佔比%', '總報酬%', '總損益']].copy()
    styled_df = display_df.style.map(color_tw_style, subset=['漲跌', '幅度%', '今日損益', '總報酬%', '總損益']) \
        .format({
            '現價': '{:.2f}',
            '漲跌': '{:+.2f}',
            '幅度%': '{:+.2f}%',
            '今日損益': '${:,.0f}',
            '佔比%': '{:.1f}%',       
            '總報酬%': '{:+.2f}%',
            '總損益': '${:,.0f}'
        })

    st.dataframe(
        styled_df,
        height=500,
        use_container_width=True,
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
