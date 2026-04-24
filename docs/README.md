# Hermes 辅助脚本

服务器 `~/.hermes/scripts/` 下的辅助脚本工具集，用于知识库管理、自动同步等运维任务。

## 脚本一览

| 脚本 | 用途 | 语言 |
|------|------|------|
| [wiki_ingest.py](wiki_ingest.py.md) | 一键抓取文档入库 Wiki | Python |
| [wiki-sync.sh](wiki-sync.sh.md) | Wiki Git 自动同步 | Shell |

---

## 公共依赖

- `git` — Wiki 版本控制和推送
- `curl` — 文档抓取
- `python3` — wiki_ingest.py 运行环境
- ~/.hermes/wiki/ — 知识库目录，git 仓库（远端：gheshang/hermes-wiki）
- ~/.hermes/.env — API 凭证（wiki_ingest.py 暂不依赖）

---

## 相关知识库

- Wiki 内容索引：`~/.hermes/wiki/index.md`
- Wiki 变更日志：`~/.hermes/wiki/log.md`
- 远端仓库：`github.com/gheshang/hermes-wiki`
