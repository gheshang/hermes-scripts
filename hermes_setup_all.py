#!/usr/bin/env python3
"""
Hermes Agent 全量配置脚本（上河一号定制版）
合并 token 优化 + 功能配置，16 大项可选
四层架构：核心配置 → Token 优化 → 成本控制 → 进阶功能
基于官方文档（253篇）+ 社区优化方案（OnlyTerp/Reddit）持续迭代
"""

import subprocess, os, stat, shlex

ENV_PATH = os.path.expanduser("~/.hermes/.env")


# ━━━ 工具函数 ━━━

def run(cmd_args, background=False):
    """安全执行命令，列表传参防注入"""
    print(f"  执行: {' '.join(cmd_args)}")
    if background:
        subprocess.Popen(
            cmd_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("  ✓ 后台启动")
        return True
    try:
        r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)
    except Exception as e:
        print(f"  ⚠ 失败: {e}")
        return False
    if r.returncode != 0:
        print(f"  ⚠ 失败: {r.stderr.strip() or r.stdout.strip()}")
    else:
        print("  ✓ 成功")
    return r.returncode == 0


def ask(prompt, default=""):
    val = input(f"  {prompt} [{f'默认:{default}' if default else '回车跳过'}]: ").strip()
    return val if val else default


def ask_int(prompt, default, min_val=None, max_val=None):
    raw = ask(prompt, str(default))
    try:
        val = int(raw)
        if min_val is not None and val < min_val:
            print(f"  ⚠ 值不能小于 {min_val}，回退默认 {default}")
            return default
        if max_val is not None and val > max_val:
            print(f"  ⚠ 值不能大于 {max_val}，回退默认 {default}")
            return default
        return val
    except ValueError:
        print(f"  ⚠ 非数字输入，回退默认 {default}")
        return default


def ask_float(prompt, default, min_val=0.0, max_val=1.0):
    raw = ask(prompt, str(default))
    if not raw:
        return default
    try:
        val = float(raw)
        if min_val <= val <= max_val:
            return val
        print(f"  ⚠ 范围 {min_val}~{max_val}，回退默认 {default}")
        return default
    except ValueError:
        print(f"  ⚠ 非数字输入，回退默认 {default}")
        return default


def ask_yn(prompt, default="n"):
    val = ask(prompt, default)
    return val.lower() in ("y", "yes", "是")


def write_env(key, value):
    """写入 .env 单个键值，精确匹配 key= 替换，权限 0600"""
    if not value:
        return
    lines = []
    found = False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        parts = stripped.split("=", 1)
        if parts[0] == key:
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)
    os.chmod(ENV_PATH, stat.S_IRUSR | stat.S_IWUSR)
    print(f"  ✓ {key} 已写入 ~/.hermes/.env (权限 0600)")


def write_env_batch(pairs):
    """批量写入 .env，保留注释和空行，权限 0600"""
    lines = []
    existing_keys = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            for i, line in enumerate(f):
                lines.append(line.rstrip("\n"))
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, _, _ = stripped.partition("=")
                    existing_keys[k.strip()] = i
    for k, v in pairs:
        if k in existing_keys:
            lines[existing_keys[k]] = f"{k}={v}"
        else:
            lines.append(f"{k}={v}")
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_PATH, stat.S_IRUSR | stat.S_IWUSR)
    print(f"  ✓ {len(pairs)} 个键值已写入 ~/.hermes/.env (权限 0600)")


def set_auxiliary(task, provider, model, base_url="", api_key_env=None):
    """配置单个 auxiliary 任务，API Key 写 .env"""
    run(["hermes", "config", "set", f"auxiliary.{task}.provider", provider])
    run(["hermes", "config", "set", f"auxiliary.{task}.model", model])
    if base_url:
        run(["hermes", "config", "set", f"auxiliary.{task}.base_url", base_url])
    if api_key_env and isinstance(api_key_env, dict) and api_key_env.get("value"):
        write_env(api_key_env["name"], api_key_env["value"])


def validate_name(name):
    """校验名称：非空、无空格、只含字母数字连字符下划线"""
    if not name:
        print("  ⚠ 名称不能为空")
        return False
    if " " in name:
        print("  ⚠ 名称不能含空格")
        return False
    if not name.replace("-", "").replace("_", "").isalnum():
        print("  ⚠ 名称只能含字母、数字、连字符、下划线")
        return False
    return True


# ━━━ 第一层：核心配置 ━━━

def feat1_auxiliary():
    """副驾模型 — 两种模式：批量配 / 逐任务配"""
    print("\n┏━ 1. 副驾模型（auxiliary）")
    print("┃ 不配 = 所有副驾走主模型 = 用瑞士军刀削铅笔")
    print("┃ 配好 = 成本降 60%-70%，延迟快一倍")
    print("┗" + "━" * 50)

    print("\n  两种配置方式：")
    print("  a) 批量配 — 重/轻两档，一次性覆盖所有任务")
    print("  b) 逐任务配 — 精细控制每个副驾的模型和超时")

    mode = ask("选哪种 (a/b)", "a")

    if mode == "a":
        # 批量模式
        print("\n  --- 重任务模型 ---")
        print("  任务：vision, web_extract, flush_memories")
        heavy_provider = ask("重任务厂商 (如 gemini/openrouter/anthropic/custom)", "custom")
        heavy_model = ask("重任务模型名 (如 gemini-2.5-flash)", "gemini-2.5-flash")
        heavy_base_url = ask("Base URL (custom 必填，其他留空)", "")
        heavy_api_key = ask("API Key (custom 必填，其他留空，写入.env)", "")

        print("\n  --- 轻任务模型 ---")
        print("  任务：compression, session_search, approval, skills_hub, mcp")
        light_provider = ask("轻任务厂商", "custom")
        light_model = ask("轻任务模型名 (如 gemini-2.5-flash-lite)", "gemini-2.5-flash-lite")
        light_base_url = ask("Base URL (custom 必填，其他留空)", "")
        light_api_key = ask("API Key (custom 必填，其他留空，写入.env)", "")

        HEAVY = ["vision", "web_extract", "flush_memories"]
        LIGHT = ["compression", "session_search", "approval", "skills_hub", "mcp"]

    heavy_key_env = {"name": "AUX_HEAVY_API_KEY", "value": heavy_api_key} if heavy_api_key else None
    light_key_env = {"name": "AUX_LIGHT_API_KEY", "value": light_api_key} if light_api_key else None

    # 批量写 env，避免逐次 IO
    env_pairs = []
    if heavy_api_key:
        env_pairs.append(("AUX_HEAVY_API_KEY", heavy_api_key))
    if light_api_key:
        env_pairs.append(("AUX_LIGHT_API_KEY", light_api_key))
    if heavy_base_url:
        env_pairs.append(("AUX_HEAVY_BASE_URL", heavy_base_url))
    if light_base_url:
        env_pairs.append(("AUX_LIGHT_BASE_URL", light_base_url))

    print("\n 正在写入配置...")
    for task in HEAVY:
        set_auxiliary(task, heavy_provider, heavy_model, heavy_base_url)
        if heavy_key_env:
            run(["hermes", "config", "set", f"auxiliary.{task}.api_key_env", "AUX_HEAVY_API_KEY"])
    for task in LIGHT:
        set_auxiliary(task, light_provider, light_model, light_base_url)
        if light_key_env:
            run(["hermes", "config", "set", f"auxiliary.{task}.api_key_env", "AUX_LIGHT_API_KEY"])

    if env_pairs:
        write_env_batch(env_pairs)

    else:
        # 逐任务模式
        tasks = ["vision", "web_extract", "flush_memories",
                 "compression", "session_search", "approval", "skills_hub", "mcp"]
        print(f"\n  可配任务：{', '.join(tasks)}")
        print("  重任务（需理解力）：vision, web_extract, flush_memories")
        print("  轻任务（纯分类/搜索）：compression, session_search, approval, skills_hub, mcp")

        while True:
            task = ask("配置哪个任务？（回车退出）", "")
            if not task:
                break
            if task not in tasks:
                print(f"  ⚠ 未知任务 {task}，可选：{', '.join(tasks)}")
                continue
            provider = ask("provider（auto/custom/zai 等）", "custom")
            model = ask("model", "")
            if not model:
                print("  ⚠ model 不能为空，跳过")
                continue
            base_url = ""
            if provider == "custom":
                base_url = ask("base_url（custom 必填）", "")
                if not base_url:
                    print("  ⚠ custom 厂商必须填 base_url，跳过")
                    continue
            timeout = ask_int("timeout（秒）", 30, min_val=5, max_val=600)
            run(["hermes", "config", "set", f"auxiliary.{task}.provider", provider])
            run(["hermes", "config", "set", f"auxiliary.{task}.model", model])
            if base_url:
                run(["hermes", "config", "set", f"auxiliary.{task}.base_url", base_url])
            run(["hermes", "config", "set", f"auxiliary.{task}.timeout", str(timeout)])

            env_pairs = []
            if provider == "custom":
                api_key = ask(f"auxiliary.{task} 的 API key（回车跳过）", "")
                if api_key:
                    env_var = f"AUX_{task.upper()}_API_KEY"
                    env_pairs.append((env_var, api_key))
                    run(["hermes", "config", "set", f"auxiliary.{task}.api_key_env", env_var])
            if env_pairs:
                write_env_batch(env_pairs)
            print(f"  ✓ auxiliary.{task} 已配置")

            if not ask_yn("继续配置下一个副驾？(y/n)", "n"):
                break


def feat2_search():
    """搜索后端"""
    print("\n┏━ 2. 搜索后端")
    print("┃ 默认是聋的，需要配搜索才能联网")
    print("┗" + "━" * 50)

    print("\n  可选后端：")
    print("  1. tavily — 专为 AI 设计，结构化结果，月 1000 次免费")
    print("  2. duckduckgo — 零成本兜底，不需 API key")
    print("  3. 跳过")

search_choice = ask("选哪个 (1/2/3)", "2")
if search_choice == "1":
    tavily_key = ask("Tavily API Key (去 tavily.com 注册拿)", "")
    if tavily_key:
        write_env("TAVILY_API_KEY", tavily_key)
        run(["hermes", "config", "set", "web.tavily_api_key_env", "TAVILY_API_KEY"])
        run(["hermes", "config", "set", "web.backend", "tavily"])
        run(["hermes", "config", "set", "web.fallback_backend", "duckduckgo"])
    else:
        print(" ⚠ Tavily Key 为空，回退到 DuckDuckGo")
        run(["hermes", "config", "set", "web.backend", "duckduckgo"])
elif search_choice == "2":
    run(["hermes", "config", "set", "web.backend", "duckduckgo"])
else:
    print(" 跳过搜索配置。")


def feat3_memory():
    """记忆系统"""
    print("\n┏━ 3. 记忆系统")
    print("┃ 三层：内置记忆(默认开) → 外部Provider(可选) → Session Search(默认开)")
    print("┗" + "━" * 50)

    print("\n  内置记忆参数（当前默认值一般够用，重度使用可调）：")
    mem_limit = ask_int("memory_char_limit (MEMORY.md 上限字符)", 2200, min_val=100)
    user_limit = ask_int("user_char_limit (USER.md 上限字符)", 1375, min_val=100)
    nudge = ask_int("nudge_interval (每N轮提醒存记忆)", 10, min_val=1)
    flush = ask_int("flush_min_turns (至少N轮才触发退出刷新)", 6, min_val=1)

    run(["hermes", "config", "set", "memory.memory_enabled", "true"])
    run(["hermes", "config", "set", "memory.user_profile_enabled", "true"])
    run(["hermes", "config", "set", "memory.memory_char_limit", str(mem_limit)])
    run(["hermes", "config", "set", "memory.user_char_limit", str(user_limit)])
    run(["hermes", "config", "set", "memory.nudge_interval", str(nudge)])
    run(["hermes", "config", "set", "memory.flush_min_turns", str(flush)])

    print("\n  外部 Memory Provider（可选，建议先跑两周再决定）：")
    print("  支持: honcho, mem0, hindsight 等")
    if ask_yn("是否现在配外部记忆？(y/n)", "n"):
        print("  运行: hermes memory setup （交互式向导）")
        run(["hermes", "memory", "setup"])


# ━━━ 第二层：Token 优化 ━━━

def feat4_credential_pool():
    """密钥池策略 — 同 provider 多 key 轮转 + OAuth"""
    print("\n┏━ 4. 密钥池策略 (credential_pool_strategies)")
    print("┃ 避免单密钥耗尽导致任务中断，浪费已建立的 context")
    print("┃ 与 fallback_provider 的区别：密钥池 = 同 provider 轮转，fallback = 跨 provider 切换")
    print("┗" + "━" * 50)

    print("  策略选项：")
    print("  fill_first (默认) — 用完一个再用下一个，不均衡")
    print("  least_used (推荐) — 始终选请求量最少的 key，均衡负载")
    print("  round_robin — 轮询循环")
    print("  random — 随机选择")
    if not ask_yn("是否配置？(y/n)", "n"):
        return
    provider = ask("配置哪个 provider 的密钥池策略？", "zai")
    strategy = ask("策略 (least_used/round_robin/random/fill_first)", "least_used")
    if strategy not in ("least_used", "round_robin", "random", "fill_first"):
        print(f" ⚠ 无效策略 '{strategy}'，回退默认 least_used")
        strategy = "least_used"
    run(["hermes", "config", "set", f"credential_pool_strategies.{provider}", strategy])
    print(f"  ✓ credential_pool_strategies.{provider} = {strategy}")

    print("\n  添加密钥到池：")
    print("  方式 A：交互向导（推荐）")
    print("  方式 B：手动逐个添加")
    auth_mode = ask("选哪种 (A/B)", "A")
    if auth_mode.lower() == "a":
        print("  运行: hermes auth （交互向导，支持 API key + OAuth）")
        if ask_yn("现在运行？(y/n)", "y"):
            run(["hermes", "auth"])
    else:
        keys_added = []
        while True:
            env_var = ask(f" 密钥环境变量名（如 GLM_API_KEY, ZAI_API_KEY_{len(keys_added)+1}）", "")
            if not env_var:
                break
            key_val = input(f" 输入 {env_var} 的值: ").strip()
            if not key_val:
                print(" 值为空，跳过")
                continue
            keys_added.append((env_var, key_val))
            if not ask_yn("继续添加下一个密钥？(y/n)", "n"):
                break

        base_url = ask("统一 base_url（回车跳过）", "")
        if base_url:
            keys_added.append((f"{provider.upper()}_BASE_URL", base_url))
            run(["hermes", "config", "set", "model.base_url", base_url])

        if keys_added:
            write_env_batch(keys_added)
            print(" 提示：运行 hermes auth add 将密钥 seed 到池中")

    print("\n  检查池状态：hermes auth list")
    print("  OAuth 凭证（Anthropic/Copilot）：hermes auth add <provider> --type oauth")


def feat5_context_window():
    """上下文窗口 + 最大输出"""
    print("\n┏━ 5. 上下文窗口 & 最大输出")
    print("┃ 不设 context_length → 压缩算法无法精准计算触发时机")
    print("┃ 不设 max_tokens → 模型输出可能被截断，浪费已花的输入 token")
    print("┗" + "━" * 50)

    print("  常见值：GLM-5 = 200000/131072, Claude = 200000/16384, GPT-4o = 128000/16384")

    if ask_yn("设置 model.context_length？(y/n)", "y"):
        val = ask_int("context_length（tokens数）", 200000, min_val=1000, max_val=10000000)
        run(["hermes", "config", "set", "model.context_length", str(val)])

    if ask_yn("设置 model.max_tokens？(y/n)", "y"):
        val = ask_int("max_tokens", 131072, min_val=256, max_val=10000000)
        run(["hermes", "config", "set", "model.max_tokens", str(val)])


def feat6_compression():
    """上下文压缩（双系统 + 可替换引擎）"""
    print("\n┏━ 6. 上下文压缩")
    print("┃ 双压缩系统：Gateway 安全网 85% + Agent 主压缩 50%（可调）")
    print("┃ 引擎可替换：默认 compressor（有损总结），可换 LCM（无损）等插件")
    print("┗" + "━" * 50)

    # 先确保开启
    if ask_yn("确保 compression.enabled = true？(y/n)", "y"):
        run(["hermes", "config", "set", "compression.enabled", "true"])

    # 引擎选择
    print("\n  压缩引擎：")
    print("  compressor（默认）— 有损总结，用便宜模型压缩上下文")
    print("  lcm — 无损上下文管理（需插件，详见 context-engine-plugin 文档）")
    print("  其他插件 — 由社区/第三方提供")
    engine = ask("选择 context.engine", "compressor")
    run(["hermes", "config", "set", "context.engine", engine])
    print(f" ✓ context.engine = {engine}")
    if engine != "compressor":
        print(" 注意：插件引擎需先安装，否则 fallback 到 compressor")

    if not ask_yn("调整压缩参数？(y/n)", "y"):
        return

    print("  官方默认值：threshold=0.50, target_ratio=0.20, protect_last_n=20")
    print("  知乎建议值：threshold=0.75, target_ratio=0.25, protect_last_n=30")
    print("  高频使用建议 threshold=0.75（减少压缩次数），保护消息 30+")

    threshold_pct = ask_int(
        "compression.threshold（上下文占用%达多少触发压缩，如75=75%）",
        75, min_val=10, max_val=95
    )
    target_ratio_pct = ask_int(
        "compression.target_ratio（压缩后保留原内容%，如25=保留25%）",
        25, min_val=10, max_val=90
    )
    protect_n = ask_int(
        "compression.protect_last_n（保护最近N条消息不参与压缩）",
        30, min_val=5, max_val=100
    )
    run(["hermes", "config", "set", "compression.threshold", str(threshold_pct / 100)])
    run(["hermes", "config", "set", "compression.target_ratio", str(target_ratio_pct / 100)])
    run(["hermes", "config", "set", "compression.protect_last_n", str(protect_n)])
    print(f"  ✓ threshold={threshold_pct/100}, target_ratio={target_ratio_pct/100}, protect_last_n={protect_n}")

    print("\n  压缩总结模型（用便宜模型做总结，主模型省 10 倍）：")
    print("  推荐便宜模型：gemini-2.5-flash / glm-4-flash / cerebras/llama-3.1-70b")
    if ask_yn("是否配置压缩总结模型？(y/n)", "n"):
        summary_provider = ask("summary provider（auto/zai/custom/openrouter 等）", "auto")
        summary_model = ask("summary model（如 gemini-2.5-flash）", "gemini-2.5-flash")
        run(["hermes", "config", "set", "compression.summary_provider", summary_provider])
        run(["hermes", "config", "set", "compression.summary_model", summary_model])
        env_pairs = []
        if summary_provider == "custom":
            summary_base_url = ask("summary base_url（custom 必填）", "")
            if summary_base_url:
                run(["hermes", "config", "set", "compression.summary_base_url", summary_base_url])
            summary_api_key = ask("summary API key（写入.env）", "")
            if summary_api_key:
                env_pairs.append(("AUX_COMPRESSION_API_KEY", summary_api_key))
                run(["hermes", "config", "set", "auxiliary.compression.api_key_env", "AUX_COMPRESSION_API_KEY"])
        if env_pairs:
            write_env_batch(env_pairs)


def feat7_token_monitor():
    """Token 监控工具"""
    print("\n┏━ 7. Token 监控工具")
    print("┃ 看钱花在哪")
    print("┗" + "━" * 50)

    print("\n  可选工具：")
    print("  1. tokscale — 一条命令看全局 token 消耗")
    print("  2. hermes-dashboard — 社区做的 token 面板，按组件拆解")
    print("  3. hermes dashboard — 官方 Web Dashboard")
    print("  4. 跳过")

    monitor = ask("选哪个 (1/2/3/4)", "4")
    if monitor == "1":
        if ask_yn("安装 tokscale？(需要 pip)(y/n)", "y"):
            run(["pip", "install", "tokscale"])
        print("  使用：tokscale --hermes")
    elif monitor == "2":
        if ask_yn("安装 hermes-dashboard？(需要 pip)(y/n)", "y"):
            run(["pip", "install", "hermes-dashboard"])
        print("  使用：hermes-dashboard")
    elif monitor == "3":
        print(" 启动：hermes dashboard")
        if ask_yn("现在启动？(y/n)", "n"):
            run(["hermes", "dashboard"], background=True)

    print("\n  RTK (Rust Token Killer)：把终端命令 token 消耗压掉 80-90%")
    if ask_yn("安装 RTK？(需要 cargo)(y/n)", "n"):
        run(["cargo", "install", "rtk"])
        if ask_yn("启用 RTK？(y/n)", "y"):
            run(["hermes", "config", "set", "terminal.compressor", "rtk"])


# ━━━ 第三层：进阶功能 ━━━

def feat8_profile():
    """Profile 分身"""
    print("\n┏━ 8. Profile 分身")
    print("┃ 每个分身独立记忆/人格/配置，互不干扰")
    print("┗" + "━" * 50)

    if not ask_yn("是否创建新 Profile？(y/n)", "n"):
        print("  跳过。")
        return

    profile_name = ask("Profile 名称 (如 work/life/coder)", "work")
    if not validate_name(profile_name):
        print("  ⚠ 名称不合法，跳过 Profile 创建。")
        return

    use_clone = ask_yn("从当前配置克隆？(推荐 y，否则空白分身需重新配)", "y")
    cmd = ["hermes", "profile", "create", profile_name]
    if use_clone:
        cmd.append("--clone")
    if not run(cmd):
        print(" ⚠ Profile 创建失败，跳过后续配置")
        return

    if ask_yn("是否设为默认 Profile？(y/n)", "n"):
        run(["hermes", "profile", "use", profile_name])

    print("  管理命令：")
    print("  hermes profile list — 查看所有分身")
    print("  hermes -p <name> chat — 临时切换")
    print("  hermes profile use <name> — 粘性切换为默认")
    print("  hermes profile delete <name> — 删除")


def feat9_skill_evolution():
    """Skill 自主进化"""
    print("\n┏━ 9. Skill 自主进化")
    print("┃ Agent 在对话中自动沉淀可复用经验为新 skill")
    print("┗" + "━" * 50)

    if not ask_yn("启用 Skill 自主进化？(y/n)", "y"):
        run(["hermes", "config", "set", "creation_nudge_interval", "0"])
        print("  已关闭自主进化（interval=0）。")
        return

    interval = ask_int(
        "creation_nudge_interval（每N次工具调用触发一次审查，0=关闭）",
        15, min_val=0, max_val=100
    )
    run(["hermes", "config", "set", "creation_nudge_interval", str(interval)])

    if interval > 0:
        print("  进化机制：")
        print("  工具调用达阈值 → 后台 fork review agent")
        print("  → 审查对话有无非平凡经验 → update/create/nothing")
        print("  → 结果打印 Skill created: xxx，不打断你")

    print("  手动装 skill：")
    print("  hermes skills install wondelai/skills — 380+ 跨平台 skill")
    print("  hermes skills install <owner/repo> — 从 GitHub 装")


def feat10_delegation():
    """子 Agent 并发 + 深度控制"""
    print("\n┏━ 10. 子 Agent 并发")
    print("┃ 派多路 agent 同时干活，结果合并返回")
    print("┃ v0.11.0 新增：orchestrator 角色可再 spawn 自己的 worker")
    print("┗" + "━" * 50)

    print("  Hermes 内置 delegate_task 工具，无需额外配置。")
    print("  角色：leaf（默认，干活完返回）vs orchestrator（可再派子 agent）")
    print("  用法：直接告诉 Hermes ——")
    print('  "帮我派3路agent，一个查GitHub、一个查X、一个查Reddit"')
    print("  建议：2-3 个并发最稳，子 agent 不继承上下文，指令要一次塞够。")

    if ask_yn("是否配置默认并发上限？(y/n)", "n"):
        max_concurrent = ask_int("最大并发子 agent 数", 3, min_val=1, max_val=10)
        run(["hermes", "config", "set", "delegation.max_concurrent_children", str(max_concurrent)])
        print(f" ✓ max_concurrent_children = {max_concurrent}")

    if ask_yn("是否配置最大 spawn 深度？(y/n)", "n"):
        max_depth = ask_int("delegation.max_spawn_depth（orchestrator 最多嵌套几层，默认2）", 2, min_val=1, max_val=5)
        run(["hermes", "config", "set", "delegation.max_spawn_depth", str(max_depth)])
        print(f"  ✓ max_spawn_depth = {max_depth}")


def feat11_cron():
    """Cron 定时任务"""
    print("\n┏━ 11. Cron 定时任务")
    print("┃ 让 agent 定时自己干活，如每天早8点总结新闻")
    print("┗" + "━" * 50)

    print("  前置条件：hermes gateway 必须在跑，cron 才会按时触发")
    if ask_yn("现在启动 hermes gateway？(y/n)", "n"):
        if ask_yn("是否后台启动？(y/n)", "y"):
            run(["hermes", "gateway"], background=True)
        else:
            run(["hermes", "gateway"])

    if ask_yn("是否创建一个示例 Cron 任务？(y/n)", "n"):
        print(" 示例：每天早8点总结AI新闻")
        schedule = ask("Cron 表达式或自然语言（如 '0 8 * * *' 或 '每天早上8点'）", "0 8 * * *")
        prompt_text = ask("任务指令", "总结昨天AI圈最重要的3条新闻")
        target = ask("结果推送到哪（如 telegram/discord/local，留空=仅保存）", "local")
        if ask_yn("现在创建？(y/n)", "y"):
            run(["hermes", "cron", "create", "--schedule", schedule, "--prompt", prompt_text, "--deliver", target])
        else:
            print(" 建议直接跟 Hermes 说：")
            print(f'  "{schedule} {prompt_text}"')

    print("  管理命令：")
    print("  hermes cron list — 查看所有定时任务")
    print("  hermes cron pause — 暂停")
    print("  hermes cron resume — 恢复")
    print("  hermes cron remove — 删除")


def feat12_ecosystem():
    """生态工具"""
    print("\n┏━ 12. 生态工具")
    print("┃ 批量装 skill、装文档处理工具")
    print("┗" + "━" * 50)

    print("\n  --- Skill 库 ---")
    print("  1. wondelai/skills — 380+ 跨平台 skill")
    print("  2. awesome-agent-skills — 1000+ skills 社区合集")
    print("  3. 两个都装")
    print("  4. 跳过")

    skill_choice = ask("选哪个 (1/2/3/4)", "4")
    if skill_choice in ("1", "3"):
        if ask_yn("安装 wondelai/skills？(y/n)", "y"):
            run(["hermes", "skills", "install", "wondelai/skills"])
    if skill_choice in ("2", "3"):
        if ask_yn("安装 awesome-agent-skills？(y/n)", "y"):
            run(["hermes", "skills", "install", "nicholasgriffintn/awesome-agent-skills"])

    print("\n  --- 文档处理工具 ---")
    print("  Pandoc：万能格式转换（PDF/DOCX/HTML/EPUB → Markdown）")
    if ask_yn("安装 Pandoc？(y/n)", "n"):
        run(["sudo", "apt-get", "install", "-y", "pandoc"])

    print("  Marker：PDF 转 Markdown 效果优于 Pandoc（需 pip）")
    if ask_yn("安装 Marker？(y/n)", "n"):
        run(["pip", "install", "marker-pdf"])

    print("\n  生态导航：")
    print("  awesome-hermes-agent: https://github.com/awesome-hermes-agent")
    print("  生态地图: https://hermes-ecosystem.vercel.app")
    print("  OnlyTerp/hermes-optimization-guide: https://github.com/OnlyTerp/hermes-optimization-guide")
    print("  （21 章优化指南 + 13 个可安装 skill + 5 套配置模板 + 基准测试）")


# ━━━ 第四层：成本控制 ━━━

def feat13_provider_routing():
    """Provider Routing — OpenRouter 下控制路由到最便宜的 provider"""
    print("\n┏━ 13. Provider Routing (OpenRouter 专用)")
    print("┃ 控制请求路由到哪个底层 provider，优化价格/速度/隐私")
    print("┃ ⚠ 仅在使用 OpenRouter 时生效，直连 provider 无效")
    print("┗" + "━" * 50)

    print("\n  核心配置：")
    print("  sort: price（最便宜）/ throughput（最快）/ latency（最低首token延迟）")
    print("  only: 白名单 — 只用指定 provider")
    print("  ignore: 黑名单 — 永远不用指定 provider")
    print("  order: 优先级顺序 — 指定 provider 排名")
    print("  data_collection: deny（禁止用你的数据训练）")
    print("  require_parameters: true（只用支持所有参数的 provider）")

    if not ask_yn("是否配置 provider routing？(y/n)", "n"):
        return

    sort = ask("sort 策略 (price/throughput/latency)", "price")
    if sort not in ("price", "throughput", "latency"):
        print(f" ⚠ 无效策略 '{sort}'，回退默认 price")
        sort = "price"
    run(["hermes", "config", "set", "provider_routing.sort", sort])

    if ask_yn("是否设置 provider 白名单？(y/n)", "n"):
        only = ask("白名单 provider（逗号分隔，如 Anthropic,Google）", "")
        if only:
            run(["hermes", "config", "set", "provider_routing.only", only])

    if ask_yn("是否设置 provider 黑名单？(y/n)", "n"):
        ignore = ask("黑名单 provider（逗号分隔，如 Together,DeepInfra）", "")
        if ignore:
            run(["hermes", "config", "set", "provider_routing.ignore", ignore])

    if ask_yn("禁止数据收集？(y/n)", "y"):
        run(["hermes", "config", "set", "provider_routing.data_collection", "deny"])

    if ask_yn("要求 provider 支持所有参数？(y/n)", "n"):
        run(["hermes", "config", "set", "provider_routing.require_parameters", "true"])

    print("  ✓ provider_routing 已配置")
    print("  提示：模型名后加 :nitro 可快速启用 throughput 排序")


def feat14_fallback_provider():
    """Fallback Provider — 主模型挂了自动切到备用 provider"""
    print("\n┏━ 14. Fallback Provider (跨 provider 故障切换)")
    print("┃ 三层容灾：密钥池(同provider轮转) → fallback_model(跨provider切换)")
    print("┃ 主模型 429/402/401/超时 → 自动切到备用，不丢对话")
    print("┗" + "━" * 50)

    print("\n  支持的 provider：")
    print("  openrouter / anthropic / zai / kimi-coding / minimax / gemini / xai / deepseek / custom ...")

    if not ask_yn("是否配置 fallback model？(y/n)", "n"):
        return

    fb_provider = ask("fallback provider", "openrouter")
    fb_model = ask("fallback model (如 anthropic/claude-sonnet-4)", "anthropic/claude-sonnet-4")
    if not fb_model:
        print("  ⚠ model 不能为空，跳过")
        return
    run(["hermes", "config", "set", "fallback_model.provider", fb_provider])
    run(["hermes", "config", "set", "fallback_model.model", fb_model])
    print(f"  ✓ fallback_model: {fb_provider}/{fb_model}")

    if fb_provider == "custom":
        fb_base_url = ask("fallback base_url (custom 必填)", "")
        if not fb_base_url:
            print(" ⚠ custom 必须填 base_url，跳过 fallback 配置")
            return
        run(["hermes", "config", "set", "fallback_model.base_url", fb_base_url])
        fb_api_key = ask("fallback API key (写入.env)", "")
        if fb_api_key:
            write_env("FALLBACK_API_KEY", fb_api_key)
            run(["hermes", "config", "set", "fallback_model.api_key_env", "FALLBACK_API_KEY"])

    print("\n  fallback 激活场景：")
    print("  429 限流 → 同 key 重试一次 → 失败则切 fallback")
    print("  402 账单 → 立即切 fallback（24h 冷却）")
    print("  401 认证 → 尝试刷新 → 失败则切 fallback")
    print("  超时/断连 → 切 fallback")


def feat15_shell_hooks():
    """Shell Hooks — 绑定脚本到生命周期事件"""
    print("\n┏━ 15. Shell Hooks (生命周期钩子)")
    print("┃ 将任意 shell 脚本绑定为 Hermes 生命周期钩子")
    print("┃ 无需写 Python plugin，一个脚本文件即可")
    print("┗" + "━" * 50)

    print("\n  支持的钩子事件：")
    print("  on_session_start — 新会话开始时")
    print("  on_session_end — 会话结束时")
    print("  pre_tool — 每次工具调用前（可阻断）")
    print("  post_tool — 每次工具调用后")
    print("  on_agent_start — agent 开始处理消息")
    print("  on_agent_end — agent 处理完成")

    print("\n  典型用例：")
    print("  pre_tool: 自动格式化代码、安全检查")
    print("  on_session_start: 加载环境变量、发送通知")
    print("  post_tool: 记录操作日志、统计 token")

    if not ask_yn("是否配置 shell hook？(y/n)", "n"):
        return

    VALID_HOOKS = {"on_session_start", "on_session_end", "pre_tool", "post_tool",
                    "on_agent_start", "on_agent_end"}
    hook_event = ask("钩子事件 (如 pre_tool/on_session_start)", "pre_tool")
    if hook_event not in VALID_HOOKS:
        print(f" ⚠ 无效事件 '{hook_event}'，有效值：{', '.join(sorted(VALID_HOOKS))}")
        if not ask_yn("仍然继续？(y/n)", "n"):
            return
    hook_script = ask("脚本路径 (绝对路径)", "")
    if not hook_script:
        print(" ⚠ 脚本路径不能为空，跳过")
        return
    if not os.path.isfile(hook_script):
        print(f" ⚠ 文件不存在: {hook_script}")
        if not ask_yn("仍然写入配置？(y/n)", "n"):
            return
    run(["hermes", "config", "set", f"hooks.{hook_event}", hook_script])
    print(f"  ✓ hooks.{hook_event} = {hook_script}")
    print("  提示：脚本必须可执行（chmod +x），失败不会崩溃 agent（非阻塞）")

    if ask_yn("继续配置其他 hook？(y/n)", "n"):
        while True:
            event = ask("钩子事件（回车退出）", "")
            if not event:
                break
            script = ask("脚本路径", "")
            if not script:
                break
            run(["hermes", "config", "set", f"hooks.{event}", script])
            print(f"  ✓ hooks.{event} = {script}")


def feat16_nous_tool_gateway():
    """Nous Tool Gateway — 付费用户免额外 API key 用搜索/图片/TTS/浏览器"""
    print("\n┏━ 16. Nous Tool Gateway (付费订阅专属)")
    print("┃ 付费 Nous Portal 订阅用户可免额外 API key 使用：")
    print("┃ Web 搜索+提取 / 图片生成 / TTS / 浏览器自动化")
    print("┃ 四件套全走 Nous 订阅账单，不需要单独注册 Firecrawl/FAL/OpenAI TTS")
    print("┗" + "━" * 50)

    # 检查订阅状态
    print("\n  先检查订阅状态...")
    r = subprocess.run(["hermes", "status"], capture_output=True, text=True, timeout=15)
    status = r.stdout + r.stderr
    if "Tool Gateway" in status and ("active" in status.lower().split() or "enabled" in status.lower().split()):
        print("  ✓ 检测到 Tool Gateway 已激活")
    else:
        print("  ⚠ 未检测到 Tool Gateway 激活状态")
        print("  需付费 Nous Portal 订阅: https://portal.nousresearch.com/manage-subscription")
        if not ask_yn("继续配置？(y/n)", "n"):
            return

    print("\n  可启用的工具：")
    tools = [
        ("web", "Web 搜索+提取（替代 TAVILY_API_KEY / FIRECRAWL_API_KEY）"),
        ("image", "图片生成（替代 FAL_KEY，8 模型含 FLUX/GPT-Image）"),
        ("tts", "文本转语音（替代 VOICE_TOOLS_OPENAI_KEY / ELEVENLABS_API_KEY）"),
        ("browser", "浏览器自动化（替代 BROWSER_USE_API_KEY / BROWSERBASE_API_KEY）"),
    ]
    for key, desc in tools:
        print(f"  {key}: {desc}")

    enable = ask("要启用哪些（逗号分隔，如 web,image,tts,browser，或 all）", "web")
    if enable.lower() == "all":
        enable = "web,image,tts,browser"

    for tool in enable.split(","):
        tool = tool.strip()
        if tool in [t[0] for t in tools]:
            run(["hermes", "config", "set", f"tool_gateway.{tool}.enabled", "true"])
            print(f"  ✓ tool_gateway.{tool} 已启用")
        else:
            print(f"  ⚠ 未知工具 {tool}，跳过")

    print("\n  验证：hermes status → 查看 Nous Tool Gateway 部分")


# ━━━ 主菜单 ━━━

FEAT_MAP = {
    "1": ("副驾模型 (auxiliary)", feat1_auxiliary),
    "2": ("搜索后端", feat2_search),
    "3": ("记忆系统", feat3_memory),
    "4": ("密钥池策略 (credential_pool)", feat4_credential_pool),
    "5": ("上下文窗口 & 最大输出", feat5_context_window),
    "6": ("上下文压缩 (双系统+引擎)", feat6_compression),
    "7": ("Token 监控工具", feat7_token_monitor),
    "8": ("Profile 分身", feat8_profile),
    "9": ("Skill 自主进化", feat9_skill_evolution),
    "10": ("子 Agent 并发 + 深度", feat10_delegation),
    "11": ("Cron 定时任务", feat11_cron),
    "12": ("生态工具", feat12_ecosystem),
    "13": ("Provider Routing (OpenRouter)", feat13_provider_routing),
    "14": ("Fallback Provider (跨provider容灾)", feat14_fallback_provider),
    "15": ("Shell Hooks (生命周期钩子)", feat15_shell_hooks),
    "16": ("Nous Tool Gateway (付费专属)", feat16_nous_tool_gateway),
}

VALID_KEYS = set(FEAT_MAP.keys())

print("=" * 56)
print(" Hermes 全量配置（上河一号定制版）")
print(" 合并 token 优化 + 功能配置 + 成本控制，16 大项可选")
print("=" * 56)

print("\n 第一层：核心配置")
print(" 1.  副驾模型 (auxiliary) — 成本降 60%-70%，两种模式")
print(" 2.  搜索后端 — 让它能联网查东西")
print(" 3.  记忆系统 — 内置记忆参数 + 可选外部 Provider")

print("\n 第二层：Token 优化")
print(" 4.  密钥池策略 — 同 provider 多 key 轮转 + OAuth")
print(" 5.  上下文窗口 & 最大输出 — 压缩算法精准计算的前提")
print(" 6.  上下文压缩 (双系统+引擎) — Gateway 85% + Agent 50%，引擎可替换")
print(" 7.  Token 监控工具 — 看钱花在哪、压掉终端冗余")

print("\n 第三层：成本控制 🆕")
print(" 13. Provider Routing — OpenRouter 路由到最便宜的 provider")
print(" 14. Fallback Provider — 主模型挂了自动切备用 provider")
print(" 15. Shell Hooks — 绑定脚本到生命周期事件")
print(" 16. Nous Tool Gateway — 付费订阅免额外 API key 用搜索/图片/TTS/浏览器")

print("\n 第四层：进阶功能")
print(" 8.  Profile 分身 — 独立记忆/人格/配置")
print(" 9.  Skill 自主进化 — 对话中自动沉淀新技能")
print(" 10. 子 Agent 并发 + 深度 — 派多路 agent，orchestrator 可嵌套")
print(" 11. Cron 定时任务 — 定时自己跑任务")
print(" 12. 生态工具 — 批量装 skill、文档处理工具")

print(f"\n  0. 全部配置")
print(f"  a. 全部跳过（退出）")

selection = ask("\n选哪些（多选用逗号分隔，如 1,4,6）", "0")

if selection == "a":
    print("  退出。")
    raise SystemExit(0)

if selection == "0":
    chosen = sorted(VALID_KEYS, key=int)
else:
    raw_keys = [k.strip() for k in selection.split(",")]
    chosen = []
    invalid = []
    for k in raw_keys:
        if k in VALID_KEYS:
            chosen.append(k)
        elif k:
            invalid.append(k)
    if invalid:
        print(f" ⚠ 忽略无效选项: {', '.join(invalid)}")
    chosen = sorted(chosen, key=int)

if not chosen:
    print("  无有效选择，退出。")
    raise SystemExit(0)

print(f"\n 将配置: {', '.join(chosen)}")

for k in chosen:
    name, fn = FEAT_MAP[k]
    fn()

# ━━━ 完成 ━━━
print("\n" + "=" * 56)
print(" 配置完成。验证：")
print(" hermes config — 查看当前配置")
print(" hermes profile list — 查看分身")
print(" hermes cron list — 查看定时任务")
print(" hermes skills list — 查看已装 skill")
print(" ⚠ 修改配置后需重启网关才能生效：/restart")
print("=" * 56)
