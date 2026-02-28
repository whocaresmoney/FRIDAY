#!/usr/bin/env python3
"""
小单测试 - 10U 5x 市价做空
"""
import asyncio
import time
import lighter

BASE_URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = 708480
API_KEY_INDEX = 0
PRIVATE_KEY = "bea64e403e7406f737266363755b601e60608d91615576e15ef461552733442db878e7ffa5665a60"

MARKET_ID = 1
MARGIN = 10       # 10U 测试
LEVERAGE = 5
PRICE_DECIMALS = 1
SIZE_DECIMALS = 5

async def main():
    # 获取当前价格
    client = lighter.ApiClient(lighter.Configuration(host=BASE_URL))
    resp = await lighter.OrderApi(client).order_book_details()
    price = None
    for book in resp.order_book_details:
        if book.symbol == "BTC":
            price = float(book.last_trade_price)
    await client.close()

    if not price:
        print("[ERROR] 获取价格失败")
        return

    print(f"当前 BTC 价格: ${price:.1f}")

    # 计算仓位
    notional = MARGIN * LEVERAGE  # 50U 名义价值
    size_btc = notional / price
    print(f"仓位: {size_btc:.5f} BTC (名义 ${notional})")

    # 下单
    signer = lighter.SignerClient(
        url=BASE_URL,
        api_private_keys={API_KEY_INDEX: PRIVATE_KEY},
        account_index=ACCOUNT_INDEX
    )

    price_int = int(round(price * (10 ** PRICE_DECIMALS)))
    size_int = int(round(size_btc * (10 ** SIZE_DECIMALS)))
    client_order_index = int(time.time() * 1000) % (2**48)

    print(f"\n下单参数: price_int={price_int} size_int={size_int} is_ask=True(做空)")

    tx, tx_hash, err = await signer.create_order(
        market_index=MARKET_ID,
        client_order_index=client_order_index,
        base_amount=size_int,
        price=price_int,
        is_ask=True,   # 做空
        order_type=signer.ORDER_TYPE_MARKET,
        time_in_force=signer.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
        reduce_only=False,
        order_expiry=signer.DEFAULT_IOC_EXPIRY,
    )

    if err:
        print(f"[ERROR] 下单失败: {err}")
    else:
        print(f"[成功] tx_hash: {tx_hash}")

    await signer.close()

asyncio.run(main())
