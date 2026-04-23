# hermes-scripts

上河一号自用的 Hermes Agent 配置/优化脚本 + 腾讯云秒杀抢购脚本。

## 脚本清单

| 文件 | 用途 |
|------|------|
| `hermes_setup_all.py` | Hermes Agent 全量配置（9大功能可选：副驾模型/搜索后端/记忆系统/Profile分身/Skill进化/子Agent并发/Cron定时/Token监控/生态工具） |
| `hermes_token_optimizer.py` | Token 成本优化（10项：密钥池策略/上下文长度/压缩参数/副驾模型等） |
| `log_generator.py` | 任务日志生成器（JSON输入 → Markdown格式日志） |
| `snap_up_server.py` | 腾讯云秒杀抢购（定时HEAD校时+POST下单，后台运行） |
| `get_cookies.py` | 腾讯云 cookies 获取辅助脚本 |

## 使用

```bash
# Hermes 配置
python3 hermes_setup_all.py

# Token 优化
python3 hermes_token_optimizer.py

# 任务日志
python3 log_generator.py '{"task_name":"示例","status":"完成","key_outputs":["结果1"]}'

# 秒杀抢购（先填入 cookies 和 csrf-token，后台运行）
python3 snap_up_server.py
```

## 注意

- `hermes_setup_all.py` 和 `hermes_token_optimizer.py` 依赖 `hermes` CLI
- `snap_up_server.py` 需要在开抢前填入有效 cookies 和 csrf-token
- 所有脚本仅用于个人服务器环境，不包含任何敏感信息
