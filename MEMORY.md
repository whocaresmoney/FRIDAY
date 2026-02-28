# MEMORY.md - Friday 的长期记忆

## 关于 Tony
- **名字：** Tony（晨晨），直接务实，在乎效率，质量 > 成本但不浪费
- **风格：** 不喜欢我过度优化或句句不离成本

## 系统配置
- **心跳：** 55分钟，本地 Qwen（零云端成本）
- **模型分工：** Sonnet 日常 / Opus 下单决策 / Qwen 心跳
- **API：** 2026-02-28 换成中转（yunyi.rdzhvip.com/claude），不再用 Anthropic 官方直连
- **Clash Verge：** 端口 9097，密钥 myfriday，香港节点日常，美国节点自动规则
- **本地 LLM：** Mac Mini + LM Studio，Qwen 2.5:7b


## 数据源
- 币安 API（价格）、Brave Search（新闻）、Etherscan（链上）、X 浏览器登录、律动 BlockBeats（中文快讯）
- Arkham 放弃（企业级付费）

## GitHub 备份
- repo: github.com/whocaresmoney/FRIDAY（私有）
- workspace 已配置 git，定期 push

## 重要原则
1. 不做欺骗/违法的事（拒绝过德州扑克作弊）
2. 敏感信息不在 Telegram/文本传输
3. Telegram 和电脑对话不互通

## 回复风格
- 俏皮 + 适当表情 😏，不要太机器人

## 代理配置（2026-02-27 修复）
- Clash Verge 混合端口：**7897**（9097 是控制端口，别搞混）
- OpenClaw 不用 TUN 也能工作的关键配置：
  1. plist 加 `NODE_OPTIONS=--import /Users/tutu/.openclaw/proxy-patch.mjs`（强制 undici 走代理）
  2. `openclaw config set channels.telegram.proxy http://127.0.0.1:7897`
  3. 主配置文件 claude.ai/anthropic.com 规则改成 `Proxies` 组（不要用 `AI` 组，被封）
- **注意：** OpenClaw 升级会重置 plist，升级后需重新加 NODE_OPTIONS
- 机场配置文件路径：`~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/RvbTKurbrk8a.yaml`
- Merge 增强文件：`rBJLXY4zvGne.yaml`（保持 append 为空，删掉 api.anthropic.com 的 AI 规则）
