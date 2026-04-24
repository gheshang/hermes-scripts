#!/usr/bin/env python3
"""
Wiki Ingest — 优化流程的一键文档抓取+入库

核心流程（按优先级自动尝试）:
  1. GitHub raw → 如果 URL 指向 GitHub 或已知 repo，直接 curl 拉原始 markdown
  2. GitHub API 发现 → 对 Docusaurus/MkDocs 站点，自动找 GitHub 源仓库，遍历目录拉全部 .md
  3. curl 直接拉 → 对可直达的 raw 文件（PDF/markdown/纯文本）
  4. web_extract → 对渲染页面，但会被截断（~5KB），仅作 fallback
  5. 浏览器 JS 提取 → 最后手段，慢但能拿完整内容

自动完成的后续步骤:
  - raw markdown 存入 wiki/raw/articles/
  - 生成 wiki 页（提取标题/摘要/frontmatter）
  - 更新 index.md + log.md
  - git add/commit/push

用法:
  # 单个 URL
  python3 wiki_ingest.py https://raw.githubusercontent.com/owner/repo/main/docs/guide.md

  # Docusaurus 站点（自动发现 GitHub 仓库 + 批量拉取）
  python3 wiki_ingest.py https://hermes-agent.nousresearch.com \
    --github NousResearch/hermes-agent \
    --docs-path website/docs

  # 限定子路径
  python3 wiki_ingest.py https://hermes-agent.nousresearch.com/docs/reference \
    --github NousResearch/hermes-agent \
    --docs-path website/docs/reference

  # 从 URL 列表文件批量拉取
  python3 wiki_ingest.py urls.txt

  # 只抓取不生成 wiki 页
  python3 wiki_ingest.py <url> --raw-only

  # dry run（只列出会拉什么，不实际执行）
  python3 wiki_ingest.py <url> --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

WIKI_DIR = os.path.expanduser("~/.hermes/wiki")
RAW_DIR = os.path.join(WIKI_DIR, "raw/articles")
TODAY = time.strftime("%Y-%m-%d")


# ── 工具函数 ──────────────────────────────────────────────

def run_cmd(cmd, timeout=30):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.returncode


def log(msg, level="info"):
    prefix = {"info": "  ", "ok": "  ✓", "fail": "  ✗", "warn": "  ⚠"}
    print(f"{prefix.get(level, '  ')} {msg}")


# ── 策略1: GitHub raw（最快，拿完整原文）──────────────────────

def github_url_to_raw(url):
    """GitHub blob/tree URL → raw.githubusercontent.com URL"""
    m = re.match(r'https://github\.com/([^/]+)/([^/]+)/(?:blob|tree)/([^/]+)/(.*)', url)
    if m:
        owner, repo, branch, path = m.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    if "raw.githubusercontent.com" in url:
        return url
    return None


def try_github_raw(url, outpath):
    """尝试从 GitHub raw 拉取。返回 (成功, 字节数)"""
    raw_url = github_url_to_raw(url)
    if not raw_url:
        return False, 0
    out, rc = run_cmd(f"curl -sL '{raw_url}' -o '{outpath}' && wc -c '{outpath}' | awk '{{print $1}}'")
    if rc == 0 and out.isdigit() and int(out) > 50:
        return True, int(out)
    # 清理失败文件
    if os.path.exists(outpath):
        os.remove(outpath)
    return False, 0


# ── 策略2: GitHub API 批量发现 ─────────────────────────────

def discover_github_files(owner_repo, docs_path, branch="main"):
    """通过 GitHub API 递归遍历目录，发现所有 .md 文件"""
    api_url = f"https://api.github.com/repos/{owner_repo}/contents/{docs_path}?ref={branch}"
    out, rc = run_cmd(f"curl -sL '{api_url}'", timeout=15)
    if rc != 0:
        return []

    try:
        entries = json.loads(out)
    except json.JSONDecodeError:
        return []
    if not isinstance(entries, list):
        return []

    results = []
    for entry in entries:
        if entry.get("type") == "file" and entry["name"].endswith(".md"):
            results.append({
                "name": entry["name"].replace(".md", ""),
                "raw_url": entry["download_url"],
                "html_url": entry["html_url"],
                "size": entry.get("size", 0),
                "path": entry.get("path", ""),
            })
        elif entry.get("type") == "dir":
            results.extend(discover_github_files(owner_repo, entry["path"], branch))

    return results


def fetch_file(raw_url, outpath):
    """curl 下载文件，返回字节数"""
    out, rc = run_cmd(f"curl -sL '{raw_url}' -o '{outpath}' && wc -c '{outpath}' | awk '{{print $1}}'")
    if rc == 0 and out.isdigit():
        return int(out)
    return 0


# ── 策略3: 直接 curl ──────────────────────────────────────

def try_curl_direct(url, outpath):
    """对非 GitHub 的可直达 URL，curl 拉取"""
    out, rc = run_cmd(f"curl -sL '{url}' -o '{outpath}' && wc -c '{outpath}' | awk '{{print $1}}'")
    if rc == 0 and out.isdigit() and int(out) > 50:
        # 检查是否是 HTML（不是我们要的 markdown）
        with open(outpath, 'r', errors='ignore') as f:
            head = f.read(200)
        if '<html' in head.lower() or '<!doctype' in head.lower():
            os.remove(outpath)
            return False, 0
        return True, int(out)
    if os.path.exists(outpath):
        os.remove(outpath)
    return False, 0


# ── 自动生成 wiki 页 ─────────────────────────────────────

def strip_frontmatter(content):
    return re.sub(r'^---\n.*?\n---\n*', '', content, flags=re.DOTALL).strip()


def extract_summary(raw, max_section=600, max_sections=25, max_total=8000):
    """从 raw markdown 提取结构化摘要"""
    sections = re.split(r'^##\s+', raw, flags=re.MULTILINE)
    parts = []
    for i, section in enumerate(sections):
        if i == 0:
            intro = section.strip()[:800]
            if intro:
                parts.append(intro)
        else:
            lines = section.split('\n')
            heading = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()[:max_section]
            if body:
                parts.append(f"## {heading}\n\n{body}...")
    content = '\n\n'.join(parts[:max_sections])
    if len(content) > max_total:
        content = content[:max_total] + "\n\n> 完整内容见 raw 源文件"
    return content


def generate_wiki_page(name, raw_path, page_type="concept", tags=None, source_url=""):
    """从 raw 文件生成 wiki 页"""
    with open(raw_path, 'r') as f:
        raw = f.read()

    raw_content = strip_frontmatter(raw)
    title_m = re.search(r'^#\s+(.+)$', raw_content, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else name.replace("-", " ").replace("_", " ").title()

    summary = extract_summary(raw_content)
    tag_str = json.dumps(tags or [page_type])

    # 自动找关联页
    related = []
    for pt in ["entities", "concepts"]:
        pdir = os.path.join(WIKI_DIR, pt)
        if os.path.isdir(pdir):
            for fn in os.listdir(pdir)[:20]:
                if fn.endswith(".md") and fn != f"{name}.md":
                    related.append(fn.replace(".md", ""))
    related = related[:5]

    content = f"""---
title: {title}
created: {TODAY}
updated: {TODAY}
type: {page_type}
tags: {tag_str}
sources: [raw/articles/{os.path.basename(raw_path)}]
---

# {title}

{f"源文档：[{title}]({source_url})" if source_url else ""}

{summary}

## 关联

{chr(10).join(f'- [[{r}]]' for r in related) if related else '- (暂无)'}
"""
    wiki_path = os.path.join(WIKI_DIR, f"{page_type}s/{name}.md")
    os.makedirs(os.path.dirname(wiki_path), exist_ok=True)
    with open(wiki_path, 'w') as f:
        f.write(content)
    return wiki_path


# ── 更新 index + log ─────────────────────────────────────

def update_index():
    pages = {"entities": [], "concepts": [], "comparisons": [], "queries": []}
    for ptype in pages:
        pdir = os.path.join(WIKI_DIR, ptype)
        if not os.path.isdir(pdir):
            continue
        for fname in sorted(os.listdir(pdir)):
            if not fname.endswith(".md"):
                continue
            with open(os.path.join(pdir, fname)) as f:
                head = f.read(600)
            m = re.search(r'^title:\s*(.+)$', head, re.MULTILINE)
            title = m.group(1).strip() if m else fname.replace(".md", "")
            m2 = re.search(r'^#\s+.+\n\n(.+)', head, re.MULTILINE)
            desc = m2.group(1).strip()[:80] if m2 else ""
            pages[ptype].append((fname.replace(".md", ""), title, desc))

    total = sum(len(v) for v in pages.values())
    lines = [f"# Wiki Index\n\n> Last updated: {TODAY} | Total pages: {total}\n"]
    for ptype, items in pages.items():
        if items:
            lines.append(f"\n## {ptype.capitalize()}\n")
            for slug, title, desc in items:
                lines.append(f"- [[{slug}]] — {desc}")

    with open(os.path.join(WIKI_DIR, "index.md"), 'w') as f:
        f.write('\n'.join(lines))
    return total


def append_log(action, subject, details=""):
    log_path = os.path.join(WIKI_DIR, "log.md")
    with open(log_path, 'a') as f:
        f.write(f"\n## [{TODAY}] {action} | {subject}\n")
        if details:
            f.write(f"- {details}\n")


def git_sync():
    os.chdir(WIKI_DIR)
    run_cmd("git add -A")
    out, rc = run_cmd("git diff --cached --quiet")
    if rc == 0:
        log("No changes to sync.")
        return
    ts = time.strftime("%H%M%S")
    run_cmd(f"git commit -m 'ingest: {TODAY}_{ts}'")
    out, rc = run_cmd("git push origin master")
    if rc == 0:
        log("Pushed to GitHub.", "ok")
    else:
        log(f"Push failed: {out}", "fail")


# ── lint 校验 ─────────────────────────────────────────────

def lint_wiki():
    errors, warnings = [], []
    for ptype in ["entities", "concepts", "comparisons", "queries"]:
        pdir = os.path.join(WIKI_DIR, ptype)
        if not os.path.isdir(pdir):
            continue
        for fname in sorted(os.listdir(pdir)):
            if not fname.endswith(".md"):
                continue
            slug = fname.replace(".md", "")
            with open(os.path.join(pdir, fname)) as f:
                content = f.read()
            if not re.match(r'^---\n.*?\n---', content, re.DOTALL):
                errors.append(f"{slug}: missing frontmatter")
                continue
            for field in ["title", "created", "type", "tags"]:
                if f"{field}:" not in content[:500]:
                    errors.append(f"{slug}: missing '{field}'")
            if not re.search(r'^#\s+', content, re.MULTILINE):
                errors.append(f"{slug}: missing # heading")
            wikilinks = re.findall(r'\[\[([^\]]+)\]\]', content)
            if not wikilinks:
                warnings.append(f"{slug}: no [[wikilinks]]")
            for link in wikilinks:
                link_slug = link.split("|")[0].strip().lower().replace(" ", "-")
                found = any(
                    os.path.exists(os.path.join(WIKI_DIR, pt, f"{link_slug}.md"))
                    for pt in ["entities", "concepts", "comparisons", "queries"]
                )
                if not found:
                    warnings.append(f"{slug}: broken link [[{link}]]")
    return errors, warnings


# ── 主流程 ────────────────────────────────────────────────

def ingest_url(url, name=None, page_type="concept", tags=None, raw_only=False):
    """单 URL 抓取（自动选最优策略）"""
    os.makedirs(RAW_DIR, exist_ok=True)
    if not name:
        parsed = urlparse(url)
        name = os.path.splitext(os.path.basename(parsed.path))[0] or parsed.hostname.replace(".", "-")
        name = re.sub(r'[^a-z0-9-]', '', name.lower().replace(" ", "-"))
        if not name:
            name = f"doc-{int(time.time())}"

    raw_path = os.path.join(RAW_DIR, f"{name}.md")
    source = ""

    # 策略1: GitHub raw
    ok, size = try_github_raw(url, raw_path)
    if ok:
        source = "github-raw"
        log(f"{name}: {size} bytes via GitHub raw", "ok")

    # 策略2: 直接 curl
    if not ok:
        ok, size = try_curl_direct(url, raw_path)
        if ok:
            source = "curl"
            log(f"{name}: {size} bytes via curl", "ok")

    # 策略3: web_extract（需要 hermes 上下文，独立运行时跳过）
    if not ok:
        log(f"{name}: all fetch strategies failed", "fail")
        log(f"  Try providing GitHub raw URL instead", "warn")
        return False

    if raw_only:
        return True

    # 自动生成 wiki 页
    wiki_path = generate_wiki_page(name, raw_path, page_type=page_type, tags=tags, source_url=url)
    log(f"Wiki page: {wiki_path}", "ok")
    append_log("ingest", name, f"Source: {url} | {size} bytes | Method: {source}")
    return True


def ingest_github_dir(github_repo, docs_path, branch="main", page_type="concept", tags=None,
                      filter_path=None, dry_run=False, raw_only=False):
    """GitHub 仓库目录批量抓取"""
    log(f"Discovering .md files in {github_repo}/{docs_path}...")
    files = discover_github_files(github_repo, docs_path, branch)

    if filter_path:
        files = [f for f in files if filter_path in f["path"]]

    log(f"Found {len(files)} .md files")

    if dry_run:
        for f in files:
            print(f"  {f['name']:40s} {f['size']:>8d} bytes  {f['path']}")
        return

    created, failed = 0, 0
    for f in files:
        name = f["name"]
        # 子目录前缀避免重名
        parent = os.path.basename(os.path.dirname(f["path"])).replace("_", "-")
        if parent and parent not in ("docs", "articles", "raw"):
            name = f"{parent}-{name}"

        raw_path = os.path.join(RAW_DIR, f"{name}.md")
        size = fetch_file(f["raw_url"], raw_path)

        if size > 50:
            log(f"{name}: {size} bytes", "ok")
            if not raw_only:
                generate_wiki_page(name, raw_path, page_type=page_type, tags=tags, source_url=f["html_url"])
            append_log("ingest", name, f"GitHub: {f['html_url']} | {size} bytes")
            created += 1
        else:
            log(f"{name}: FAILED", "fail")
            failed += 1

    log(f"Done: {created} fetched, {failed} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Wiki Ingest — 一键文档抓取+入库（优化流程版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # Docusaurus 站点批量抓取（推荐方式）
  python3 wiki_ingest.py https://hermes-agent.nousresearch.com \\
    --github NousResearch/hermes-agent --docs-path website/docs

  # 只抓 reference 子目录
  python3 wiki_ingest.py https://hermes-agent.nousresearch.com \\
    --github NousResearch/hermes-agent --docs-path website/docs/reference

  # 单个 GitHub raw 文件
  python3 wiki_ingest.py https://raw.githubusercontent.com/owner/repo/main/docs/guide.md

  # 从 URL 列表文件批量拉取
  python3 wiki_ingest.py urls.txt

  # dry run
  python3 wiki_ingest.py <url> --dry-run
""")
    parser.add_argument("source", help="URL, GitHub repo 目录, 或 URL 列表文件")
    parser.add_argument("--github", help="GitHub 仓库 (owner/repo)，配合文档站使用")
    parser.add_argument("--docs-path", default="docs", help="GitHub 仓库中的文档路径")
    parser.add_argument("--branch", default="main", help="Git 分支")
    parser.add_argument("--name", help="页面名称（自动从 URL 推导）")
    parser.add_argument("--type", default="concept", choices=["entity", "concept", "comparison", "query"])
    parser.add_argument("--tags", default=None, help="逗号分隔的标签")
    parser.add_argument("--filter", default=None, help="只抓路径包含此子串的文件")
    parser.add_argument("--raw-only", action="store_true", help="只存 raw 不生成 wiki 页")
    parser.add_argument("--no-sync", action="store_true", help="不自动 git push")
    parser.add_argument("--no-lint", action="store_true", help="不校验")
    parser.add_argument("--dry-run", action="store_true", help="只列出会抓什么，不实际执行")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    # URL 列表文件
    if os.path.isfile(args.source):
        with open(args.source) as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        log(f"Loaded {len(urls)} URLs from {args.source}")
        for url in urls:
            ingest_url(url, page_type=args.type, tags=tags, raw_only=args.raw_only)

    # GitHub 仓库目录批量抓取
    elif args.github:
        ingest_github_dir(
            args.github, args.docs_path, args.branch,
            page_type=args.type, tags=tags,
            filter_path=args.filter, dry_run=args.dry_run, raw_only=args.raw_only,
        )

    # 单个 URL
    else:
        ingest_url(args.source, name=args.name, page_type=args.type, tags=tags, raw_only=args.raw_only)

    # 后续：更新 index
    total = update_index()
    log(f"Index updated: {total} pages total")

    # 后续：lint
    if not args.no_lint:
        errors, warnings = lint_wiki()
        if errors:
            log(f"Lint: {len(errors)} errors", "fail")
            for e in errors:
                log(f"  {e}", "fail")
        if warnings:
            log(f"Lint: {len(warnings)} warnings", "warn")
            for w in warnings:
                log(f"  {w}", "warn")
        if not errors and not warnings:
            log("Lint: all clean", "ok")

    # 后续：git sync
    if not args.no_sync and not args.dry_run:
        git_sync()


if __name__ == "__main__":
    main()
