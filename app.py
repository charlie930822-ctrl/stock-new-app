import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime
import pytz

# =========================
# 0) Streamlit 基本設定
# =========================
st.set_page_config(page_title="我的資產儀表板", layout="wide")
st.title("💰 媽媽狩獵者 的資產儀表板")

DATA_FILE = "cash_data.json"

# =========================
# 1) 讀寫設定（側邊欄數值）
# =========================
def load_settings():
    default_data = {
        "twd_bank": 68334, "twd_physical": 0, "twd_max": 0, "usd": 544.16,
        "btc": 0.012498, "btc_cost": 79905.3,
        "eth": 0.0536, "eth_cost": 2961.40,
        "sol": 4.209, "sol_cost": 131.0,
        "realized_profit_twd": 0.0,       # 台股 (TWD)
        "realized_profit_us_stock": 0.0,  # 美股 (USD)
        "realized_profit_crypto": 0.0     # 幣圈 (USD)
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**default_data, **saved}
        except:
            return default_data
    return default_data

def save_settings(data_dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=2)

# =========================
# 2) 你的持股（先留硬編碼）
#    之後要做成檔案匯入也可以再升級
# =========================
tw_portfolio = [
    {"code": "2317.TW", "name": "鴻海", "shares": 160, "cost": 166.84},
    {"code": "2330.TW", "name": "台積電", "shares": 44, "cost": 1013.12},
]
us_portfolio = [
    {"code": "GRAB", "shares": 50, "cost": 5.125},
    {"code": "NFLX", "shares": 10.33591, "cost": 96.75007},
    {"code": "NVDA", "shares": 9.78414, "cost": 173.7884},
    {"code": "PLTR", "shares": 2.2357, "cost": 148.96006},
    {"code": "SOFI", "shares": 80.3943, "cost": 24.419},
    {"code": "ORCL", "shares": 4.20742, "cost": 169.68324},
    {"code": "QQQI", "shares": 9, "cost": 52.3771},
    {"code": "TSLA", "shares": 5.09479, "cost": 423.040823},
]

# =========================
# 3) 側邊欄 UI
# =========================
st.sidebar.header("⚙️ 資產設定")
saved_data = load_settings()

with st.sidebar.expander("💰 已實現損益 (落袋為安)", expanded=True):
    realized_twd = st.number_input(
        "🇹🇼 台股已實現獲利 (TWD)",
        value=float(saved_data.get("realized_profit_twd", 0.0)),
        step=100.0
    )
    realized_us_stock = st.number_input(
        "🇺🇸 美股已實現獲利 (USD)",
        value=float(saved_data.get("realized_profit_us_stock", 0.0)),
        step=10.0
    )
    realized_crypto = st.number_input(
        "🪙 加密貨幣已實現獲利 (USD)",
        value=float(saved_data.get("realized_profit_crypto", 0.0)),
        step=10.0
    )

st.sidebar.subheader("💵 法幣現金")
cash_twd_bank = st.sidebar.number_input("🏦 銀行存款 (TWD)", value=float(saved_data.get("twd_bank", 0)), step=10000.0)
cash_twd_physical = st.sidebar.number_input("🧧 實體現鈔 (TWD)", value=float(saved_data.get("twd_physical", 0)), step=1000.0)
cash_twd_max = st.sidebar.number_input("🟣 MAX 交易所 (TWD)", value=float(saved_data.get("twd_max", 0)), step=1000.0)
cash_usd = st.sidebar.number_input("🇺🇸 美金 (USD)", value=float(saved_data.get("usd", 0)), step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 加密貨幣持倉")
c1, c2 = st.sidebar.columns(2)
btc_qty = c1.number_input("BTC 顆數", value=float(saved_data.get("btc", 0)), step=0.00000001, format="%.8f")
btc_cost = c2.number_input("BTC 均價(USD)", value=float(saved_data.get("btc_cost", 0.0)), step=100.0, format="%.2f")

c3, c4 = st.sidebar.columns(2)
eth_qty = c3.number_input("ETH 顆數", value=float(saved_data.get("eth", 0)), step=0.00000001, format="%.8f")
eth_cost = c4.number_input("ETH 均價(USD)", value=float(saved_data.get("eth_cost", 0.0)), step=10.0, format="%.2f")

c5, c6 = st.sidebar.columns(2)
sol_qty = c5.number_input("SOL 顆數", value=float(saved_data.get("sol", 0)), step=0.00000001, format="%.8f")
sol_cost = c6.number_input("SOL 均價(USD)", value=float(saved_data.get("sol_cost", 0.0)), step=1.0, format="%.2f")

# 存檔（避免一直寫入）
current_data = {
    "twd_bank": cash_twd_bank, "twd_physical": cash_twd_physical, "twd_max": cash_twd_max, "usd": cash_usd,
    "btc": btc_qty, "btc_cost": btc_cost, "eth": eth_qty, "eth_cost": eth_cost, "sol": sol_qty, "sol_cost": sol_cost,
    "realized_profit_twd": realized_twd,
    "realized_profit_us_stock": realized_us_stock,
    "realized_profit_crypto": realized_crypto
}
if current_data != saved_data:
    save_settings(current_data)

# =========================
# 4) 工具：抓匯率（USD/TWD）
# =========================
@st.cache_data(ttl=60)
def get_usdtwd():
    # yfinance 有時候代碼會失效，這裡做 fallback
    candidates = ["TWD=X", "USDTWD=X"]  # 先試 USD/TWD，再試 USDTWD
    for c in candidates:
        try:
            s = yf.download(c, period="5d", interval="1d", progress=False)["Close"].dropna()
            if len(s) > 0:
                return float(s.iloc[-1]), c
        except:
            pass
    return 32.5, "fallback(32.5)"

# =========================
# 5) 核心：一次抓一批價格 + 算損益
# =========================
@st.cache_data(ttl=30)
def build_positions_df(tw_portfolio, us_portfolio, crypto_inputs):
    errors = []

    rate, rate_src = get_usdtwd()

    # 代碼整理
    tw_codes = [x["code"] for x in tw_portfolio]
    us_codes = [x["code"] for x in us_portfolio]
    crypto_codes = list(crypto_inputs.keys())  # e.g. BTC-USD, ETH-USD...

    # 一次抓一批（分三次，因為市場不同也沒差）
    def fetch_last_two_closes(codes):
        if not codes:
            return {}
        try:
            df = yf.download(codes, period="10d", interval="1d", group_by="ticker", progress=False)
            # 單一代碼時 df["Close"] 會是一個 Series；多代碼是 DataFrame
            close = df["Close"].dropna(how="all")
            out = {}

            if isinstance(close, pd.Series):
                # 單一 ticker
                if close.dropna().shape[0] >= 2:
                    out[codes[0]] = (float(close.iloc[-1]), float(close.iloc[-2]))
                elif close.dropna().shape[0] == 1:
                    out[codes[0]] = (float(close.iloc[-1]), float(close.iloc[-1]))
                return out

            # 多 ticker
            for code in close.columns:
                s = close[code].dropna()
                if s.shape[0] >= 2:
                    out[code] = (float(s.iloc[-1]), float(s.iloc[-2]))
                elif s.shape[0] == 1:
                    out[code] = (float(s.iloc[-1]), float(s.iloc[-1]))
            return out
        except Exception as e:
            errors.append(f"下載失敗：{codes} / {e}")
            return {}

    tw_prices = fetch_last_two_closes(tw_codes)
    us_prices = fetch_last_two_closes(us_codes)
    crypto_prices = fetch_last_two_closes(crypto_codes)

    rows = []

    # 台股：以 TWD 計價
    for it in tw_portfolio:
        code = it["code"]
        if code not in tw_prices:
            errors.append(f"台股抓不到：{code}")
            continue
        last_close, prev_close = tw_prices[code]
        price = last_close
        change = last_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0

        market_val = price * it["shares"]
        cost_val = it["cost"] * it["shares"]
        unreal = market_val - cost_val
        unreal_pct = (unreal / cost_val * 100) if cost_val != 0 else 0

        rows.append({
            "代號": it["name"],
            "類型": "台股",
            "幣別": "TWD",
            "現價": price,
            "漲跌": change,
            "幅度%": change_pct,
            "今日損益": change * it["shares"],   # 台股：今日=最新收盤對前一日
            "市值(TWD)": market_val,
            "未實現損益(TWD)": unreal,
            "未實現報酬%": unreal_pct,
        })

    # 美股：以 USD 計價，但我們統一換算到 TWD 顯示市值/損益
    for it in us_portfolio:
        code = it["code"]
        if code not in us_prices:
            errors.append(f"美股抓不到：{code}")
            continue
        last_close, prev_close = us_prices[code]
        price_usd = last_close
        change_usd = last_close - prev_close
        change_pct = (change_usd / prev_close * 100) if prev_close != 0 else 0

        mv_usd = price_usd * it["shares"]
        cost_usd = it["cost"] * it["shares"]
        unreal_usd = mv_usd - cost_usd
        unreal_pct = (unreal_usd / cost_usd * 100) if cost_usd != 0 else 0

        rows.append({
            "代號": code,
            "類型": "美股",
            "幣別": "USD",
            "現價": price_usd,
            "漲跌": change_usd,
            "幅度%": change_pct,
            "今日損益": (change_usd * it["shares"]) * rate,   # 換成 TWD
            "市值(TWD)": mv_usd * rate,
            "未實現損益(TWD)": unreal_usd * rate,
            "未實現報酬%": unreal_pct,
        })

    # 幣圈：用「最近兩天 close」近似 24h（比較直覺）
    for code, info in crypto_inputs.items():
        qty = info["qty"]
        cost = info["cost"]
        if qty <= 0:
            continue
        if code not in crypto_prices:
            errors.append(f"幣圈抓不到：{code}")
            continue
        last_close, prev_close = crypto_prices[code]
        price_usd = last_close
        change_usd = last_close - prev_close
        change_pct = (change_usd / prev_close * 100) if prev_close != 0 else 0

        mv_usd = price_usd * qty
        cost_usd = cost * qty
        unreal_usd = mv_usd - cost_usd
        unreal_pct = (unreal_usd / cost_usd * 100) if cost_usd != 0 else 0

        name = code.replace("-USD", "")
        rows.append({
            "代號": name,
            "類型": "Crypto(24h)",
            "幣別": "USD",
            "現價": price_usd,
            "漲跌": change_usd,
            "幅度%": change_pct,
            "今日損益": (change_usd * qty) * rate,  # 這裡其實是 24h 變動(用日K近似)
            "市值(TWD)": mv_usd * rate,
            "未實現損益(TWD)": unreal_usd * rate,
            "未實現報酬%": unreal_pct,
        })

    df = pd.DataFrame(rows)
    return df, rate, rate_src, errors

# =========================
# 6) 執行：計算
# =========================
st.write("🔄 正在取得最新報價...")

crypto_inputs = {
    "BTC-USD": {"qty": btc_qty, "cost": btc_cost},
    "ETH-USD": {"qty": eth_qty, "cost": eth_cost},
    "SOL-USD": {"qty": sol_qty, "cost": sol_cost},
}

df, rate, rate_src, errors = build_positions_df(tw_portfolio, us_portfolio, crypto_inputs)

# 現金換算
total_cash_twd = cash_twd_bank + cash_twd_physical + cash_twd_max + (cash_usd * rate)

# 總市值
stock_crypto_total = float(df["市值(TWD)"].sum()) if not df.empty else 0.0
total_assets = stock_crypto_total + total_cash_twd

# 未實現
unrealized_tw = float(df[df["類型"] == "台股"]["未實現損益(TWD)"].sum()) if not df.empty else 0.0
unrealized_us = float(df[df["類型"] == "美股"]["未實現損益(TWD)"].sum()) if not df.empty else 0.0
unrealized_crypto = float(df[df["類型"].str.contains("Crypto")]["未實現損益(TWD)"].sum()) if not df.empty else 0.0

# 已實現（USD -> TWD）
realized_tw_twd = float(realized_twd)
realized_us_twd = float(realized_us_stock) * rate
realized_crypto_twd = float(realized_crypto) * rate

profit_tw_total = unrealized_tw + realized_tw_twd
profit_us_total = unrealized_us + realized_us_twd
profit_crypto_total = unrealized_crypto + realized_crypto_twd
total_profit = profit_tw_total + profit_us_total + profit_crypto_total

# 近似投入本金（你原本的做法保留，但我會在 UI 上標示「近似」）
total_invested_capital = total_assets - total_profit
total_return_rate = (total_profit / total_invested_capital * 100) if total_invested_capital > 0 else 0

today_change_total = float(df["今日損益"].sum()) if not df.empty else 0.0
today_change_pct = (today_change_total / total_assets * 100) if total_assets != 0 else 0

# 佔比
if not df.empty and total_assets > 0:
    df["佔比%"] = df["市值(TWD)"] / total_assets * 100
else:
    df["佔比%"] = 0.0

# =========================
# 7) 顯示指標
# =========================
col1, col2, col3, col4 = st.columns(4)
col1.metric("🏆 總資產(TWD)", f"${total_assets:,.0f}")
col2.metric("💰 總獲利(含已實現)", f"${total_profit:,.0f}", delta=f"{total_return_rate:.2f}% (近似)")
col3.metric("📅 今日/24h 變動(TWD)", f"${today_change_total:,.0f}", delta=f"{today_change_pct:.2f}%")
col4.metric("💱 USD/TWD", f"{rate:.2f}", delta=rate_src)

st.markdown("---")

# =========================
# 8) 損益結構拆解
# =========================
st.subheader("📊 損益結構分析 (TWD)")
a, b, c = st.columns(3)
with a:
    st.info(f"**🇹🇼 台股總損益**\n\n### ${profit_tw_total:,.0f}")
    st.write(f"- 未實現：${unrealized_tw:,.0f}")
    st.write(f"- 已實現：${realized_tw_twd:,.0f}")
with b:
    st.info(f"**🇺🇸 美股總損益**\n\n### ${profit_us_total:,.0f}")
    st.write(f"- 未實現：${unrealized_us:,.0f}")
    st.write(f"- 已實現：${realized_us_twd:,.0f}")
with c:
    st.info(f"**🪙 幣圈總損益**\n\n### ${profit_crypto_total:,.0f}")
    st.write(f"- 未實現：${unrealized_crypto:,.0f}")
    st.write(f"- 已實現：${realized_crypto_twd:,.0f}")

st.divider()

# =========================
# 9) 圓餅圖 + 明細表
# =========================
left, right = st.columns([0.35, 0.65])

with left:
    st.subheader("🍰 資產配置圓餅圖")
    chart_rows = []
    if not df.empty:
        for _, r in df.iterrows():
            chart_rows.append({"項目": r["代號"], "市值": r["市值(TWD)"]})
    # 現金拆開顯示
    if cash_twd_bank > 0: chart_rows.append({"項目": "銀行存款", "市值": cash_twd_bank})
    if cash_twd_physical > 0: chart_rows.append({"項目": "實體現鈔", "市值": cash_twd_physical})
    if cash_twd_max > 0: chart_rows.append({"項目": "MAX 交易所", "市值": cash_twd_max})
    if cash_usd > 0: chart_rows.append({"項目": "美金存款(折台)", "市值": cash_usd * rate})

    chart_df = pd.DataFrame(chart_rows)
    if not chart_df.empty:
        fig = px.pie(chart_df, values="市值", names="項目", hole=0.4, title=f"總資產: ${total_assets:,.0f} TWD")
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("目前沒有可顯示的資產。")

with right:
    st.subheader("📋 持倉詳細行情（市值/損益以 TWD 統一）")
    if df.empty:
        st.warning("沒有抓到任何行情資料（可能是網路或代碼問題）。")
    else:
        display = df[[
            "代號", "類型", "幣別", "現價", "漲跌", "幅度%", "市值(TWD)", "佔比%", "今日損益", "未實現報酬%", "未實現損益(TWD)"
        ]].copy()

        def color_style(val):
            if isinstance(val, (int, float)):
                if val > 0: return "color: #FF4B4B; font-weight: bold"
                if val < 0: return "color: #00C853; font-weight: bold"
                return "color: gray"
            return ""

        styled = (
            display.style
            .map(color_style, subset=["漲跌", "幅度%", "今日損益", "未實現報酬%", "未實現損益(TWD)"])
            .format({
                "現價": "{:.2f}",
                "漲跌": "{:+.2f}",
                "幅度%": "{:+.2f}%",
                "市值(TWD)": "${:,.0f}",
                "今日損益": "${:,.0f}",
                "佔比%": "{:.1f}%",
                "未實現報酬%": "{:+.2f}%",
                "未實現損益(TWD)": "${:,.0f}",
            })
        )
        st.dataframe(styled, use_container_width=True, height=520, hide_index=True)

# =========================
# 10) 顯示抓價錯誤（不再偷偷吞掉）
# =========================
if errors:
    with st.expander("⚠️ 抓價/資料警告（點開看哪些代碼抓不到）", expanded=False):
        for e in errors:
            st.write("-", e)
