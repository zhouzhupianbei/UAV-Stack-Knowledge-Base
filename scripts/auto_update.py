#!/usr/bin/env python3
"""
UAV-Stack-Knowledge-Base 自动更新脚本
使用 GitHub REST API 采集数据，不再依赖外部 Node 工具
"""

import os
import re
import sys
import json
import ssl
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 配置
REPO_DIR = Path("/Users/lvguofei/workspaces/openclaw/UAV-Stack-Knowledge-Base")
MEMORY_DIR = REPO_DIR / "memory"
RESOURCES_DIR = REPO_DIR / "07-OpenSource-Awesome"
LOG_FILE = REPO_DIR / "update_log.md"

CST = timezone(timedelta(hours=8))

# GitHub 搜索关键词
GITHUB_TOPICS = [
    "UAV drone PX4",
    "ArduPilot MAVLink",
    "drone SLAM AI",
    "DJI SDK payload",
    "eVTOL aircraft",
    "无人机巡检",
]

# 微信搜索关键词（暂时无法采集，留空占位）
WECHAT_KEYWORDS = [
    "无人机",
    "低空经济",
    "大疆行业",
    "PX4 飞控",
]

# GitHub API 设置
API_CTX = ssl.create_default_context()
API_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def log(msg: str):
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def sanitize(text: str) -> str:
    """移除 description 中的控制字符和非可视字符"""
    if not text:
        return ""
    # 移除控制字符、零宽字符、替换 surrogates
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff]', '', text)
    # 移除多余空白但保留换行
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def search_github(query: str, limit: int = 5, min_stars: int = 100) -> list[dict]:
    """通过 GitHub REST API 搜索仓库"""
    encoded_q = urllib.parse.quote(query)
    url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={limit}"
    req = urllib.request.Request(url, headers=API_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20, context=API_CTX) as resp:
            data = json.loads(resp.read())
            items = data.get("items", [])
            if min_stars:
                items = [i for i in items if i.get("stargazers_count", 0) >= min_stars]
            return items
    except Exception as e:
        log(f"  ⚠ API 请求失败 [{query}]：{e}")
        return []


def fetch_github_projects() -> list[dict]:
    """获取 GitHub 无人机相关项目"""
    log("🔍 获取 GitHub 无人机项目...")
    seen_ids: set[int] = set()
    results: list[dict] = []

    for topic in GITHUB_TOPICS:
        repos = search_github(topic, limit=8, min_stars=100)
        log(f"  ✓ {topic}: {len(repos)} 个项目")
        for r in repos:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                results.append({
                    "full_name": r["full_name"],
                    "stargazers_count": r["stargazers_count"],
                    "description": sanitize(r.get("description")) or "无描述",
                    "html_url": r["html_url"],
                    "topics": r.get("topics", [])[:5],
                })

    # 按 star 降序
    results.sort(key=lambda x: x["stargazers_count"], reverse=True)
    log(f"✅ 共获取 {len(results)} 个不重复项目")
    return results


def fetch_wechat_articles() -> list[dict]:
    """获取微信公众号文章（占位，需外部工具）"""
    log("📱 获取微信公众号文章...")
    # 微信文章无公开 API，暂时无法采集
    log("  ⚠ 微信文章暂无采集渠道，跳过")
    return []


def update_resources(repos: list[dict]):
    """更新 07-OpenSource-Awesome/github-projects.md"""
    log("📝 更新开源项目资源...")

    today = datetime.now(CST).strftime("%Y-%m-%d")
    res_file = RESOURCES_DIR / "github-projects.md"

    if res_file.exists():
        with open(res_file, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = "# GitHub 开源项目推荐\n\n精选无人机相关优质开源项目。\n\n---\n\n"

    new_section = f"\n## {today} 更新\n\n"
    if repos:
        for repo in repos[:15]:
            topics = repo.get("topics") or []
            new_section += f"""### {repo['full_name']}
- **Stars**: {repo['stargazers_count']:,}
- **描述**: {repo['description']}
- **链接**: [{repo['html_url']}]({repo['html_url']})
- **标签**: {', '.join(topics) if topics else '无'}

"""
    else:
        new_section += "*本期无新增项目*\n"

    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    with open(res_file, "w", encoding="utf-8") as f:
        f.write(existing + new_section)

    log(f"✅ Resources 更新完成：{res_file}")


def update_memory(repos: list[dict], articles: list[dict]):
    """更新 memory 目录"""
    log("📝 更新 memory 目录...")

    today = datetime.now(CST).strftime("%Y-%m-%d")
    mem_file = MEMORY_DIR / f"{today}_maintenance.md"

    content = f"""# 📅 更新记录 - {today}

**更新时间**: {datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")}

---

## 🔥 GitHub 热门项目

"""
    if repos:
        for repo in repos[:15]:
            topics = repo.get("topics") or []
            content += f"""### {repo['full_name']}
- **Stars**: {repo['stargazers_count']:,}
- **描述**: {repo['description']}
- **链接**: [{repo['html_url']}]({repo['html_url']})
- **标签**: {', '.join(topics) if topics else '无'}

"""
    else:
        content += "*本期无新增项目*\n"

    content += "\n---\n\n## 📱 微信公众号文章\n\n"
    if articles:
        for article in articles[:15]:
            content += f"""### {article.get('title', '无标题')}
- **来源**: {article.get('source', '未知')}
- **时间**: {article.get('datetime', '未知')}
- **链接**: {article.get('url', '')}

"""
    else:
        content += "*本期无新增文章*\n"

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(mem_file, "w", encoding="utf-8") as f:
        f.write(content)

    log(f"✅ Memory 更新完成：{mem_file}")


def commit_and_push():
    """提交并推送变更"""
    log("🔄 检查变更...")

    # 检查是否有内容变化
    import subprocess
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=30
        )
        changed = res.stdout.strip()
    except Exception as e:
        log(f"❌ git status 失败：{e}")
        return False

    if not changed:
        log("ℹ️ 没有变更，跳过提交")
        return True

    # 添加并提交
    commit_msg = f"补充 {datetime.now(CST).strftime('%Y-%m-%d')} 开源项目更新"
    try:
        subprocess.run(["git", "add", "-A"], capture_output=True, cwd=REPO_DIR, timeout=30)
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=30
        )
        subprocess.run(["git", "push"], capture_output=True, text=True, cwd=REPO_DIR, timeout=60)
        log("✅ 推送成功")
        return True
    except Exception as e:
        log(f"❌ Git 操作失败：{e}")
        return False


def main():
    log("=" * 50)
    log("🚀 UAV-Stack-Knowledge-Base 更新开始")
    log("=" * 50)

    repos = fetch_github_projects()
    articles = fetch_wechat_articles()

    if not repos and not articles:
        log("⚠️ 未获取到任何数据，跳过本次更新")
        sys.exit(0)

    update_resources(repos)
    update_memory(repos, articles)
    commit_and_push()

    log("=" * 50)
    log("✅ 更新完成")
    log("=" * 50)


if __name__ == "__main__":
    main()
