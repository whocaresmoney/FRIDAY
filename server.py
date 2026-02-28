#!/usr/bin/env python3
"""Dashboard HTTP server + API 代理（解决 CORS）"""
import os, json, asyncio, threading
import http.server
import requests
import lighter

PORT = 8765
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
LIGHTER_URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = "708480"

def fetch_account_sync():
    """同步包装异步 Lighter SDK"""
    async def _fetch():
        config = lighter.Configuration(host=LIGHTER_URL)
        async with lighter.ApiClient(config) as api_client:
            api = lighter.AccountApi(api_client)
            result = await api.account(by='index', value=ACCOUNT_INDEX)
            acc = result.accounts[0]
            pos_list = []
            for p in acc.positions:
                if float(p.position) != 0:
                    pos_list.append({
                        "symbol": p.symbol,
                        "market_id": p.market_id,
                        "direction": "short" if p.sign == -1 else "long",
                        "size": float(p.position),
                        "entry": float(p.avg_entry_price),
                        "unrealized_pnl": float(p.unrealized_pnl),
                        "liq_price": float(p.liquidation_price) if p.liquidation_price else None,
                    })
            return {
                "collateral": float(acc.collateral),
                "available_balance": float(acc.available_balance),
                "total_asset_value": float(acc.total_asset_value),
                "positions": pos_list
            }
    return asyncio.run(_fetch())

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WORKSPACE, **kwargs)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/eth-price':
            self.api_proxy('https://fapi.binance.com/fapi/v1/premiumIndex?symbol=ETHUSDT')
        elif path == '/api/account':
            self.api_account()
        else:
            super().do_GET()

    def api_proxy(self, url):
        try:
            r = requests.get(url, proxies=PROXIES, timeout=8)
            body = r.content
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def api_account(self):
        try:
            data = fetch_account_sync()
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, *args):
        pass

if __name__ == '__main__':
    server = http.server.HTTPServer(('', PORT), Handler)
    print(f'http://localhost:{PORT}/dashboard.html')
    server.serve_forever()
