# HEARTBEAT.md

## ETH 价格监控
- 查币安 ETH/USDT 价格：https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT
- 目前 Tony 无持仓（2026-03-01 更新）
- 价格阈值提醒：暂停（如需恢复再说阈值）
- 如果有重大地缘新闻（停火、哈梅内伊确认死亡、新一轮攻击）：立刻推送 Tony
- 推送时间：全天，不受 23:00-08:00 静默限制（Tony 明确要求盯盘）

## 新闻监控
- 每次心跳用 Brave Search 搜索：Iran Israel war latest、ETH crypto news
- 主快讯源（中文）：BlockBeats https://www.theblockbeats.info/newsflash
- 备用快讯源（英文 RSS）：
  - CoinDesk https://www.coindesk.com/arc/outboundfeeds/rss/
  - Cointelegraph https://cointelegraph.com/rss
- OKX API：持仓 PNL、资金费率（需 key）
- CoinGlass：清算数据、大单流向
- Glassnode/Dune：链上持仓、活跃地址（需 key）
- X 博主：Tony 自己看（不再推送）
- 推送规则：
  1. 地缘重大突发（停火/升级/新一轮攻击/高层确认死亡等）立刻推
  2. 币圈重大新闻（交易所/监管/黑天鹅/ETF/大额清算等）立刻推
  3. 上面 3 个推特号里“带行情判断/交易观点/方向信号”的内容，直接推 Tony
  4. 判断策略（本地 Qwen 适用）：作为筛选器，不当裁判；置信度低但可能重要的也推送，并提示 Tony 点开原文确认；整体偏向“宁可多推别漏”

## 早报
- 每天早上 9:00 推送，格式参考 BlockInfinity：
  1. 价格：ETH/BTC/SOL + 24h 变化
  2. 持仓：无仓写"空仓"，有仓写仓数+盈亏
  3. 重大新闻：用 🟢 🔴 标注利好/利空
  4. 地缘局势
  5. 博主观点（Ted/AshCrypto/Pathusa）
  使用 ════════════════════════ 分隔线
