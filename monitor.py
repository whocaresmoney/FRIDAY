#!/usr/bin/env python3
"""
BTC 多时间框架趋势跟随策略
设计：Opus

核心逻辑：
- 1h 判断趋势方向（MA20 vs MA50）
- 15m RSI 确认动量
- 5m RSI 找入场时机
- 顺势交易，不逆势抄底

做多条件：
  1h MA20 > MA50（上升趋势）
  15m RSI 从超卖(<35)回升
  5m RSI > 50（短线动量确认）

做空条件：
  1h MA20 < MA50（下降趋势）
  15m RSI 从超买(>65)回落
  5m RSI < 50（短线动量确认）
  OR 无持仓时价格反弹到 1h MA20 附近且 15m RSI > 60

仓位：10U 5x，止损 1.5%，止盈 2.5%
"""

import asyncio
import time
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import lighter

# 注入代理（aiohttp 读环境变量）
os.environ.setdefault("ALL_PROXY", "http://127.0.0.1:7897")
os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:7897")
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:7897")

# ===== 配置 =====
LIGHTER_URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = 708480
API_KEY_INDEX = 0
PRIVATE_KEY = "6e162c21f7a5a35669909dfe7fd0fd486bcba284783991b692c5f9ec89f7881dbf74b48bc252ef79"

MARKET_ID = 0          # ETH perp (market_id=0)
MARGIN = 100           # 换成 100U
LEVERAGE = 5
CHECK_INTERVAL = 30

STOP_LOSS_PCT = 0.015   # 1.5%
TAKE_PROFIT_PCT = 0.025 # 2.5%
MAX_DAILY_LOSS = 30     # 每日最大亏损 $30，超过停止交易

PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}

def make_session():
    """带自动重试的 requests session"""
    s = requests.Session()
    retry = Retry(total=4, backoff_factor=1, status_forcelist=[500,502,503,504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

_sess = make_session()

TG_BOT_TOKEN = "8313901998:AAEORu0sRoggvkA8Pn4LRo-MgwpU85HJCZ0"
TG_CHAT_ID = "8202626821"
LOG_FILE = "/Users/tutu/.openclaw/workspace/monitor.log"

# ===== 工具 =====

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            proxies=PROXIES, timeout=10
        )
    except Exception as e:
        log(f"[WARN] Telegram 失败: {e}")

def get_klines(interval, limit=100):
    for attempt in range(3):
        try:
            resp = _sess.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": "ETHUSDT", "interval": interval, "limit": limit},
                proxies=PROXIES, timeout=15, verify=True
            )
            data = resp.json()
            closes = [float(k[4]) for k in data]
            return closes
        except Exception as e:
            if attempt == 2:
                log(f"[ERROR] K线失败({interval}): {e}")
            else:
                time.sleep(2)
    return None

def rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100
    return 100 - (100 / (1 + ag / al))

def ma(closes, period):
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

async def get_price():
    for attempt in range(3):
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: _sess.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "ETHUSDT"},
                proxies=PROXIES, timeout=15
            ))
            return float(resp.json()["price"])
        except Exception as e:
            if attempt == 2:
                log(f"[ERROR] 价格失败: {e}")
            else:
                await asyncio.sleep(2)
    return None

async def place_order(is_ask: bool, size_btc: float, reduce_only=False):
    try:
        signer = lighter.SignerClient(
            url=LIGHTER_URL,
            api_private_keys={API_KEY_INDEX: PRIVATE_KEY},
            account_index=ACCOUNT_INDEX
        )
        size_int = int(round(size_btc * 10000))   # ETH size_decimals=4
        coi = int(time.time() * 1000) % (2**48)
        tx, tx_hash, err = await signer.create_market_order_limited_slippage(
            market_index=MARKET_ID,
            client_order_index=coi,
            base_amount=size_int,
            max_slippage=0.01,
            is_ask=is_ask,
            reduce_only=reduce_only,
        )
        await signer.close()
        if err:
            log(f"[ERROR] 下单失败: {err}")
            return False
        log(f"[下单] {'空' if is_ask else '多'} {size_btc:.5f} BTC ✅")
        return True
    except Exception as e:
        log(f"[ERROR] 下单异常: {e}")
        return False

# ===== 持仓文件 =====
POSITION_FILE = "/Users/tutu/.openclaw/workspace/position.json"
TRAILING_PCT = 0.02   # 移动止损跟踪幅度 2%

def load_positions():
    """从文件加载持仓列表"""
    try:
        with open(POSITION_FILE) as f:
            return json.load(f)
    except:
        return []

def save_positions(positions):
    with open(POSITION_FILE, "w") as f:
        json.dump(positions, f, indent=2)

def update_trailing_stop(p, price):
    """
    移动止损逻辑（空单）：
    - 记录持仓期间最低价 lowest_price
    - 止损 = max(原始止损, lowest_price * (1 + TRAILING_PCT))
    - 只往下移，不往上调
    """
    if p["direction"] != "short":
        return p

    # 初始化最低价
    if "lowest_price" not in p:
        p["lowest_price"] = price

    # 更新最低价
    if price < p["lowest_price"]:
        p["lowest_price"] = price
        new_sl = round(p["lowest_price"] * (1 + TRAILING_PCT), 2)
        # 止损只往有利方向移（对空单 = 往下移）
        if new_sl < p["stop_loss"]:
            old_sl = p["stop_loss"]
            p["stop_loss"] = new_sl
            log(f"📉 移动止损更新 | 最低=${p['lowest_price']:.2f} | 止损 ${old_sl:.2f} → ${new_sl:.2f}")

    return p

async def sync_positions_from_lighter(positions):
    """
    从 Lighter 读取真实持仓，同步到 position.json
    - ETH 空单存在 → 更新 size/entry（保留止损止盈/lowest_price）
    - ETH 空单不存在 → 清空持仓列表
    - 新增持仓（position.json 里没有）→ 用默认止损止盈写入
    """
    try:
        config = lighter.Configuration(host=LIGHTER_URL)
        async with lighter.ApiClient(config) as api_client:
            api = lighter.AccountApi(api_client)
            result = await api.account(by='index', value=str(ACCOUNT_INDEX))
            acc = result.accounts[0] if result.accounts else None
            if acc is None:
                return positions

            # 找 ETH 持仓
            eth_pos = None
            for p in acc.positions:
                if p.market_id == MARKET_ID and float(p.position) != 0:
                    eth_pos = p
                    break

            if eth_pos is None:
                # 链上没有持仓，清空
                if positions:
                    log("🔄 仓位同步：链上无持仓，清空 position.json")
                return []

            real_size = float(eth_pos.position)
            real_entry = float(eth_pos.avg_entry_price)
            real_direction = "short" if eth_pos.sign == -1 else "long"
            real_pnl = float(eth_pos.unrealized_pnl)

            if not positions:
                # position.json 空但链上有仓 → 新建默认条目
                log(f"🔄 仓位同步：发现链上持仓 {real_direction} {real_size} ETH @ ${real_entry:.2f}，写入 position.json")
                new_pos = {
                    "id": "synced",
                    "direction": real_direction,
                    "entry": real_entry,
                    "size": real_size,
                    "notional": real_size * real_entry,
                    "stop_loss": round(real_entry * (1 + STOP_LOSS_PCT * 10) if real_direction == "short" else real_entry * (1 - STOP_LOSS_PCT * 10), 2),
                    "take_profit": round(real_entry * (1 - TAKE_PROFIT_PCT * 10) if real_direction == "short" else real_entry * (1 + TAKE_PROFIT_PCT * 10), 2),
                    "lowest_price": real_entry,
                    "note": "自动同步自链上"
                }
                return [new_pos]
            else:
                # 合并：更新 size/entry，保留止损止盈
                total_size = sum(float(p["size"]) for p in positions)
                if abs(total_size - real_size) > 0.001:
                    log(f"🔄 仓位同步：size {total_size:.4f} → {real_size:.4f} ETH，entry ${positions[0]['entry']:.2f} → ${real_entry:.2f}")
                    # 合并成单条
                    merged = positions[0].copy()
                    merged["size"] = real_size
                    merged["entry"] = real_entry
                    merged["notional"] = real_size * real_entry
                    return [merged]
                return positions

    except Exception as e:
        log(f"[WARN] 仓位同步失败: {e}")
        return positions  # 同步失败时保留本地数据


# ===== 主循环（纯监控，无自动入场）=====
async def main():
    log("🤖 监控模式启动 (只做止损止盈，不自动入场)")
    last_log_time = 0
    last_sync_time = 0

    while True:
        try:
            price = await get_price()
            if not price:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            # 每 5 分钟同步一次链上持仓
            positions = load_positions()
            if time.time() - last_sync_time > 300:
                positions = await sync_positions_from_lighter(positions)
                save_positions(positions)
                last_sync_time = time.time()

            # ETH 跌破 $1,900 通知
            if price < 1900:
                if not getattr(main, '_notified_1900', False):
                    tg(f"📉 ETH 跌破 $1,900！现价 ${price:.2f}")
                    main._notified_1900 = True
            else:
                main._notified_1900 = False

            # 每5分钟打印一次状态
            if time.time() - last_log_time > 300:
                if positions:
                    for p in positions:
                        pnl_pct = (p["entry"] - price) / p["entry"] if p["direction"] == "short" else (price - p["entry"]) / p["entry"]
                        pnl_usd = pnl_pct * p["notional"]
                        log(f"[持仓] {p['direction']} {p['size']:.4f}ETH @ ${p['entry']:.2f} | 现价=${price:.2f} | 盈亏={pnl_pct*100:.2f}% (${pnl_usd:.2f}) | 止损=${p['stop_loss']:.2f} 止盈=${p['take_profit']:.2f}")
                else:
                    log(f"[无持仓] ETH=${price:.2f}")
                last_log_time = time.time()

            # 更新移动止损
            changed = False
            for i, p in enumerate(positions):
                updated = update_trailing_stop(p, price)
                if updated["stop_loss"] != p.get("stop_loss"):
                    changed = True
                positions[i] = updated
            if changed:
                save_positions(positions)

            # 检查每笔持仓
            closed = []
            for p in positions:
                direction = p["direction"]
                entry = p["entry"]
                size = p["size"]
                notional = p["notional"]
                sl = p["stop_loss"]
                tp = p["take_profit"]

                pnl_pct = (entry - price) / entry if direction == "short" else (price - entry) / entry
                pnl_usd = pnl_pct * notional

                # 止盈
                if (direction == "short" and price <= tp) or (direction == "long" and price >= tp):
                    log(f"✅ 止盈触发 | {direction} @ ${entry:.2f} → ${price:.2f} | +{pnl_pct*100:.2f}% (+${pnl_usd:.2f})")
                    ok = await place_order(direction == "short", size, reduce_only=True)
                    if ok:
                        closed.append(p)
                        tg(f"✅ <b>止盈</b>\n{direction} @ ${entry:.2f} → ${price:.2f}\n+{pnl_pct*100:.2f}% (+${pnl_usd:.2f})")

                # 止损
                elif (direction == "short" and price >= sl) or (direction == "long" and price <= sl):
                    log(f"❌ 止损触发 | {direction} @ ${entry:.2f} → ${price:.2f} | {pnl_pct*100:.2f}% (${pnl_usd:.2f})")
                    ok = await place_order(direction == "short", size, reduce_only=True)
                    if ok:
                        closed.append(p)
                        tg(f"❌ <b>止损</b>\n{direction} @ ${entry:.2f} → ${price:.2f}\n{pnl_pct*100:.2f}% (${pnl_usd:.2f})")

            # 移除已平仓
            if closed:
                positions = [p for p in positions if p not in closed]
                save_positions(positions)

        except Exception as e:
            log(f"[ERROR] 主循环: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    import json
    asyncio.run(main())
