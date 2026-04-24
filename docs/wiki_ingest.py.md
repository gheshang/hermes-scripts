# wiki_ingest.py

一键文档抓取+入库脚本。从任何文档站点抓取原始 markdown，自动生成 Wiki 页面，更新索引并推送到 GitHub。

## 文件位置

`~/.hermes/scripts/wiki_ingest.py`

## 核心流程

按优先级自动选择最优抓取策略：

| 优先级 | 策略 | 适用场景 | 局限性 |
|--------|------|----------|--------|
| 1 | GitHub raw | 已知 GitHub 仓库 docs/ 目录 | 只对公开仓库有效 |
| 2 | 直接 curl | 非 GitHub 的原始文件 | 会标记 HTML（避免灌入渲染页面） |
| 3 | web_extract | 渲染页面 | 截断~5KB |
| 4 | 浏览器 JS | 最后一招 | 慢 |

后续自动完成：
- 原始 markdown → `wiki/raw/articles/`
- 生成 Wiki 页面（自动提取标题/heading/摘要）
- 更新 `index.md` + `log.md`
- git commit + push

## 用法

### 单个 URL

```bash
python3 ~/.hermes/scripts/wiki_ingest.py <URL>
python3 ~/.hermes/scripts/wiki_ingest.py <URL> --name my-page --type entity --tags hermes,reference
```

### Docusaurus 站点批量抓取（推荐方式）

```bash
python3 ~/.hermes/scripts/wiki_ingest.py https://hermes-agent.nousresearch.com \
    --github NousResearch/hermes-agent --docs-path website/docs
```

### 只抓子目录

```bash
python3 ~/.hermes/scripts/wiki_ingest.py https://hermes-agent.nousresearch.com \
    --github NousResearch/hermes-agent --docs-path website/docs/reference
```

### 从 URL 列表文件批量拉取

```bash
# urls.txt 内容格式：一行一个 URL
python3 ~/.hermes/scripts/wiki_ingest.py urls.txt
```

### 只存 raw 不生成 Wiki 页

```bash
python3 ~/.hermes/scripts/wiki_ingest.py <URL> --raw-only
```

### 试运行（只列出会抓什么，不真正执行）

```bash
python3 ~/.hermes/scripts/wiki_ingest.py <URL> --dry-run
```

## 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| `source` | URL、GitHub 目录 URL、或 URL 列表文件 | 必填 |
| `--github` | GitHub 仓库 (owner/repo) | 无 |
| `--docs-path` | 文档路径 | docs |
| `--branch` | Git 分支 | main |
| `--name` | 页面名称 | 自动从 URL 推导 |
| `--type` | 页面类型：entity/concept/comparison/query | concept |
| `--tags` | 逗号分隔的标签 | 无 |
| `--filter` | 只抓路径包含此子串的文件 | 无 |
| `--raw-only` | 只存 raw 不生成 Wiki 页 | false |
| `--no-sync` | 不自动 git push | false |
| `--no-lint` | 不校验 | false |
| `--dry-run` | 只列出不执行 | false |

## 输出文件结构

```
~/.hermes/wiki/
├── raw/articles/        ← 原始文档（按源路径保留）
├── entities/            ← 实体级别 Wiki 页
├── concepts/            ← 概念级别 Wiki 页
├── comparisons/
├── queries/
├── index.md             ← 目录索引（自动更新）
└── log.md               ← 变更日志（自动记录）
```

## 注意事项

- API key 写入 `wiki_ingest.py` 源码？不需要。脚本用 curl + GitHub public API，不依赖 .env
- GitHub API 未认证时有限速（60次/小时），大仓库建议设置 `GITHUB_TOKEN`
- web_extract + 浏览器策略未在独立运行时实现，只会在 Hermes 会话内生效
