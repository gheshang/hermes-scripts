# Hermes Scripts

Hermes Agent 的日常运维脚本合集，覆盖配置、Token 优化、日志等场景。

## 脚本清单

| 脚本 | 说明 | 行数 |
|------|------|------|
| [hermes_setup_all.py](#hermes_setup_allpy) | 全量配置（9 大功能，交互式选择） | 462 |
| [hermes_token_optimizer.py](#hermes_token_optimizerpy) | Token 成本优化（四层 10 项参数） | 380 |
| [log_generator.py](#log_generatorpy) | 任务日志格式化输出 | 53 |
| [snap_up_server.py](#snap_up_serverpy) | 腾讯云服务器秒杀抢购 | — |
| [get_cookies.py](#get_cookiespy) | 腾讯云登录 Cookie 获取辅助 | — |

---

## hermes_setup_all.py

**全量配置脚本**，一个入口覆盖 Hermes Agent 所有核心配置项，可选安装，不想要的就跳过。

### 功能列表

1. **副驾模型 (auxiliary)** — 分轻重两档，重任务（vision/web_extract）用强模型，轻任务（compression/session_search）用便宜快模型，成本降 60-70%
2. **搜索后端** — Tavily（月 1000 次免费）或 DuckDuckGo（零成本）
3. **记忆系统** — 内置记忆参数调优 + 可选外部 Memory Provider（honcho/mem0/hindsight）
4. **Profile 分身** — 一台机器多个独立人格/记忆的分身
5. **Skill 自主进化** — Agent 从对话中自动沉淀新技能
6. **子 Agent 并发** — 派多路 agent 同时干活
7. **Cron 定时任务** — 让 agent 定时自己跑任务
8. **Token 监控与压缩** — 看钱花在哪、压掉冗余（tokscale / RTK 等）
9. **生态工具** — 批量装 skill 库、文档处理工具

### 用法

```bash
python3 ~/.hermes/hermes_setup_all.py
```

输入编号选功能，逗号分隔多选，`0` 全配，`a` 退出。

### 安全说明

- API Key 写入 `~/.hermes/.env`（权限 0600），**不写入 config.yaml**
- 所有 `hermes config set` 用列表传参，无 shell 注入风险
- 压缩参数支持百分比输入（如 75 → 自动转为 0.75）

---

## hermes_token_optimizer.py

**Token 成本优化专项脚本**，基于知乎《Hermes Agent 成本优化大揭秘》四层优化体系 + 官方文档 + SegmentFault 转述。

### 优化层次

| 层次 | 配置项 | 推荐值 |
|------|--------|--------|
| 第一层：密钥池策略 | `credential_pool_strategies` | `least_used` |
| 第二层：Context 压缩 | `context_length` / `max_tokens` / `threshold` / `target_ratio` / `protect_last_n` / `summary_model` | 200000 / 131072 / 0.75 / 0.25 / 30 / glm-4-flash |
| 第三层：Auxiliary 模型 | vision, web_extract, compression, session_search 等 8 个副驾 | 自定义 |
| 第四层：Smart Model Routing | Hermes v0.10.0 暂不支持，等效方案为 auxiliary | 说明性 |

### 用法

```bash
python3 ~/.hermes/hermes_token_optimizer.py
```

逐项按需配置，每项独立确认。

---

## log_generator.py

简单的任务日志格式化工具，输出 Markdown 格式的任务日志。

### 用法

```bash
python3 ~/.hermes/log_generator.py '{"task_name": "...", "status": "...", ...}'
```

---

## snap_up_server.py

腾讯云服务器**秒杀抢购**脚本。支持：

- 精准定时抢购（秒级触发）
- 自动检测服务器时间同步误差
- Cookie + Token 认证
- 后台静默运行，完成通知

### 用法

```bash
python3 snap_up_server.py --time "2026-04-23 15:00:00" --region 8 --cookies "..." --csrf "..."
```

---

## get_cookies.py

腾讯云登录 Cookie 获取辅助脚本。

---

## License

MIT
