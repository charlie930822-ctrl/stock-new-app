import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime, time
import pytz 

# --- 設定網頁標題與版面 ---
st.set_page_config(page_title="我的資產儀表板", layout="wide")
st.title("💰 媽媽狩獵者 的資產儀表板")

# --- [功能] 讀取與寫入設定檔 ---
DATA_FILE = "cash_data.json"

def load_settings():
    # 預設值
    default_data = {
        "twd_bank": 48492, "twd_physical": 0, "twd_max": 0, "usd": 1900,
        "btc": 0.00887095, "btc_cost": 85460.87,
        "eth": 0.0536, "eth_cost": 2960.53,
        "sol": 4.209, "sol_cost": 130.0,
        # [已實現損益]
        "realized_profit_twd": 0.0,       # 台股 (TWD)
        "realized_profit_us_stock": 0.0,  # 美股 (USD)
        "realized_profit_crypto": 0.0     # 加密貨幣 (USD)
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
    with open(DATA_FILE, "w") as f:
        json.dump(data_dict, f)

# --- 1. 設定持股資料 ---
tw_portfolio = [
    {'code': '2317.TW', 'name': '鴻海', 'shares': 252, 'cost': 166.84},
    {'code': '2330.TW', 'name': '台積電', 'shares': 44, 'cost': 1013.12},
]

us_portfolio = [
    {'code': 'GRAB', 'shares': 50, 'cost': 5.125},
    {'code': 'NFLX', 'shares': 10.33591, 'cost': 96.75007},
    {'code': 'NVDA', 'shares': 8.93654, 'cost': 173.48549},
    {'code': 'PLTR', 'shares': 2.2357, 'cost': 148.96006},
    {'code': 'SOFI', 'shares': 51.523, 'cost': 26.68769	},
    {'code': 'ORCL', 'shares': 2.98072, 'cost': 182.04},
    {'code': 'TSLA', 'shares': 5.09479, 'cost': 423.040823}, 
]

# --- 2. 側邊欄設定 ---
st.sidebar.header("⚙️ 資產設定")
saved_data = load_settings()

# [已實現損益輸入區]
with st.sidebar.expander("💰 已實現損益 (落袋為安)", expanded=True):
    realized_twd = st.number_input(
        "🇹🇼 台股已實現獲利 (TWD)", 
        value=float(saved_data.get("realized_profit_twd", 3455)), 
        step=100.0,
        help="輸入台股券商顯示的已實現損益 (例如: 3455)"
    )
    
    realized_us_stock = st.number_input(
        "🇺🇸 美股已實現獲利 (USD)", 
        value=float(saved_data.get("realized_profit_us_stock", 14.63)), 
        step=10.0,
        help="輸入美股券商顯示的 Realized P/L (例如: 50.5)"
    )
    
    realized_crypto = st.number_input(
        "🪙 加密貨幣已實現獲利 (USD)", 
        value=float(saved_data.get("realized_profit_crypto", 0.0)), 
        step=10.0,
        help="輸入交易所顯示的 Realized P/L (例如: 120)"
    )

st.sidebar.subheader("💵 法幣現金")
cash_twd_bank = st.sidebar.number_input("🏦 銀行存款 (TWD)", value=float(saved_data.get("twd_bank", 50000)), step=10000.0)
cash_twd_physical = st.sidebar.number_input("🧧 實體現鈔 (TWD)", value=float(saved_data.get("twd_physical", 0)), step=1000.0)
cash_twd_max = st.sidebar.number_input("🟣 MAX 交易所 (TWD)", value=float(saved_data.get("twd_max", 0)), step=1000.0)
cash_usd = st.sidebar.number_input("🇺🇸 美金 (USD)", value=float(saved_data["usd"]), step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 加密貨幣設定")
c1, c2 = st.sidebar.columns(2)
btc_qty = c1.number_input("BTC 顆數", value=float(saved_data["btc"]), step=0.00000001, format="%.8f")
btc_cost = c2.number_input("BTC 均價(USD)", value=float(saved_data.get("btc_cost", 0.0)), step=100.0, format="%.2f")

c3, c4 = st.sidebar.columns(2)
eth_qty = c3.number_input("ETH 顆數", value=float(saved_data["eth"]), step=0.00000001, format="%.8f")
eth_cost = c4.number_input("ETH 均價(USD)", value=float(saved_data.get("eth_cost", 0.0)), step=10.0, format="%.2f")

c5, c6 = st.sidebar.columns(2)
sol_qty = c5.number_input("SOL 顆數", value=float(saved_data["sol"]), step=0.00000001, format="%.8f")
sol_cost = c6.number_input("SOL 均價(USD)", value=float(saved_data.get("sol_cost", 0.0)), step=1.0, format="%.2f")

# 存檔邏輯
current_data = {
    "twd_bank": cash_twd_bank, "twd_physical": cash_twd_physical, "twd_max": cash_twd_max, "usd": cash_usd,
    "btc": btc_qty, "btc_cost": btc_cost, "eth": eth_qty, "eth_cost": eth_cost, "sol": sol_qty, "sol_cost": sol_cost,
    "realized_profit_twd": realized_twd,
    "realized_profit_us_stock": realized_us_stock,
    "realized_profit_crypto": realized_crypto
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
    
    tw_tz = pytz.timezone('Asia/Taipei')
    now_tw = datetime.now(tw_tz)
    today_tw_str = now_tw.strftime('%Y-%m-%d')
    
    is_tw_market_active = time(9, 0) <= now_tw.time() <= time(14, 30)
    is_us_market_active = (now_tw.time() >= time(21, 0)) or (now_tw.time() <= time(5, 0))

    # 台股
    for item in tw_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            hist = hist.dropna()
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                last_dt = hist.index[-1]
                if last_dt.tzinfo is None:
                    last_dt = tw_tz.localize(last_dt)
                else:
                    last_dt = last_dt.astimezone(tw_tz)
                data_date_str = last_dt.strftime('%Y-%m-%d')
                include_in_daily = (data_date_str == today_tw_str) or is_tw_market_active
                if len(hist) >= 2:
                    change_price = price - hist['Close'].iloc[-2]
                    change_pct = (change_price / hist['Close'].iloc[-2]) * 100
                else:
                    change_price = 0; change_pct = 0

                market_val = price * item['shares']
                cost_val = item['cost'] * item['shares']
                profit = market_val - cost_val
                profit_pct = (profit / cost_val) * 100 if cost_val != 0 else 0
                
                data_list.append({
                    "代號": item['name'], "類型": "台股", "現價": price, "漲跌": change_price,
                    "幅度%": change_pct, "今日損益": change_price * item['shares'],
                    "市值": market_val, "總損益": profit, "總報酬%": profit_pct, "include_in_daily": include_in_daily
                })
        except: pass

    # 美股
    for item in us_portfolio:
        try:
            ticker = yf.Ticker(item['code'])
            hist = ticker.history(period="5d")
            hist = hist.dropna()
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                last_dt = hist.index[-1]
                if last_dt.tzinfo is None:
                    last_dt = tw_tz.localize(last_dt) 
                else:
                    last_dt = last_dt.astimezone(tw_tz)
                data_date_str = last_dt.strftime('%Y-%m-%d')
                include_in_daily = (data_date_str == today_tw_str) or is_us_market_active
                if len(hist) >= 2:
                    change_price = price - hist['Close'].iloc[-2]
                    change_pct = (change_price / hist['Close'].iloc[-2]) * 100
                else:
                    change_price = 0; change_pct = 0
                
                market_val_usd = price * item['shares']
                cost_val_usd = item['cost'] * item['shares']
                profit_usd = market_val_usd - cost_val_usd
                profit_pct = (profit_usd / cost_val_usd) * 100 if cost_val_usd != 0 else 0
                
                data_list.append({
                    "代號": item['code'], "類型": "美股", "現價": price, "漲跌": change_price,        
                    "幅度%": change_pct, "今日損益": (change_price * item['shares']) * usdtwd,
                    "市值": market_val_usd * usdtwd, "總損益": profit_usd * usdtwd,
                    "總報酬%": profit_pct, "include_in_daily": include_in_daily
                })
        except: pass

    # 加密貨幣
    crypto_map = {
        'BTC-USD': {'name': 'BTC', 'qty': btc_d['qty'], 'cost': btc_d['cost']},
        'ETH-USD': {'name': 'ETH', 'qty': eth_d['qty'], 'cost': eth_d['cost']},
        'SOL-USD': {'name': 'SOL', 'qty': sol_d['qty'], 'cost': sol_d['cost']}
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
                        change_usd = price_usd - hist['Close'].iloc[-2]
                        change_pct = (change_usd / hist['Close'].iloc[-2]) * 100
                    else:
                        change_usd = 0; change_pct = 0
                    
                    market_val_usd = price_usd * info['qty']
                    cost_val_usd = info['cost'] * info['qty']
                    profit_usd = market_val_usd - cost_val_usd
                    profit_pct = (profit_usd / cost_val_usd * 100) if cost_val_usd > 0 else 0
                    
                    data_list.append({
                        "代號": info['name'], "類型": "Crypto", "現價": price_usd, "漲跌": change_usd,
                        "幅度%": change_pct, "今日損益": (change_usd * info['qty']) * usdtwd,
                        "市值": market_val_usd * usdtwd, "總損益": profit_usd * usdtwd, 
                        "總報酬%": profit_pct, "include_in_daily": True 
                    })
            except: pass
            
    return pd.DataFrame(data_list), usdtwd

# --- 4. 樣式 ---
def color_tw_style(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #FF4B4B; font-weight: bold'
        elif val < 0: return 'color: #00C853; font-weight: bold'
        elif val == 0: return 'color: white; opacity: 0.5'
    return ''

# --- 5. 執行與計算 ---
st.write("🔄 正在取得最新報價 (含加密貨幣)...")
btc_data = {'qty': btc_qty, 'cost': btc_cost}
eth_data = {'qty': eth_qty, 'cost': eth_cost}
sol_data = {'qty': sol_qty, 'cost': sol_cost}

df, rate = get_data_and_calculate(btc_data, eth_data, sol_data)

# 分類數據
crypto_df = df[df['類型'] == 'Crypto']
stock_df = df[df['類型'] != 'Crypto']
crypto_total_val = crypto_df['市值'].sum() if not crypto_df.empty else 0
stock_total_val = stock_df['市值'].sum() if not stock_df.empty else 0

total_cash_twd_only = cash_twd_bank + cash_twd_physical + cash_twd_max
cash_total_val = total_cash_twd_only + (cash_usd * rate)
invested_assets = stock_total_val + crypto_total_val
total_assets = stock_total_val + crypto_total_val + cash_total_val

# --- [關鍵計算升級] 總獲利分類計算 ---
# 1. 計算各市場的「帳面損益 (Unrealized)」(從 df 抓)
unrealized_tw = df[df['類型'] == '台股']['總損益'].sum()
unrealized_us = df[df['類型'] == '美股']['總損益'].sum()
unrealized_crypto = df[df['類型'] == 'Crypto']['總損益'].sum()

# 2. 計算各市場的「總獲利 (Total)」= 帳面 + 已實現
# 注意：美股和幣圈的已實現是 USD，要乘匯率
profit_tw_total = unrealized_tw + realized_twd
profit_us_total = unrealized_us + (realized_us_stock * rate)
profit_crypto_total = unrealized_crypto + (realized_crypto * rate)

# 3. 整體總獲利
total_profit = profit_tw_total + profit_us_total + profit_crypto_total

# 報酬率計算 (還原成本法)
total_realized_twd = realized_twd + ((realized_us_stock + realized_crypto) * rate)
invested_capital = (stock_total_val + crypto_total_val + total_realized_twd) - total_profit
total_return_rate = 0 
if invested_capital > 0:
    total_return_rate = (total_profit / invested_capital) * 100

today_change_total = df[df['include_in_daily'] == True]['今日損益'].sum()
today_change_pct = (today_change_total / total_assets) * 100 if total_assets != 0 else 0

df['佔比%'] = (df['市值'] / total_assets) * 100

# --- 6. 顯示指標 (第一排：總覽) ---
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("🏆 總資產", f"${total_assets:,.0f}")
col2.metric("📈 投資總資產", f"${invested_assets:,.0f}")
col3.metric("💰 整體總獲利", f"${total_profit:,.0f}", delta=f"{total_return_rate:.2f}%")
col4.metric("📅 今日變動", f"${today_change_total:,.0f}", delta=f"{today_change_pct:.2f}%")
col5.metric("💵 現金部位", f"${cash_total_val:,.0f}")
col6.metric("🪙 加密市值", f"${crypto_total_val:,.0f}")

# --- [新功能] 顯示獲利細項 (第二排：各市場獲利) ---
st.markdown("### 📊 獲利貢獻分析 (含已實現)")
sub_c1, sub_c2, sub_c3 = st.columns(3)
sub_c1.metric("🇹🇼 台股總獲利", f"${profit_tw_total:,.0f}", help=f"帳面: ${unrealized_tw:,.0f} + 已實現: ${realized_twd:,.0f}")
sub_c2.metric("🇺🇸 美股總獲利", f"${profit_us_total:,.0f}", help=f"帳面: ${unrealized_us:,.0f} + 已實現: ${(realized_us_stock * rate):,.0f} (TWD)")
sub_c3.metric("🪙 幣圈總獲利", f"${profit_crypto_total:,.0f}", help=f"帳面: ${unrealized_crypto:,.0f} + 已實現: ${(realized_crypto * rate):,.0f} (TWD)")

st.caption(f"註：美股與幣圈已自動依匯率 (1:{rate:.2f}) 換算台幣。")
st.divider()

# --- 7. 圖表與表格 ---
col_chart, col_table = st.columns([0.35, 0.65])
with col_chart:
    st.subheader("📊 資產配置")
    chart_df = df[['代號', '市值']].copy()
    if cash_twd_bank > 0: chart_df = pd.concat([chart_df, pd.DataFrame([{'代號': '銀行存款', '市值': cash_twd_bank}])], ignore_index=True)
    if cash_twd_physical > 0: chart_df = pd.concat([chart_df, pd.DataFrame([{'代號': '實體現鈔', '市值': cash_twd_physical}])], ignore_index=True)
    if cash_twd_max > 0: chart_df = pd.concat([chart_df, pd.DataFrame([{'代號': 'MAX 交易所', '市值': cash_twd_max}])], ignore_index=True)
    if cash_usd > 0: chart_df = pd.concat([chart_df, pd.DataFrame([{'代號': '美金存款', '市值': cash_usd * rate}])], ignore_index=True)
    fig = px.pie(chart_df, values='市值', names='代號', hole=0.4, title=f"總資產: ${total_assets:,.0f}")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.subheader("📋 持股與幣圈詳細行情")
    display_df = df[['代號', '類型', '現價', '漲跌', '幅度%', '市值', '佔比%', '今日損益', '總報酬%', '總損益']].copy()
    styled_df = display_df.style.map(color_tw_style, subset=['漲跌', '幅度%', '今日損益', '總報酬%', '總損益']).format({
            '現價': '{:.2f}', '漲跌': '{:+.2f}', '幅度%': '{:+.2f}%', '市值': '${:,.0f}',
            '今日損益': '${:,.0f}', '佔比%': '{:.1f}%', '總報酬%': '{:+.2f}%', '總損益': '${:,.0f}' 
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
