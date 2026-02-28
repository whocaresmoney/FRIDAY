#!/usr/bin/env python3
"""
Lighter 交易机器人
策略：Tony 给大方向（做空），我负责找入场点、止损、止盈
标的：BTC（market_id=1）
资金：100 USDT，5倍杠杆
"""

import asyncio
import time
import requests
import lighter

# ===== 配置 =====
BASE_URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = 708480
API_KEY_INDEX = 0
PRIVATE_KEY = "6e162c21f7a5a35669909dfe7fd0fd486bcba284783991b692c5f9ec89f7881dbf74b48bc252ef79"

MARKET_ID = 1          # BTC perp
SYMBOL = "BTCUSDT"
MARGIN = 100           # USDT

# 代理
PROXIES = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}
LEVERAGE = 5
PRICE_DECIMALS = 1     # BTC price精度
SIZE_DECIMALS = 5      # BTC size精度

# 止损止盈设置
STOP_LOSS_PCT = 0.04   # 4% 止损（5倍杠杆 → 20%保证金损失）
TAKE_PROFIT_PCT = 0.06 # 6% 止盈（5倍杠杆 → 30%保证金收益）

# ===== 工具函数 =====

def get_btc_price():
    """从 Binance 获取实时 BTC 价格"""
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": SYMBOL},
            proxies=PROXIES,
            timeout=10
        )
        return float(resp.json()["price"])
    except Exception as e:
        print(f"[ERROR] 获取价格失败: {e}")
        return None

def get_klines(interval="1h", limit=50):
    """获取 K 线数据"""
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": SYMBOL, "interval": interval, "limit": limit},
            proxies=PROXIES,
            timeout=10
        )
        data = resp.json()
        closes = [float(k[4]) for k in data]
        highs = [float(k[2]) for k in data]
        lows = [float(k[3]) for k in data]
        volumes = [float(k[5]) for k in data]
        return closes, highs, lows, volumes
    except Exception as e:
        print(f"[ERROR] 获取K线失败: {e}")
        return None, None, None, None

def calc_rsi(closes, period=14):
    """计算 RSI"""
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_ma(closes, period):
    """计算移动平均"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

def analyze_entry(direction="short"):
    """
    分析入场时机
    返回: (should_enter, reason, entry_price)
    """
    price = get_btc_price()
    if not price:
        return False, "获取价格失败", None

    closes, highs, lows, volumes = get_klines("1h", 50)
    if not closes:
        return False, "获取K线失败", None

    rsi = calc_rsi(closes)
    ma20 = calc_ma(closes, 20)
    ma50 = calc_ma(closes, 50)

    print(f"\n[分析] BTC: ${price:.1f} | RSI(14): {rsi:.1f} | MA20: {ma20:.1f} | MA50: {ma50:.1f}")

    if direction == "short":
        reasons = []

        # RSI 超买
        if rsi > 60:
            reasons.append(f"RSI={rsi:.1f}(超买)")

        # 价格在均线上方（压力位附近）
        if ma20 and price > ma20:
            reasons.append(f"价格高于MA20(${ma20:.0f})")

        # 成交量判断（近3根缩量）
        if volumes and volumes[-1] < sum(volumes[-10:-1]) / 9:
            reasons.append("成交量萎缩")

        # 至少满足2个条件才入场
        if len(reasons) >= 2:
            return True, " | ".join(reasons), price
        else:
            return False, f"条件不足({len(reasons)}/2): {' | '.join(reasons) if reasons else '无'}", price

    return False, "方向未定义", price

async def place_order(client, is_short: bool, price: float, size_btc: float, order_type="market"):
    """下单"""
    # Lighter: is_ask=True 是卖出(做空), is_ask=False 是买入(做多)
    is_ask = is_short

    # 转换为整数精度
    price_int = int(round(price * (10 ** PRICE_DECIMALS)))
    size_int = int(round(size_btc * (10 ** SIZE_DECIMALS)))

    client_order_index = int(time.time() * 1000) % (2**48)

    print(f"\n[下单] {'做空' if is_short else '做多'} | 价格: ${price:.1f} | 数量: {size_btc:.5f} BTC")
    print(f"       price_int={price_int} | size_int={size_int}")

    tx, tx_hash, err = await client.create_market_order_limited_slippage(
        market_index=MARKET_ID,
        client_order_index=client_order_index,
        base_amount=size_int,
        max_slippage=0.01,
        is_ask=is_ask,
        reduce_only=False,
    )

    if err:
        print(f"[ERROR] 下单失败: {err}")
        return None

    print(f"[成功] tx_hash: {tx_hash}")
    return tx_hash

async def close_position(client, is_short: bool, price: float, size_btc: float):
    """平仓（反向开单）"""
    print(f"\n[平仓] 方向: {'平空(买入)' if is_short else '平多(卖出)'}")
    return await place_order(client, not is_short, price, size_btc)

async def run_bot(direction="short"):
    """主运行逻辑"""
    print("=" * 50)
    print(f"[启动] Lighter 交易机器人")
    print(f"[配置] 方向={direction} | 保证金={MARGIN}U | 杠杆={LEVERAGE}x")
    print(f"[配置] 止损={STOP_LOSS_PCT*100:.0f}% | 止盈={TAKE_PROFIT_PCT*100:.0f}%")
    print("=" * 50)

    # 初始化 SignerClient
    signer = lighter.SignerClient(
        url=BASE_URL,
        api_private_keys={API_KEY_INDEX: PRIVATE_KEY},
        account_index=ACCOUNT_INDEX
    )

    # 分析入场
    print("\n[分析入场时机...]")
    should_enter, reason, entry_price = analyze_entry(direction)

    print(f"[结果] {'✅ 入场' if should_enter else '⏳ 等待'}: {reason}")

    if not should_enter:
        print("\n条件不满足，不入场。")
        await signer.close()
        return

    # 计算仓位大小
    notional = MARGIN * LEVERAGE  # 名义价值
    size_btc = notional / entry_price
    print(f"\n[仓位] 名义价值=${notional} | BTC数量={size_btc:.5f}")

    # 下单
    tx_hash = await place_order(signer, direction == "short", entry_price, size_btc)
    if not tx_hash:
        await signer.close()
        return

    # 计算止损止盈价格
    if direction == "short":
        stop_loss_price = entry_price * (1 + STOP_LOSS_PCT)
        take_profit_price = entry_price * (1 - TAKE_PROFIT_PCT)
    else:
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        take_profit_price = entry_price * (1 + TAKE_PROFIT_PCT)

    print(f"\n[监控] 入场价: ${entry_price:.1f}")
    print(f"       止损价: ${stop_loss_price:.1f}")
    print(f"       止盈价: ${take_profit_price:.1f}")

    # 监控持仓
    while True:
        await asyncio.sleep(30)  # 每30秒检查一次
        current_price = get_btc_price()
        if not current_price:
            continue

        if direction == "short":
            pnl_pct = (entry_price - current_price) / entry_price
        else:
            pnl_pct = (current_price - entry_price) / entry_price

        pnl_usd = pnl_pct * notional
        print(f"[持仓] 当前=${current_price:.1f} | 盈亏={pnl_pct*100:.2f}% (${pnl_usd:.2f})")

        # 止盈
        if (direction == "short" and current_price <= take_profit_price) or \
           (direction == "long" and current_price >= take_profit_price):
            print(f"\n✅ 止盈触发! 价格=${current_price:.1f}")
            await close_position(signer, direction == "short", current_price, size_btc)
            break

        # 止损
        if (direction == "short" and current_price >= stop_loss_price) or \
           (direction == "long" and current_price <= stop_loss_price):
            print(f"\n❌ 止损触发! 价格=${current_price:.1f}")
            await close_position(signer, direction == "short", current_price, size_btc)
            break

    await signer.close()
    print("\n[完成] 机器人退出")

if __name__ == "__main__":
    # 用法: python3 lighter_bot.py
    # 默认做空方向，等条件满足自动入场
    asyncio.run(run_bot(direction="short"))
