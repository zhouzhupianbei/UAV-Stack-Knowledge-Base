#!/usr/bin/env python3
"""
UAV-Stack-Knowledge-Base 资源更新脚本

通过 GitHub REST API、jisu-wechat-article skill、CSDN 搜索采集无人机领域
近期有价值的开源项目和文章，写入 07-OpenSource-Awesome/github-projects.md
和 wechat-articles.md。
"""

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
RESOURCES_DIR = REPO_DIR / "07-OpenSource-Awesome"
CST = timezone(timedelta(hours=8))

# GitHub 搜索关键词
GITHUB_TOPICS = [
    "UAV drone PX4",
    "ArduPilot MAVLink",
    "drone SLAM AI",
    "DJI SDK payload",
    "eVTOL aircraft",
    "drone inspection powerline",
    "autonomous drone",
    "无人机巡检",
    "PX4 autopilot",
]

# 微信搜索关键词（通过 jisu-wechat-article skill）
WECHAT_KEYWORDS = [
    "无人机",
    "低空经济",
    "大疆行业",
    "PX4 飞控",
    "无人机巡检",
    "eVTOL",
    "无人机算法",
]

# CSDN 搜索关键词
CSDN_KEYWORDS = [
    "PX4 飞控",
    "MAVLink 协议",
    "无人机 SLAM",
    "DJI SDK 开发",
    "无人机巡检 算法",
    "无人机 YOLO",
]

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


def now_str() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def log(msg: str):
    print(f"[{now_str()}] {msg}")


def sanitize(text: str, max_len: int = 200) -> str:
    """清理 GitHub description 字段

    1. 移除控制字符、零宽字符
    2. 去除全角空格填充（疑似 base64 注入的常见手法）
    3. 实际内容过短（< 20 字符有效内容）视为垃圾
    4. 单字符占比异常（>40% 是同一种字符如空格/全角空格）视为垃圾
    """
    if not text:
        return ""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]', '', text)
    text = text.replace('\u3000', ' ').replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ""
    # 全角空格（已被替换为普通空格）后看是否有效内容过短
    visible = re.sub(r'\s', '', text)
    if len(visible) < 20:
        return ""
    # 单字符占比异常（疑似填充）
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
    # 活跃度加分（30 天内有 push）
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


def fetch_github_projects() -> list[dict]:
    """获取 GitHub 无人机相关项目（带相关性打分 + spam 过滤）"""
    log("🔍 搜索 GitHub 项目...")
    seen_ids: set[int] = set()
    results: list[dict] = []

    for topic in GITHUB_TOPICS:
        repos = search_github(topic, limit=10, min_stars=80)
        log(f"  · {topic}: {len(repos)} 候选")
        for r in repos:
            if r["id"] in seen_ids:
                continue
            seen_ids.add(r["id"])
            # 严格过滤：先打 spam 标签，再做描述清理，最后打分
            if is_spam(r):
                continue
            clean_desc = sanitize(r.get("description"))
            if not clean_desc:
                continue
            score = relevance_score(r)
            if score < 3:  # 相关性太低，跳过
                continue
            results.append({
                "full_name": r["full_name"],
                "stargazers_count": r["stargazers_count"],
                "description": clean_desc,
                "html_url": r["html_url"],
                "topics": r.get("topics", [])[:5],
                "score": score,
            })

    # 按 score 优先、stars 次之排序
    results.sort(key=lambda x: (x["score"], x["stargazers_count"]), reverse=True)
    log(f"✅ 筛选出 {len(results)} 个相关项目")
    return results


def fetch_wechat_articles() -> list[dict]:
    """通过 jisu-wechat-article skill 获取微信公众号文章"""
    log("📱 搜索微信公众号文章...")
    if not WECHAT_SCRIPT.exists():
        log(f"  ⚠ 微信采集脚本不存在：{WECHAT_SCRIPT}")
        return []
    if not Path(PYTHON_BIN).exists():
        log(f"  ⚠ Python 解释器不存在：{PYTHON_BIN}")
        return []

    articles: list[dict] = []
    seen_fps: set[str] = set()

    for kw in WECHAT_KEYWORDS:
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
                # 指纹去重：标题前 12 字符
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

    log(f"✅ 共获取 {len(articles)} 篇不重复微信文章")
    return articles


def fetch_csdn_articles() -> list[dict]:
    """通过 CSDN 公开搜索接口获取技术文章"""
    log("💻 搜索 CSDN 文章...")
    articles: list[dict] = []
    seen_fps: set[str] = set()

    for kw in CSDN_KEYWORDS:
        try:
            # CSDN 公开搜索接口（无需登录）
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
            for it in results[:5]:  # 每个关键词 top 5
                title = (it.get("title") or "").strip()
                # CSDN 返回的 title 含 HTML 高亮标签，要清理
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

    log(f"✅ 共获取 {len(articles)} 篇不重复 CSDN 文章")
    return articles


def update_projects_doc(repos: list[dict]):
    """追加新章节到 07-OpenSource-Awesome/github-projects.md"""
    today = today_str()
    res_file = RESOURCES_DIR / "github-projects.md"

    if res_file.exists():
        with open(res_file, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = "# GitHub 开源项目推荐\n\n精选无人机相关优质开源项目。\n\n---\n\n"

    # 抽取已有 full_name，去重
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
        return False

    new_section += f"\n> 本期共收录 {added} 个项目\n\n---\n\n"
    with open(res_file, "w", encoding="utf-8") as f:
        f.write(existing + new_section)

    log(f"✅ GitHub 项目文档更新：{res_file}（新增 {added} 个）")
    return True


def update_wechat_doc(articles: list[dict]):
    """追加新章节到 07-OpenSource-Awesome/wechat-articles.md"""
    today = today_str()
    res_file = RESOURCES_DIR / "wechat-articles.md"

    if res_file.exists():
        with open(res_file, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = "# 微信公众号文章\n\n精选无人机领域优质公众号文章。\n\n---\n\n"

    # 指纹去重
    existing_fps = set()
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
        new_section += (
            f"### {art['title']}\n"
            f"- **来源**: {art['source']}\n"
            f"- **时间**: {art['datetime']}\n"
            f"- **链接**: [{art['url']}]({art['url']}) if {art['url']} else 无\n"
        )
        if art.get("summary"):
            new_section += f"- **摘要**: {art['summary']}\n"
        new_section += "\n"
        added += 1

    if added == 0:
        log(f"  · 本期无新增微信文章")
        return False

    new_section += f"\n> 本期共收录 {added} 篇文章\n\n---\n\n"
    with open(res_file, "w", encoding="utf-8") as f:
        f.write(existing + new_section)

    log(f"✅ 微信文章文档更新：{res_file}（新增 {added} 篇）")
    return True


def update_csdn_doc(articles: list[dict]):
    """追加新章节到 07-OpenSource-Awesome/csdn-articles.md"""
    today = today_str()
    res_file = RESOURCES_DIR / "csdn-articles.md"

    if res_file.exists():
        with open(res_file, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = "# CSDN 技术文章\n\n精选 CSDN 平台无人机领域技术文章。\n\n---\n\n"

    existing_fps = set()
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
        new_section += (
            f"### {art['title']}\n"
            f"- **作者**: {art.get('author', '匿名')}\n"
            f"- **时间**: {art['datetime']}\n"
            f"- **链接**: [{art['url']}]({art['url']})\n"
        )
        if art.get("summary"):
            new_section += f"- **摘要**: {art['summary']}\n"
        new_section += "\n"
        added += 1

    if added == 0:
        log(f"  · 本期无新增 CSDN 文章")
        return False

    new_section += f"\n> 本期共收录 {added} 篇文章\n\n---\n\n"
    with open(res_file, "w", encoding="utf-8") as f:
        f.write(existing + new_section)

    log(f"✅ CSDN 文章文档更新：{res_file}（新增 {added} 篇）")
    return True


def commit_and_push(changes: list[str]):
    """提交并推送"""
    if not changes:
        log("ℹ️ 无新增内容，跳过提交")
        return False

    log("🔄 准备提交...")
    try:
        # 只添加本次有变化的资源文档（避免误带其他修改）
        subprocess.run(
            ["git", "add"] + changes,
            cwd=REPO_DIR, check=True, timeout=30,
        )
        subprocess.run(
            ["git", "commit", "-m", "补充近期无人机领域开源项目与技术文章"],
            cwd=REPO_DIR, check=True, timeout=30,
        )
        subprocess.run(
            ["git", "push"],
            cwd=REPO_DIR, check=True, timeout=60,
        )
        log("✅ 推送成功")
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ Git 操作失败：{e}")
        return False


def main():
    log("=" * 50)
    log("UAV-Stack-Knowledge-Base 资源更新")
    log("=" * 50)

    repos = fetch_github_projects()
    wechat = fetch_wechat_articles()
    csdn = fetch_csdn_articles()

    changes: list[str] = []

    if repos:
        if update_projects_doc(repos):
            changes.append("07-OpenSource-Awesome/github-projects.md")

    if wechat:
        if update_wechat_doc(wechat):
            changes.append("07-OpenSource-Awesome/wechat-articles.md")

    if csdn:
        if update_csdn_doc(csdn):
            changes.append("07-OpenSource-Awesome/csdn-articles.md")

    log("=" * 50)
    commit_and_push(changes)
    log("=" * 50)


if __name__ == "__main__":
    main()