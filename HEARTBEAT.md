# HEARTBEAT.md

## ETH 价格监控
- 查币安 ETH/USDT 价格：https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT
- 目前 Tony 无持仓（2026-03-01 更新）
- 价格阈值提醒：暂停（如需恢复再说阈值）
- 如果有重大地缘新闻（停火、哈梅内伊确认死亡、新一轮攻击）：立刻推送 Tony
- 推送时间：全天，不受 23:00-08:00 静默限制（Tony 明确要求盯盘）

## GitHub 备份
- 位置：~/.openclaw/workspace/backup.sh
- 远程：github.com/whocaresmoney/FRIDAY
- 每天早上 9:00 推送时执行 git add + commit + push

## 新闻监控（优化版）

### 优先级：BlockBeats > RSS > Brave Search
1. **BlockBeats**（主用，免费稳定）
   - 每心跳必抓：https://www.theblockbeats.info/newsflash
   - 中文快讯源，覆盖币圈/地缘

2. **RSS 订阅**（备用）
   - CoinDesk: https://www.coindesk.com/arc/outboundfeeds/rss/
   - Cointelegraph: https://cointelegraph.com/rss

3. **Brave Search**（节省用）
   - 仅在 BlockBeats + RSS 无新内容时使用
   - 每天最多 3 次（早/中/晚各1次）
   - 关键词：Iran Israel war latest、ETH crypto news

### 推送规则
- 🚨 重大地缘/黑天鹅/高层确认死亡：立刻推
- 📰 币圈重大新闻（交易所/监管/ETF/大额清算）：立刻推
- 📊 博主观点变化：直接推
- 🔄 判断：置信度低但可能重要的也推送，提示 Tony 点开原文

## 心跳间隔
- 每 30 分钟一次

## 去重规则
- 记录文件：`workspace/dedup.json`
- 每次推送后更新 lastPush 数组（存标题Hash）
- 推送前比对：24小时内相同Hash不推
- 重大突发（地缘/黑天鹅/高层确认死亡）无视去重，直接推

## 早上推送格式
📰 每日简报 YYYY-MM-DD HH:MM
═══════════════════════════════

📊 价格（当前）24h变化
• ETH: $xxx（±x.xx%）
• BTC: $xxx（±x.xx%）
• SOL: $xxx（±x.xx%）

💰 持仓：空仓/仓数+盈亏

🌍 地缘局势（每个新闻标注🟢利好/🔴利空）
🟢/**🔴** 要点1
🟢/**🔴** 要点2

🇺🇸 美股概览（每个新闻标注🟢利好/🔴利空）
🟢/**🔴** SPY/QQQ/VIX 走势

📉/📈 重大新闻（空多比例：空>多则用📉，多>空则用📈）
🟢/**🔴** **时间** 标题（涨用🟢，跌用🔴，标注具体分钟/小时前）

📉/📈 博主观点（空多比例：空>多则用📉，多>空用📈）
🟢/**🔴** **@博主**（X小时前）: 观点摘要
🟢/**🔴**（X小时前）无更新

📊 技术分析
• 关键支撑/阻力位
• 趋势信号

📊 分析
• 综合分析

📊 建议（根据综合分析，自主判断）
• 短期：做空/做多/观望
• 中长期：做空/做多/观望
• 建仓点位
