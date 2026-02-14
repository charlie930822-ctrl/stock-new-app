import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json, os

# =========================
# 0) Streamlit 基本設定
# =========================
st.set_page_config(page_title="我的資產儀表板", layout="wide")
st.title("💰 媽媽狩獵者 的資產儀表板")

DATA_FILE = "cash_data.json"

# =========================
# 1) 讀寫設定
# =========================
def load_settings():
default_data = {
        "twd_bank": 68334, "twd_physical": 0, "twd_max": 0, "usd": 544.16,
        "btc": 0.012498, "btc_cost": 79905.3,
        "eth": 0.0536, "eth_cost": 2961.40,
        "sol": 4.209, "sol_cost": 131.0,
        "realized_profit_twd": 0.0,
        "realized_profit_us_stock": 0.0,
        "realized_profit_crypto": 0.0
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**default_data, **saved}
        except:
            return default_data
    return default_data

def save_settings(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# =========================
# 2) 你的持股（先保留硬編碼）
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
# 3) 側邊欄
# =========================
st.sidebar.header("⚙️ 資產設定")
saved = load_settings()

with st.sidebar.expander("💰 已實現損益 (落袋為安)", expanded=True):
    realized_twd = st.number_input("🇹🇼 台股已實現獲利 (TWD)", value=float(saved.get("realized_profit_twd", 0.0)), step=100.0)
    realized_us_stock = st.number_input("🇺🇸 美股已實現獲利 (USD)", value=float(saved.get("realized_profit_us_stock", 0.0)), step=10.0)
    realized_crypto = st.number_input("🪙 加密貨幣已實現獲利 (USD)", value=float(saved.get("realized_profit_crypto", 0.0)), step=10.0)

st.sidebar.subheader("💵 法幣現金")
cash_twd_bank = st.sidebar.number_input("🏦 銀行存款 (TWD)", value=float(saved.get("twd_bank", 0.0)), step=10000.0)
cash_twd_physical = st.sidebar.number_input("🧧 實體現鈔 (TWD)", value=float(saved.get("twd_physical", 0.0)), step=1000.0)
cash_twd_max = st.sidebar.number_input("🟣 MAX 交易所 (TWD)", value=float(saved.get("twd_max", 0.0)), step=1000.0)
cash_usd = st.sidebar.number_input("🇺🇸 美金 (USD)", value=float(saved.get("usd", 0.0)), step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 加密貨幣持倉")
c1, c2 = st.sidebar.columns(2)
btc_qty = c1.number_input("BTC 顆數", value=float(saved.get("btc", 0.0)), step=0.00000001, format="%.8f")
btc_cost = c2.number_input("BTC 均價(USD)", value=float(saved.get("btc_cost", 0.0)), step=100.0, format="%.2f")

c3, c4 = st.sidebar.columns(2)
eth_qty = c3.number_input("ETH 顆數", value=float(saved.get("eth", 0.0)), step=0.00000001, format="%.8f")
eth_cost = c4.number_input("ETH 均價(USD)", value=float(saved.get("eth_cost", 0.0)), step=10.0, format="%.2f")

c5, c6 = st.sidebar.columns(2)
sol_qty = c5.number_input("SOL 顆數", value=float(saved.get("sol", 0.0)), step=0.00000001, format="%.8f")
sol_cost = c6.number_input("SOL 均價(USD)", value=float(saved.get("sol_cost", 0.0)), step=1.0, format="%.2f")

current = {
    "twd_bank": cash_twd_bank, "twd_physical": cash_twd_physical, "twd_max": cash_twd_max, "usd": cash_usd,
    "btc": btc_qty, "btc_cost": btc_cost, "eth": eth_qty, "eth_cost": eth_cost, "sol": sol_qty, "sol_cost": sol_cost,
    "realized_profit_twd": realized_twd,
    "realized_profit_us_stock": realized_us_stock,
    "realized_profit_crypto": realized_crypto
}
if current != saved:
    save_settings(current)

# =========================
# 4) 穩定抓匯率 & 價格（逐檔抓，不會整包死）
# =========================
@st.cache_data(ttl=120)
def get_usdtwd():
    # 先試 USD/TWD，再試 USDTWD，最後 fallback
    candidates = ["TWD=X", "USDTWD=X"]
    for c in candidates:
        try:
            df = yf.download(c, period="10d", interval="1d", progress=False)
            s = df.get("Close", pd.Series()).dropna()
            if len(s) > 0:
                return float(s.iloc[-1]), c
        except:
            pass
    return 32.5, "fallback(32.5)"

@st.cache_data(ttl=60)
def fetch_last_two_closes(codes):
    """
    回傳 dict: {code: (last_close, prev_close)}
    - 逐檔抓，避免一次抓一堆導致整包掛掉
    """
    out = {}
    errors = []
    for code in codes:
        try:
            df = yf.download(code, period="15d", interval="1d", progress=False)
            s = df.get("Close", pd.Series()).dropna()
            if len(s) >= 2:
                out[code] = (float(s.iloc[-1]), float(s.iloc[-2]))
            elif len(s) == 1:
                out[code] = (float(s.iloc[-1]), float(s.iloc[-1]))
            else:
                errors.append(f"{code}：沒拿到 Close")
        except Exception as e:
            errors.append(f"{code} 抓價失敗：{e}")
    return out, errors

@st.cache_data(ttl=60)
def build_df(tw_portfolio, us_portfolio, crypto_inputs):
    errors = []

    rate, rate_src = get_usdtwd()

    tw_codes = [x["code"] for x in tw_portfolio]
    us_codes = [x["code"] for x in us_portfolio]
    crypto_codes = list(crypto_inputs.keys())

    tw_prices, tw_err = fetch_last_two_closes(tw_codes)
    us_prices, us_err = fetch_last_two_closes(us_codes)
    cr_prices, cr_err = fetch_last_two_closes(crypto_codes)
    errors += tw_err + us_err + cr_err

    rows = []

    # 台股（TWD）
    for it in tw_portfolio:
        code = it["code"]
        if code not in tw_prices:
            errors.append(f"台股抓不到：{code}")
            continue
        last_close, prev_close = tw_prices[code]
        change = last_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        mv = last_close * it["shares"]
        cost = it["cost"] * it["shares"]
        unreal = mv - cost
        unreal_pct = (unreal / cost * 100) if cost else 0.0

        rows.append({
            "代號": it["name"],
            "類型": "台股",
            "幣別": "TWD",
            "現價": last_close,
            "漲跌": change,
            "幅度%": change_pct,
            "今日損益(TWD)": change * it["shares"],
            "市值(TWD)": mv,
            "未實現損益(TWD)": unreal,
            "未實現報酬%": unreal_pct,
        })

    # 美股（USD -> 顯示換成 TWD）
    for it in us_portfolio:
        code = it["code"]
        if code not in us_prices:
            errors.append(f"美股抓不到：{code}")
            continue
        last_close, prev_close = us_prices[code]
        change = last_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        mv_usd = last_close * it["shares"]
        cost_usd = it["cost"] * it["shares"]
        unreal_usd = mv_usd - cost_usd
        unreal_pct = (unreal_usd / cost_usd * 100) if cost_usd else 0.0

        rows.append({
            "代號": code,
            "類型": "美股",
            "幣別": "USD",
            "現價": last_close,
            "漲跌": change,
            "幅度%": change_pct,
            "今日損益(TWD)": (change * it["shares"]) * rate,
            "市值(TWD)": mv_usd * rate,
            "未實現損益(TWD)": unreal_usd * rate,
            "未實現報酬%": unreal_pct,
        })

    # 幣圈（用日K兩天 close 近似 24h）
    for code, info in crypto_inputs.items():
        qty = float(info["qty"])
        cost = float(info["cost"])
        if qty <= 0:
            continue
        if code not in cr_prices:
            errors.append(f"幣圈抓不到：{code}")
            continue
        last_close, prev_close = cr_prices[code]
        change = last_close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        mv_usd = last_close * qty
        cost_usd = cost * qty
        unreal_usd = mv_usd - cost_usd
        unreal_pct = (unreal_usd / cost_usd * 100) if cost_usd else 0.0

        rows.append({
            "代號": code.replace("-USD", ""),
            "類型": "Crypto(24h)",
            "幣別": "USD",
            "現價": last_close,
            "漲跌": change,
            "幅度%": change_pct,
            "今日損益(TWD)": (change * qty) * rate,
            "市值(TWD)": mv_usd * rate,
            "未實現損益(TWD)": unreal_usd * rate,
            "未實現報酬%": unreal_pct,
        })

    df = pd.DataFrame(rows)
    return df, rate, rate_src, errors

# =========================
# 5) 執行計算
# =========================
st.write("🔄 正在取得最新報價...")

crypto_inputs = {
    "BTC-USD": {"qty": btc_qty, "cost": btc_cost},
    "ETH-USD": {"qty": eth_qty, "cost": eth_cost},
    "SOL-USD": {"qty": sol_qty, "cost": sol_cost},
}

df, rate, rate_src, errors = build_df(tw_portfolio, us_portfolio, crypto_inputs)

# 現金（統一 TWD）
cash_total_twd = cash_twd_bank + cash_twd_physical + cash_twd_max + (cash_usd * rate)

# 市值 & 總資產
stock_crypto_total = float(df["市值(TWD)"].sum()) if not df.empty else 0.0
total_assets = stock_crypto_total + cash_total_twd

# 未實現
unreal_tw = float(df[df["類型"] == "台股"]["未實現損益(TWD)"].sum()) if not df.empty else 0.0
unreal_us = float(df[df["類型"] == "美股"]["未實現損益(TWD)"].sum()) if not df.empty else 0.0
unreal_crypto = float(df[df["類型"].str.contains("Crypto")]["未實現損益(TWD)"].sum()) if not df.empty else 0.0

# 已實現（USD -> TWD）
real_tw_twd = float(realized_twd)
real_us_twd = float(realized_us_stock) * rate
real_crypto_twd = float(realized_crypto) * rate

profit_tw_total = unreal_tw + real_tw_twd
profit_us_total = unreal_us + real_us_twd
profit_crypto_total = unreal_crypto + real_crypto_twd
total_profit = profit_tw_total + profit_us_total + profit_crypto_total

# 近似報酬率（保留你的邏輯）
invested_approx = total_assets - total_profit
return_rate_approx = (total_profit / invested_approx * 100) if invest
