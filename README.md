# Hermes Scripts

Hermes Agent 自用运维脚本合集，覆盖配置、Token 优化、成本控制、日志、秒杀等场景。

## 脚本清单

| 脚本 | 说明 |
|------|------|
| [hermes_setup_all.py](#hermes_setup_allpy) | 全量配置 + Token 优化 + 成本控制（16 大项，四层架构） |
| [log_generator.py](#log_generatorpy) | 任务日志格式化输出 |
| [snap_up_server.py](#snap_up_serverpy) | 腾讯云服务器秒杀抢购 |
| [get_cookies.py](#get_cookiespy) | 腾讯云登录 Cookie 获取辅助 |

---

## hermes_setup_all.py

**唯一入口**，合并了原 `hermes_token_optimizer.py` 和 `hermes_setup_all.py`（旧版 9 项）。

基于官方文档（253 篇 GitHub 源码文档）+ 社区优化方案（OnlyTerp/hermes-optimization-guide、Reddit）持续迭代。

### 快速开始

```bash
python3 hermes_setup_all.py
```

脚本启动后显示交互式菜单：

```
========================================================
 Hermes 全量配置（上河一号定制版）
 合并 token 优化 + 功能配置 + 成本控制，16 大项可选
========================================================

 第一层：核心配置
 1.  副驾模型 (auxiliary) — 成本降 60%-70%，两种模式
 2.  搜索后端 — 让它能联网查东西
 3.  记忆系统 — 内置记忆参数 + 可选外部 Provider

 第二层：Token 优化
 4.  密钥池策略 — 同 provider 多 key 轮转 + OAuth
 ...

选哪些（多选用逗号分隔，如 1,4,6）[默认:0]:
```

**操作方式：**

| 输入 | 含义 |
|------|------|
| `0` | 全部配置（按 1→16 顺序走一遍） |
| `1,4,6` | 只配置第 1、4、6 项 |
| `a` | 全部跳过，退出 |
| 回车 | 接受方括号内的默认值 |

每项配置内部也是交互式的，所有参数都有默认值，直接回车即可跳过。

---

### 四层架构 · 16 大项详解

#### 第一层：核心配置

**1. 副驾模型 (auxiliary)**

| 项目 | 说明 |
|------|------|
| **功效** | 将 vision、web_extract、compression 等 8 个副驾任务从主模型卸载到便宜模型，**成本降 60%-70%**，延迟快一倍 |
| **两种模式** | **批量配**（重/轻两档，3 个重任务 + 5 个轻任务一次性覆盖）/ **逐任务配**（每个副驾单独指定模型、超时、API Key） |
| **操作** | 选模式 → 输入重/轻任务的 provider、模型名、base_url、API Key → 自动写入 `hermes config set auxiliary.{task}.*` |
| **重任务** | vision, web_extract, flush_memories — 需要理解力，用稍强模型 |
| **轻任务** | compression, session_search, approval, skills_hub, mcp — 纯分类/搜索，用最便宜模型即可 |
| **推荐搭配** | 重任务: gemini-2.5-flash / 轻任务: gemini-2.5-flash-lite |

**2. 搜索后端**

| 项目 | 说明 |
|------|------|
| **功效** | 默认不配搜索 = 聋的，配了才能联网查东西 |
| **选项** | **Tavily**（专为 AI 设计，结构化结果，月 1000 次免费，需 API Key）/ **DuckDuckGo**（零成本，不需 Key）/ 跳过 |
| **操作** | 选后端 → 如选 Tavily 则输入 API Key（自动写入 .env + 设置 `web.tavily_api_key_env`）|
| **兜底** | Tavily 模式自动配 DuckDuckGo 为 fallback；Key 为空自动回退到 DuckDuckGo |

**3. 记忆系统**

| 项目 | 说明 |
|------|------|
| **功效** | 三层记忆：内置记忆(MEMORY.md) → 外部 Provider(可选) → Session Search(默认开) |
| **可调参数** | `memory_char_limit`（MEMORY.md 上限字符，默认 2200）/ `user_char_limit`（USER.md 上限，默认 1375）/ `nudge_interval`（每N轮提醒存记忆，默认 10）/ `flush_min_turns`（至少N轮才触发退出刷新，默认 6） |
| **外部 Provider** | 可选 honcho / mem0 / hindsight 等，建议先跑两周内置记忆再决定 |
| **操作** | 逐项输入参数值 → 可选运行 `hermes memory setup` 交互向导配外部 Provider |

---

#### 第二层：Token 优化

**4. 密钥池策略 (credential_pool)**

| 项目 | 说明 |
|------|------|
| **功效** | 同 provider 下多个 API Key 轮转使用，**避免单 Key 耗尽导致任务中断**（中断 = 浪费已建立的整个 context） |
| **与 fallback 的区别** | 密钥池 = 同 provider 内轮转 / fallback = 跨 provider 切换（见选项 14） |
| **四种策略** | `least_used`（推荐，选请求量最少的 Key 均衡负载）/ `round_robin`（轮询）/ `random`（随机）/ `fill_first`（默认，用完一个再用下一个，不均衡） |
| **添加密钥** | 方式 A: 交互向导 `hermes auth`（支持 API Key + OAuth）/ 方式 B: 手动逐个输入 → 写入 .env |
| **操作** | 输入 provider 名 → 选策略 → 选添加方式 → 输入 Key |

**5. 上下文窗口 & 最大输出**

| 项目 | 说明 |
|------|------|
| **功效** | `context_length` 让压缩算法精准计算触发时机；`max_tokens` 防止输出截断浪费输入 token |
| **不设的后果** | 压缩靠猜 context 大小 → 触发时机不准 / 输出被截断 → 已花的输入 token 打水漂 |
| **常见值** | GLM-5: 200000/131072 / Claude: 200000/16384 / GPT-4o: 128000/16384 |
| **操作** | 确认设 `context_length` → 输入 token 数 → 确认设 `max_tokens` → 输入 token 数 |

**6. 上下文压缩**

| 项目 | 说明 |
|------|------|
| **功效** | **双系统架构**：Gateway 安全网（context 占 85% 时强制压缩保命）+ Agent 主压缩（到阈值后用便宜模型总结，保留关键信息），**长对话成本降一个数量级** |
| **引擎可替换** | 默认 `compressor`（有损总结）→ 可换 `lcm`（无损上下文管理，需插件）→ 社区/第三方插件 |
| **核心参数** | `threshold`（上下文占用%达多少触发压缩，官方默认 0.50，推荐 0.75）/ `target_ratio`（压缩后保留原内容%，官方默认 0.20，推荐 0.25）/ `protect_last_n`（保护最近N条消息不参与压缩，官方默认 20，推荐 30） |
| **压缩总结模型** | 用便宜模型做总结（推荐 gemini-2.5-flash / glm-4-flash），主模型省 10 倍 |
| **操作** | 确认开启 → 选引擎 → 调参数（输入百分比整数，如 75 → 自动转为 0.75）→ 可选配总结模型 |

**7. Token 监控工具**

| 项目 | 说明 |
|------|------|
| **功效** | 看钱花在哪、压掉终端输出冗余 |
| **可选工具** | `tokscale`（pip 装，一条命令看全局消耗）/ `hermes-dashboard`（社区面板，按组件拆解）/ `hermes dashboard`（官方 Web Dashboard，后台启动）/ 跳过 |
| **RTK** | Rust Token Killer，把终端命令 token 消耗**压掉 80%-90%**（需 cargo 安装） |
| **操作** | 选监控工具 → 可选装 RTK → 启用 |

---

#### 第三层：成本控制

**13. Provider Routing (OpenRouter 专用)**

| 项目 | 说明 |
|------|------|
| **功效** | 控制 OpenRouter 请求路由到哪个底层 provider，**sort=price 直接走最便宜通道** |
| **⚠ 限制** | 仅在使用 OpenRouter 时生效，直连 provider 无效 |
| **核心配置** | `sort`（price 最便宜 / throughput 最快 / latency 最低首 token）/ `only`（白名单，逗号分隔如 `Anthropic,Google`）/ `ignore`（黑名单）/ `data_collection: deny`（禁止用你的数据训练）/ `require_parameters: true`（只用支持所有参数的 provider） |
| **操作** | 选 sort 策略（输入校验，无效值回退默认）→ 可选设白/黑名单 → 禁止数据收集 |

**14. Fallback Provider (跨 provider 容灾)**

| 项目 | 说明 |
|------|------|
| **功效** | 主模型遇到 429 限流 / 402 账单 / 401 认证 / 超时 → **自动切到备用 provider，不丢对话** |
| **三层容灾** | 密钥池(同 provider 轮转) → fallback_model(跨 provider 切换) |
| **激活场景** | 429: 同 Key 重试一次 → 失败切 fallback / 402: 立即切 fallback（24h 冷却）/ 401: 尝试刷新 → 失败切 fallback / 超时: 直接切 |
| **操作** | 输入 fallback provider 和 model → 如选 custom 则必须填 base_url（空则退出）→ 可选填 API Key |

**15. Shell Hooks (生命周期钩子)**

| 项目 | 说明 |
|------|------|
| **功效** | 将任意 shell 脚本绑定为 Hermes 生命周期钩子，**无需写 Python plugin** |
| **6 种事件** | `on_session_start`（新会话开始）/ `on_session_end`（会话结束）/ `pre_tool`（工具调用前，可阻断）/ `post_tool`（工具调用后）/ `on_agent_start` / `on_agent_end` |
| **典型用例** | pre_tool: 自动格式化代码、安全检查 / on_session_start: 加载环境变量、发通知 / post_tool: 记录操作日志、统计 token |
| **操作** | 输入钩子事件名（校验是否在 6 种有效值内，无效可强行继续）/ 输入脚本绝对路径（校验文件是否存在，不存在可强行继续）→ 可继续配多个 hook |

**16. Nous Tool Gateway (付费订阅专属)**

| 项目 | 说明 |
|------|------|
| **功效** | 付费 Nous Portal 订阅用户**免额外 API key** 使用：Web 搜索+提取 / 图片生成 / TTS / 浏览器自动化 |
| **替代关系** | 替代 TAVILY_API_KEY / FIRECRAWL_API_KEY / FAL_KEY / VOICE_TOOLS_OPENAI_KEY / ELEVENLABS_API_KEY / BROWSERBASE_API_KEY |
| **4 个工具** | `web`（搜索+提取）/ `image`（8 模型含 FLUX/GPT-Image）/ `tts`（文本转语音）/ `browser`（浏览器自动化） |
| **操作** | 自动检测订阅状态 → 输入要启用的工具（逗号分隔或 `all`）→ 逐个 `hermes config set tool_gateway.{tool}.enabled true` |

---

#### 第四层：进阶功能

**8. Profile 分身**

| 项目 | 说明 |
|------|------|
| **功效** | 每个分身独立记忆/人格/配置，互不干扰（如 work / life / coder 三个分身） |
| **操作** | 输入名称（仅字母数字连字符下划线）→ 选是否从当前配置克隆（推荐 y）→ 创建失败自动跳过后续 → 可选设为默认 |

**9. Skill 自主进化**

| 项目 | 说明 |
|------|------|
| **功效** | Agent 在对话中自动沉淀可复用经验为新 skill，**非平凡经验不丢失** |
| **机制** | 每 N 次工具调用 → 后台 fork review agent → 审查对话 → update/create/nothing → 打印 `Skill created: xxx`，不打断对话 |
| **操作** | 选是否启用 → 输入 `creation_nudge_interval`（默认 15，0=关闭）|

**10. 子 Agent 并发 + 深度**

| 项目 | 说明 |
|------|------|
| **功效** | 派多路 agent 同时干活，结果合并返回；orchestrator 角色可嵌套 spawn 自己的 worker |
| **两种角色** | `leaf`（默认，干活完返回）/ `orchestrator`（可再派子 agent，受 `max_spawn_depth` 限制） |
| **操作** | 可选配 `max_concurrent_children`（默认 3）/ 可选配 `max_spawn_depth`（默认 2）|

**11. Cron 定时任务**

| 项目 | 说明 |
|------|------|
| **功效** | 让 agent 定时自己干活，结果推送到消息平台 |
| **前置条件** | `hermes gateway` 必须在跑，cron 才会按时触发 |
| **操作** | 可选启动 gateway → 可选创建示例任务（输入 cron 表达式 + 任务指令 + 推送目标 → 自动执行 `hermes cron create`）|

**12. 生态工具**

| 项目 | 说明 |
|------|------|
| **Skill 库** | `wondelai/skills`（380+ 跨平台 skill）/ `nicholasgriffintn/awesome-agent-skills`（1000+ 社区合集） |
| **文档处理** | `Pandoc`（万能格式转换：PDF/DOCX/HTML/EPUB → Markdown，apt 安装）/ `Marker`（PDF 转 Markdown，效果优于 Pandoc，pip 安装） |
| **操作** | 选装 skill 库 → 选装文档工具 |

---

### 安全说明

- API Key 写入 `~/.hermes/.env`（权限 0600），**不写入 config.yaml**
- 所有 `hermes config set` 用列表传参，无 shell 注入风险
- 压缩参数支持百分比输入（如 75 → 自动转为 0.75）
- Tavily Key 为空自动回退 DuckDuckGo
- custom provider 空 base_url 直接拦截退出
- hook 事件名和脚本路径均做校验
- Profile 创建失败自动跳过后续

### v4.0 变更（相比旧 9 项 + 独立 token 脚本）

- **合并**：`hermes_token_optimizer.py` 功能全部纳入，旧脚本删除
- **新增 4 项**：Provider Routing / Fallback Provider / Shell Hooks / Nous Tool Gateway
- **升级 3 项**：
  - 密钥池：新增 random 策略 + `hermes auth` 交互向导 + OAuth 类型
  - 压缩：双系统架构（Gateway 85% + Agent 50%）+ `context.engine` 可替换
  - 并发：`max_spawn_depth` + orchestrator vs leaf 角色说明
- **架构**：三层 → 四层（新增「成本控制」层）
- **审查修复 16 项**：两轮代码审查，修了密钥 env 路径缺失、白名单覆盖 bug、inactive 误判、cron 只 print 不执行、hook 事件名校验等

---

## log_generator.py

任务日志格式化工具，输出 Markdown 格式。

```bash
python3 log_generator.py '{"task_name": "...", "status": "...", ...}'
```

---

## snap_up_server.py

腾讯云服务器秒杀抢购脚本。

- 精准定时抢购（秒级触发）
- 自动检测服务器时间同步误差
- Cookie + Token 认证
- 后台静默运行，完成通知

```bash
python3 snap_up_server.py --time "2026-04-23 15:00:00" --region 8 --cookies "..." --csrf "..."
```

---

## get_cookies.py

腾讯云登录 Cookie 获取辅助脚本。

---

## License

MIT
