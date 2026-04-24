# wiki-sync.sh

Wiki Git 自动同步脚本，由 cron 定时触发，将本机 Wiki 变更推送到 GitHub。

## 文件位置

`~/.hermes/scripts/wiki-sync.sh`

## 作用

- 每 4 小时自动检测 `~/.hermes/wiki/` 目录变更
- 有变更则 git commit + push
- 无变更则静默退出

## 用法

```bash
# 手动运行
bash ~/.hermes/scripts/wiki-sync.sh

# cron 自动运行（已配置，每 4 小时一次）
```

## cron 配置

| 配置项 | 值 |
|--------|-----|
| 任务名 | wiki-git-sync |
| 调度 | every 4h |
| 远端 | gheshang/hermes-wiki |

## 注意事项

- 冲突处理：cron 模式下没有手动合并机制，遇到冲突会失败。需要手动解决
- 仅 push master 分支
