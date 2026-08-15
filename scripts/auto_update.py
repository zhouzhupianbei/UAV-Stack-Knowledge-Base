#!/usr/bin/env python3
"""
UAV-Stack-Knowledge-Base 资源更新脚本（栏目随机版）

工作流（2026-07-24 重构）：
1. 从 9 个栏目里随机抽 N 个（默认 3）
2. 每个栏目读 README.md 抽取 3-5 个主题关键词
3. 用栏目主题 + UAV 强相关词作为采集关键词，分别跑 GitHub / 微信 / CSDN 三源
4. 每个栏目的产出写到「{栏目}/{source}-articles.md」，追加「## YYYY-MM-DD 更新」章节
5. 一次性 git add 全部变更路径 + commit + push
"""

from __future__ import annotations  # 兼容 Python 3.9 的 PEP 604 union 语法

import os
import re
import sys
import json
import ssl
import time
import random
import urllib.request
import urllib.parse
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_DIR = Path("/Users/lvguofei/workspaces/openclaw/UAV-Stack-Knowledge-Base")
CST = timezone(timedelta(hours=8))

# 9 大栏目（00-08），每次随机抽其中的 N 个
SECTIONS = [
    "00-QuickStart",
    "01-Policy-Standard",
    "02-Hardware-Systems",
    "03-Protocols-Dev",
    "04-Streaming-AI",
    "05-GIS-DigitalTwin",
    "06-Industry-Solutions",
    "07-OpenSource-Awesome",
    "08-Project-Analysis",
]

# 默认每次随机抽几个栏目
DEFAULT_SECTION_COUNT = 3

# 引导分享段落：每次生成文档前自动塞到顶部（按栏目调性微调）
SHARE_INTRO_UAV = (
    "> 💡 **如果你也在做无人机 / 飞控 / 巡检 / 低空相关**，"
    "觉得这份清单有用，欢迎 **点个 ⭐ Star + 把这个仓库分享给身边的朋友** —— "
    "PX4 / ArduPilot / MAVLink / 仿真 / 巡检算法 这些领域资料散落各处，"
    "**一个人查文档远不如一群人共建一份知识库更高效**。\n\n---\n\n"
)

# 主题关键词（用于相关性打分）
UAV_STRONG = [
    "uav", "drone", "px4", "ardupilot", "mavlink", "dji", "slam",
    "autopilot", "multirotor", "quadrotor", "evtol", "vtol",
    "无人机", "飞控", "航线", "巡检",
]

# 垃圾数据特征关键词（命中直接丢弃）
SPAM_SIGNALS = [
    "books", "book list", "free books", "ebook",
    "recipe", "cricket", "game", "ecommerce",
    "personal collection", "图书", "书单",
]

# 微信脚本位置
WECHAT_SCRIPT = Path("/Users/lvguofei/.openclaw/workspace/skills/jisu-wechat-article/search.py")
PYTHON_BIN = "/Users/lvguofei/miniconda3/bin/python3"

API_CTX = ssl.create_default_context()
API_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

CSDN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://so.csdn.net/",
}

# 停用词：抽 README 关键词时过滤掉这些高频但无语义的词
STOPWORDS = {
    "本模块", "面向", "提供", "包含", "以及", "包括", "适用于", "通过",
    "目标", "读者", "文档", "文档", "模块", "内容", "导航",
    "分钟", "小时", "预计", "耗时",
}


# ============================================================
# 工具函数
# ============================================================

def now_str() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def log(msg: str):
    print(f"[{now_str()}] {msg}")


def sanitize(text: str, max_len: int = 200) -> str:
    """清理 GitHub description 字段"""
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]', '', text)
    text = text.replace('\u3000', ' ').replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ""
    visible = re.sub(r'\s', '', text)
    if len(visible) < 20:
        return ""
    if len(text) > 100:
        from collections import Counter
        most_common_char, most_common_count = Counter(text).most_common(1)[0]
        if most_common_count / len(text) > 0.4:
            return ""
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def is_spam(repo: dict) -> bool:
    """检测 description 或仓库名是否命中垃圾信号"""
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    text = f"{name} {desc}"
    return any(sig in text for sig in SPAM_SIGNALS)


def relevance_score(repo: dict) -> int:
    """UAV 相关性打分（0-10）"""
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    topics = " ".join(repo.get("topics") or []).lower()
    text = f"{name} {desc} {topics}"
    score = 0
    for kw in UAV_STRONG:
        if kw in text:
            score += 3
    pushed = repo.get("pushed_at", "")[:10]
    if pushed:
        try:
            d = datetime.strptime(pushed, "%Y-%m-%d")
            days_old = (datetime.now() - d).days
            if days_old <= 90:
                score += 2
        except ValueError:
            pass
    return score


# ============================================================
# 栏目关键词抽取
# ============================================================

def extract_keywords_from_readme(readme_path: Path, max_keywords: int = 5) -> list[str]:
    """从栏目 README.md 抽取主题关键词（3-5 个）

    抽取策略（按优先级）：
    1. 表格行：从每行的"链接文本"[...](...) 中提取中文短语（如 MAVLink 协议）
       跳过表头行（含 '文档'/'章节'/'内容'/'导航' 等表头关键词）和分隔行（|---|---|）
    2. 第一个 H1 标题（去掉 `XX-模块名：` 前缀）
    3. blockquote 副标题
    4. 表格 "核心内容" 列（仅在数据行）

    过滤停用词、去重、按长度排序取前 max_keywords 个。
    """
    if not readme_path.exists():
        return []

    text = readme_path.read_text(encoding="utf-8")
    candidates: list[str] = []

    # 表头关键词（出现这些词的行判定为表头，跳过）
    table_header_signals = ("文档", "章节", "内容导航", "模块", "路径", "链接")
    table_sep_pattern = re.compile(r"^\|[\s\-:|]+\|$")

    # 策略 1 + 4：表格行（跳过表头和分隔行）
    for row in re.finditer(r"^\|[^\n]+\|$", text, re.MULTILINE):
        row_text = row.group(0)
        # 跳过分隔行
        if table_sep_pattern.match(row_text):
            continue
        cells = [c.strip() for c in row_text.strip("|").split("|")]
        if not cells:
            continue
        # 跳过表头行（含典型表头词）
        if any(sig in cells[0] for sig in table_header_signals):
            continue
        # 遍历所有列
        for cell in cells:
            # 从 [name](path) 提取链接文本
            for m in re.finditer(r"\[([^\]]+)\]\([^)]+\)", cell):
                link_text = m.group(1).strip()
                # 去掉前导序号（如 "01-MAVLink 协议详解" → "MAVLink 协议详解"）
                link_text = re.sub(r"^\d{2}-", "", link_text)
                for phrase in re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9]{2,}", link_text):
                    if phrase not in STOPWORDS and len(phrase) >= 2:
                        candidates.append(phrase)
            # 也提取 cell 里的纯中文短语
            for phrase in re.findall(r"[\u4e00-\u9fff]{2,8}", cell):
                if phrase not in STOPWORDS:
                    candidates.append(phrase)

    # 策略 2：H1 标题
    h1_match = re.search(r"^#\s+([^\n]+)", text, re.MULTILINE)
    if h1_match:
        h1 = h1_match.group(1).strip()
        h1 = re.sub(r"^\d{2}-[A-Za-z-]+[：:]\s*", "", h1)
        for phrase in re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9]{2,}", h1):
            if phrase not in STOPWORDS:
                candidates.append(phrase)

    # 策略 3：blockquote 副标题
    bq_match = re.search(r"^>\s*([^\n]+)", text, re.MULTILINE)
    if bq_match:
        bq = bq_match.group(1).strip()
        bq = re.sub(r"^[^\u4e00-\u9fffA-Za-z]+", "", bq)
        bq = re.sub(r"[^\u4e00-\u9fffA-Za-z]+$", "", bq)
        for phrase in re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9]{2,}", bq):
            if phrase not in STOPWORDS:
                candidates.append(phrase)

    # 策略 5："目标读者" 段
    reader_match = re.search(r"##\s*🎯\s*目标读者\s*\n+(.+?)(?=\n##|\Z)", text, re.DOTALL)
    if reader_match:
        reader_text = reader_match.group(1)
        for phrase in re.findall(r"[\u4e00-\u9fff]{2,8}", reader_text):
            if phrase not in STOPWORDS:
                candidates.append(phrase)

    # 去重（保序）
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    # 取前 max_keywords 个
    return unique[:max_keywords]


# ============================================================
# 三源采集（带关键词参数）
# ============================================================

def search_github(query: str, limit: int = 8, min_stars: int = 100) -> list[dict]:
    """GitHub REST API 搜索"""
    encoded_q = urllib.parse.quote(query)
    url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={limit}"
    req = urllib.request.Request(url, headers=API_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20, context=API_CTX) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])
            return [i for i in items if i.get("stargazers_count", 0) >= min_stars]
    except Exception as e:
        log(f"  ⚠ GitHub API 失败 [{query}]：{e}")
        return []


def fetch_github(keywords: list[str]) -> list[dict]:
    """根据栏目关键词采集 GitHub 项目"""
    log(f"🔍 GitHub 搜索（{len(keywords)} 个关键词）...")
    seen_ids: set[int] = set()
    results: list[dict] = []

    # 每个关键词 + UAV 强相关词组合搜一次（提高相关性）
    for kw in keywords:
        # 原始关键词
        for query in [kw, f"{kw} drone", f"{kw} UAV"]:
            repos = search_github(query, limit=8, min_stars=50)
            for r in repos:
                if r["id"] in seen_ids:
                    continue
                seen_ids.add(r["id"])
                if is_spam(r):
                    continue
                clean_desc = sanitize(r.get("description"))
                if not clean_desc:
                    continue
                score = relevance_score(r)
                if score < 3:
                    continue
                results.append({
                    "full_name": r["full_name"],
                    "stargazers_count": r["stargazers_count"],
                    "description": clean_desc,
                    "html_url": r["html_url"],
                    "topics": r.get("topics", [])[:5],
                    "score": score,
                })

    results.sort(key=lambda x: (x["score"], x["stargazers_count"]), reverse=True)
    log(f"  ✅ 筛选出 {len(results)} 个相关项目")
    return results


def fetch_wechat(keywords: list[str]) -> list[dict]:
    """根据栏目关键词采集微信公众号文章"""
    log(f"📱 微信搜索（{len(keywords)} 个关键词）...")
    if not WECHAT_SCRIPT.exists():
        log(f"  ⚠ 微信采集脚本不存在：{WECHAT_SCRIPT}")
        return []
    if not Path(PYTHON_BIN).exists():
        log(f"  ⚠ Python 解释器不存在：{PYTHON_BIN}")
        return []

    articles: list[dict] = []
    seen_fps: set[str] = set()

    for kw in keywords:
        try:
            result = subprocess.run(
                [PYTHON_BIN, str(WECHAT_SCRIPT), kw, "-n", "5"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode not in (0, 1):
                log(f"  ⚠ [{kw}] exit={result.returncode}")
                continue
            data = json.loads(result.stdout)
            items = data.get("items", []) or []
            log(f"  · {kw}: {len(items)} 篇")
            for it in items:
                title = (it.get("title") or "").strip()
                if not title:
                    continue
                fp = re.sub(r"\s+", "", title)[:12]
                if fp in seen_fps:
                    continue
                seen_fps.add(fp)
                articles.append({
                    "title": title,
                    "source": it.get("source_account", "未知"),
                    "datetime": it.get("publish_time", "未知"),
                    "url": it.get("detail_url") or it.get("url_real") or it.get("url", ""),
                    "summary": (it.get("summary") or "").strip()[:200],
                })
        except Exception as e:
            log(f"  ⚠ [{kw}] 异常：{e}")
            continue
        time.sleep(2.5)  # 避免触发搜狗风控

    log(f"  ✅ 共获取 {len(articles)} 篇不重复微信文章")
    return articles


def fetch_csdn(keywords: list[str]) -> list[dict]:
    """根据栏目关键词采集 CSDN 文章"""
    log(f"💻 CSDN 搜索（{len(keywords)} 个关键词）...")
    articles: list[dict] = []
    seen_fps: set[str] = set()

    for kw in keywords:
        try:
            encoded_q = urllib.parse.quote(kw)
            url = (
                f"https://so.csdn.net/api/v3/search?"
                f"q={encoded_q}&p=1&s=0&tm=0&lv=-1&ft=0&l=&u="
                f"&ct=-1&pnt=-1&ry=-1&ss=-1&dct=-1&vt=-1&bnt=-1&ewt=-1"
                f"&fst=0&ra=28&fid=&platform=pc&cId=-1&ab_test_code_overlap=&ab_test_random_code=&ab_test_code=ctrlA_search"
            )
            req = urllib.request.Request(url, headers=CSDN_HEADERS)
            with urllib.request.urlopen(req, timeout=20, context=API_CTX) as resp:
                data = json.loads(resp.read())
            results = data.get("result_vos", []) or []
            log(f"  · {kw}: {len(results)} 条")
            for it in results[:5]:
                title = (it.get("title") or "").strip()
                title = re.sub(r"<[^>]+>", "", title).strip()
                if not title:
                    continue
                fp = re.sub(r"\s+", "", title)[:12]
                if fp in seen_fps:
                    continue
                seen_fps.add(fp)
                articles.append({
                    "title": title,
                    "source": "CSDN",
                    "author": it.get("user_name", ""),
                    "datetime": it.get("create_time_str", ""),
                    "url": it.get("url", ""),
                    "summary": (it.get("description") or "").strip()[:200],
                })
        except Exception as e:
            log(f"  ⚠ [{kw}] 异常：{e}")
            continue
        time.sleep(1.5)

    log(f"  ✅ 共获取 {len(articles)} 篇不重复 CSDN 文章")
    return articles


# ============================================================
# 栏目级文档写入
# ============================================================

DEFAULT_HEADER_GH = "# GitHub 开源项目推荐\n\n精选本栏目主题相关的优质开源项目。\n\n---\n\n"
DEFAULT_HEADER_WECHAT = "# 微信公众号文章\n\n精选本栏目主题相关的优质公众号文章。\n\n---\n\n"
DEFAULT_HEADER_CSDN = "# CSDN 技术文章\n\n精选本栏目主题相关的 CSDN 技术文章。\n\n---\n\n"


def _ensure_share_intro(existing: str, intro: str) -> str:
    """保证文档顶部有引导分享段（幂等）"""
    if intro.strip()[:20] not in existing:
        return intro + existing
    return existing


def update_projects_doc(section: str, repos: list[dict]) -> tuple[bool, str]:
    """追加章节到 {section}/github-projects.md"""
    today = today_str()
    section_dir = REPO_DIR / section
    res_file = section_dir / "github-projects.md"

    if not section_dir.exists():
        log(f"  ⚠ 栏目目录不存在：{section_dir}")
        return False, ""

    if res_file.exists():
        existing = res_file.read_text(encoding="utf-8")
    else:
        existing = DEFAULT_HEADER_GH

    existing = _ensure_share_intro(existing, SHARE_INTRO_UAV)

    # 去重：抽取已有 full_name
    existing_names = set(re.findall(r"^###\s+([\w.-]+/[\w.-]+)\s*$", existing, re.MULTILINE))

    new_section = f"\n## {today} 更新\n\n"
    added = 0
    for repo in repos[:12]:
        if repo["full_name"] in existing_names:
            continue
        topics = repo.get("topics") or []
        new_section += (
            f"### {repo['full_name']}\n"
            f"- **Stars**: {repo['stargazers_count']:,}\n"
            f"- **描述**: {repo['description']}\n"
            f"- **链接**: [{repo['html_url']}]({repo['html_url']})\n"
            f"- **标签**: {', '.join(topics) if topics else '无'}\n\n"
        )
        added += 1

    if added == 0:
        log(f"  · 本期无新增项目（已全部收录）")
        return False, ""

    new_section += f"\n> 本期共收录 {added} 个项目\n\n---\n\n"
    res_file.write_text(existing + new_section, encoding="utf-8")

    log(f"  ✅ GitHub 文档更新：{res_file.relative_to(REPO_DIR)}（新增 {added} 个）")
    return True, f"{section}/github-projects.md"


def update_wechat_doc(section: str, articles: list[dict]) -> tuple[bool, str]:
    """追加章节到 {section}/wechat-articles.md"""
    today = today_str()
    section_dir = REPO_DIR / section
    res_file = section_dir / "wechat-articles.md"

    if not section_dir.exists():
        return False, ""

    if res_file.exists():
        existing = res_file.read_text(encoding="utf-8")
    else:
        existing = DEFAULT_HEADER_WECHAT

    existing = _ensure_share_intro(existing, SHARE_INTRO_UAV)

    # 指纹去重
    existing_fps: set[str] = set()
    for m in re.finditer(r'(?m)^###\s+(.+?)$', existing):
        t = re.sub(r"\s+", "", m.group(1))
        if len(t) >= 8:
            existing_fps.add(t[:12])

    new_section = f"\n## {today} 更新\n\n"
    added = 0
    for art in articles[:15]:
        fp = re.sub(r"\s+", "", art["title"])[:12]
        if fp in existing_fps:
            continue
        existing_fps.add(fp)
        url = art.get("url", "")
        new_section += (
            f"### {art['title']}\n"
            f"- **来源**: {art['source']}\n"
            f"- **时间**: {art['datetime']}\n"
            f"- **链接**: [{url}]({url}) if {url} else 无\n"
        )
        if art.get("summary"):
            new_section += f"- **摘要**: {art['summary']}\n"
        new_section += "\n"
        added += 1

    if added == 0:
        log(f"  · 本期无新增微信文章")
        return False, ""

    new_section += f"\n> 本期共收录 {added} 篇文章\n\n---\n\n"
    res_file.write_text(existing + new_section, encoding="utf-8")

    log(f"  ✅ 微信文档更新：{res_file.relative_to(REPO_DIR)}（新增 {added} 篇）")
    return True, f"{section}/wechat-articles.md"


def update_csdn_doc(section: str, articles: list[dict]) -> tuple[bool, str]:
    """追加章节到 {section}/csdn-articles.md"""
    today = today_str()
    section_dir = REPO_DIR / section
    res_file = section_dir / "csdn-articles.md"

    if not section_dir.exists():
        return False, ""

    if res_file.exists():
        existing = res_file.read_text(encoding="utf-8")
    else:
        existing = DEFAULT_HEADER_CSDN

    existing = _ensure_share_intro(existing, SHARE_INTRO_UAV)

    # 指纹去重
    existing_fps: set[str] = set()
    for m in re.finditer(r'(?m)^###\s+(.+?)$', existing):
        t = re.sub(r"\s+", "", m.group(1))
        if len(t) >= 8:
            existing_fps.add(t[:12])

    new_section = f"\n## {today} 更新\n\n"
    added = 0
    for art in articles[:15]:
        fp = re.sub(r"\s+", "", art["title"])[:12]
        if fp in existing_fps:
            continue
        existing_fps.add(fp)
        url = art.get("url", "")
        new_section += (
            f"### {art['title']}\n"
            f"- **作者**: {art.get('author', '匿名')}\n"
            f"- **时间**: {art['datetime']}\n"
            f"- **链接**: [{url}]({url})\n"
        )
        if art.get("summary"):
            new_section += f"- **摘要**: {art['summary']}\n"
        new_section += "\n"
        added += 1

    if added == 0:
        log(f"  · 本期无新增 CSDN 文章")
        return False, ""

    new_section += f"\n> 本期共收录 {added} 篇文章\n\n---\n\n"
    res_file.write_text(existing + new_section, encoding="utf-8")

    log(f"  ✅ CSDN 文档更新：{res_file.relative_to(REPO_DIR)}（新增 {added} 篇）")
    return True, f"{section}/csdn-articles.md"


# ============================================================
# Git 提交
# ============================================================

def commit_and_push(changes: list[str], summary: dict) -> bool:
    """提交并推送（带变更摘要）"""
    if not changes:
        log("ℹ️ 无新增内容，跳过提交")
        return False

    log("🔄 准备提交...")
    # 构造带变更摘要的 commit message
    sections_str = "、".join(summary.get("sections", []))
    msg = (
        f"补充近期无人机领域开源项目与技术文章\n\n"
        f"本期随机更新栏目：{sections_str}\n"
        f"各栏目新增：{summary.get('counts', {})}"
    )

    try:
        subprocess.run(
            ["git", "add"] + changes,
            cwd=REPO_DIR, check=True, timeout=30,
        )
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=REPO_DIR, check=True, timeout=30,
        )
        # cron 环境默认无 proxy；github.com 直连超时(2026-08-16 实测),
        # 必须注入 7890 代理才能成功 push。优先尝试代理,失败再回退直连。
        push_env = os.environ.copy()
        push_env["HTTPS_PROXY"] = push_env.get("HTTPS_PROXY", "http://127.0.0.1:7890")
        push_env["HTTP_PROXY"] = push_env.get("HTTP_PROXY", "http://127.0.0.1:7890")
        push_env["https_proxy"] = push_env["HTTPS_PROXY"]
        push_env["http_proxy"] = push_env["HTTP_PROXY"]
        push_env["GIT_TERMINAL_PROMPT"] = "0"
        try:
            subprocess.run(
                ["git", "push"],
                cwd=REPO_DIR, check=True, timeout=60,
                env=push_env, capture_output=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            subprocess.run(
                ["git", "push"],
                cwd=REPO_DIR, check=True, timeout=60,
            )
        log("✅ 推送成功")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Git 操作失败：{e}")
        return False


# ============================================================
# 主流程
# ============================================================

def pick_sections(count: int = DEFAULT_SECTION_COUNT, seed: int | None = None) -> list[str]:
    """随机抽 N 个栏目"""
    if seed is not None:
        random.seed(seed)
    return random.sample(SECTIONS, min(count, len(SECTIONS)))


def process_section(section: str) -> tuple[list[str], dict]:
    """处理单个栏目：抽关键词 → 三源采集 → 写入对应文档

    Returns:
        (changed_paths, counts) - changed_paths 是有变更的文件路径列表（相对 REPO_DIR），
                                 counts 是 {source: 数量} 摘要
    """
    log("=" * 50)
    log(f"📂 栏目：{section}")
    log("=" * 50)

    readme_path = REPO_DIR / section / "README.md"
    keywords = extract_keywords_from_readme(readme_path, max_keywords=5)
    log(f"🔑 抽到关键词：{keywords}")

    if not keywords:
        log(f"  ⚠ README 抽不到关键词，跳过")
        return [], {}

    changed: list[str] = []
    counts: dict[str, int] = {}

    # 三源采集
    repos = fetch_github(keywords)
    wechat = fetch_wechat(keywords)
    csdn = fetch_csdn(keywords)

    # 写入
    if repos:
        ok, path = update_projects_doc(section, repos)
        if ok:
            changed.append(path)
            counts["github"] = min(len(repos), 12)

    if wechat:
        ok, path = update_wechat_doc(section, wechat)
        if ok:
            changed.append(path)
            counts["wechat"] = min(len(wechat), 15)

    if csdn:
        ok, path = update_csdn_doc(section, csdn)
        if ok:
            changed.append(path)
            counts["csdn"] = min(len(csdn), 15)

    return changed, counts


def main():
    log("=" * 50)
    log("UAV-Stack-Knowledge-Base 资源更新（栏目随机版）")
    log("=" * 50)

    # 1. 选栏目
    chosen = pick_sections(DEFAULT_SECTION_COUNT)
    log(f"🎲 本期随机抽到栏目：{chosen}")

    # 2. 每个栏目独立处理
    all_changed: list[str] = []
    summary: dict = {"sections": [], "counts": {}}
    for section in chosen:
        changed, counts = process_section(section)
        all_changed.extend(changed)
        if counts:
            summary["sections"].append(f"{section}({sum(counts.values())})")
            summary["counts"][section] = counts

    # 3. 一次性提交
    log("=" * 50)
    if all_changed:
        commit_and_push(all_changed, summary)
    else:
        log("ℹ️ 本期所有栏目都无新增内容")
    log("=" * 50)


if __name__ == "__main__":
    main()