# Hermes Scripts

Hermes Agent 自用运维脚本合集。

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

### 四层架构 · 16 大项

#### 第一层：核心配置

| # | 功能 | 说明 |
|---|------|------|
| 1 | 副驾模型 (auxiliary) | 重/轻两档批量配 or 逐任务精细配，成本降 60%-70% |
| 2 | 搜索后端 | Tavily（月 1000 次免费）或 DuckDuckGo（零成本） |
| 3 | 记忆系统 | 内置记忆参数调优 + 可选外部 Provider（honcho/mem0/hindsight） |

#### 第二层：Token 优化

| # | 功能 | 说明 |
|---|------|------|
| 4 | 密钥池策略 | 同 provider 多 key 轮转（least_used/round_robin/random）+ OAuth |
| 5 | 上下文窗口 & 最大输出 | `context_length` / `max_tokens`，压缩算法精准计算的前提 |
| 6 | 上下文压缩 | **双系统**：Gateway 安全网 85% + Agent 主压缩 50%（可调）；引擎可替换（compressor/lcm/插件） |
| 7 | Token 监控工具 | tokscale / hermes-dashboard / RTK 终端压缩 |

#### 第三层：成本控制 🆕

| # | 功能 | 说明 |
|---|------|------|
| 13 | Provider Routing | OpenRouter 下 sort=price 直走最便宜通道 |
| 14 | Fallback Provider | 主模型 429/402/401/超时 → 自动切备用 provider，不丢对话 |
| 15 | Shell Hooks | 绑定脚本到生命周期事件（pre_tool/post_tool/on_session_start 等） |
| 16 | Nous Tool Gateway | 付费订阅免额外 API key 用搜索/图片/TTS/浏览器 |

#### 第四层：进阶功能

| # | 功能 | 说明 |
|---|------|------|
| 8 | Profile 分身 | 每个分身独立记忆/人格/配置 |
| 9 | Skill 自主进化 | Agent 从对话中自动沉淀新技能 |
| 10 | 子 Agent 并发 + 深度 | 派多路 agent，orchestrator 可嵌套 spawn（max_spawn_depth 可配） |
| 11 | Cron 定时任务 | 定时自己跑任务，结果推送到消息平台 |
| 12 | 生态工具 | 批量装 skill 库（wondelai/awesome-agent-skills）、文档处理（Pandoc/Marker） |

### 用法

```bash
python3 hermes_setup_all.py
```

交互式菜单：输入编号选功能，逗号分隔多选（如 `1,4,6`），`0` 全配，`a` 退出。

### 安全说明

- API Key 写入 `~/.hermes/.env`（权限 0600），**不写入 config.yaml**
- 所有 `hermes config set` 用列表传参，无 shell 注入风险
- 压缩参数支持百分比输入（如 75 → 自动转为 0.75）

### v4.0 变更（相比旧 9 项 + 独立 token 脚本）

- **合并**：`hermes_token_optimizer.py` 功能全部纳入，旧脚本删除
- **新增 4 项**：Provider Routing / Fallback Provider / Shell Hooks / Nous Tool Gateway
- **升级 3 项**：
  - 密钥池：新增 random 策略 + `hermes auth` 交互向导 + OAuth 类型
  - 压缩：双系统架构（Gateway 85% + Agent 50%）+ `context.engine` 可替换
  - 并发：`max_spawn_depth` + orchestrator vs leaf 角色说明
- **架构**：三层 → 四层（新增「成本控制」层）

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
