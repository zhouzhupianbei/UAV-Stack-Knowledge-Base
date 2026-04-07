#!/usr/bin/env python3
"""
UAV-Stack-Knowledge-Base 自动更新脚本
根据领域配置，定期获取无人机相关最新动态并更新知识库
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 配置
REPO_DIR = Path("/Users/lvguofei/workspaces/openclaw/UAV-Stack-Knowledge-Base")
MEMORY_DIR = REPO_DIR / "memory"
RESOURCES_DIR = REPO_DIR / "07-OpenSource-Awesome"
LOG_FILE = REPO_DIR / "update_log.md"

CST = timezone(timedelta(hours=8))

# 根据领域配置定义的搜索关键词
GITHUB_TOPICS = [
    "UAV",
    "drone",
    "PX4",
    "ArduPilot",
    "MAVLink",
    "DJI SDK",
    "drone AI",
    "SLAM drone",
]

WECHAT_KEYWORDS = [
    "无人机",
    "低空经济",
    "大疆行业",
    "PX4 飞控",
    "无人机巡检",
    "eVTOL",
]

def log(message: str):
    """记录日志"""
    timestamp = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def run_command(cmd: str, shell=True):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=REPO_DIR
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "命令执行超时"
    except Exception as e:
        return False, str(e)

def fetch_github_projects():
    """获取 GitHub 无人机相关项目"""
    log("🔍 获取 GitHub 无人机项目...")
    
    results = []
    
    for topic in GITHUB_TOPICS:
        cmd = f"node /Users/lvguofei/.openclaw/workspace/skills/github-search-1.0.0/scripts/github-search.mjs '{topic}' --min-stars 100 --updated-within 60 --limit 3 --output json 2>&1"
        success, output = run_command(cmd)
        
        if success:
            try:
                start_idx = output.find("{")
                end_idx = output.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = output[start_idx:end_idx]
                    data = json.loads(json_str)
                    if "repositories" in data:
                        results.extend(data["repositories"][:2])
                        log(f"  ✓ {topic}: {len(data['repositories'])} 个项目")
            except json.JSONDecodeError as e:
                log(f"  ⚠ 解析 {topic} 结果失败：{e}")
    
    log(f"✅ 找到 {len(results)} 个 GitHub 项目")
    return results

def fetch_wechat_articles():
    """获取微信公众号文章"""
    log("📱 获取微信公众号文章...")
    
    results = []
    
    for keyword in WECHAT_KEYWORDS:
        cmd = f"node /Users/lvguofei/.openclaw/workspace/skills/wechat-article-search-0.1.0/scripts/search_wechat.js '{keyword}' -n 3 2>&1"
        success, output = run_command(cmd)
        
        if success:
            try:
                start_idx = output.find("{")
                if start_idx >= 0:
                    data = json.loads(output[start_idx:])
                    if "articles" in data:
                        articles = data["articles"]
                        results.extend(articles[:2])
                        log(f"  ✓ {keyword}: {len(articles)} 篇文章")
            except json.JSONDecodeError as e:
                log(f"  ⚠ 解析 {keyword} 文章结果失败：{e}")
    
    log(f"✅ 找到 {len(results)} 篇微信文章")
    return results

def update_resources(github_projects):
    """更新 07-OpenSource-Awesome 目录"""
    log("📝 更新开源项目资源...")
    
    today = datetime.now(CST).strftime("%Y-%m-%d")
    resources_file = RESOURCES_DIR / "github-projects.md"
    
    if resources_file.exists():
        with open(resources_file, "r", encoding="utf-8") as f:
            existing_content = f.read()
    else:
        existing_content = "# GitHub 开源项目推荐\n\n精选无人机相关优质开源项目。\n\n---\n\n"
    
    new_section = f"\n## {today} 更新\n\n"
    for repo in github_projects[:15]:
        topics = repo.get('topics', [])
        new_section += f"""### {repo.get('full_name', 'Unknown')}
- **Stars**: {repo.get('stargazers_count', 0):,}
- **描述**: {repo.get('description', '无描述')}
- **链接**: [{repo.get('html_url', '')}]({repo.get('html_url', '')})
- **标签**: {', '.join(topics[:5]) if topics else '无'}

"""
    
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    with open(resources_file, "w", encoding="utf-8") as f:
        f.write(existing_content + new_section)
    
    log(f"✅ Resources 更新完成：{resources_file}")
    return resources_file

def update_memory(github_projects, wechat_articles):
    """更新 memory 目录"""
    log("📝 更新 memory 目录...")
    
    today = datetime.now(CST).strftime("%Y-%m-%d")
    memory_file = MEMORY_DIR / f"{today}_auto_update.md"
    
    content = f"""# 📅 自动更新 - {today}

**更新时间**: {datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")}

---

## 🔥 GitHub 热门项目

"""
    
    for repo in github_projects[:15]:
        content += f"""### {repo.get('full_name', 'Unknown')}
- **Stars**: {repo.get('stargazers_count', 0):,}
- **描述**: {repo.get('description', '无描述')}
- **链接**: [{repo.get('html_url', '')}]({repo.get('html_url', '')})
- **标签**: {', '.join(repo.get('topics', [])[:5]) if repo.get('topics') else '无'}

"""
    
    content += """\n---\n\n## 📱 微信公众号文章\n\n"""
    
    for article in wechat_articles[:15]:
        content += f"""### {article.get('title', '无标题')}
- **来源**: {article.get('source', '未知')}
- **时间**: {article.get('datetime', '未知')}
- **链接**: {article.get('url', '')}

"""
    
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(memory_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    log(f"✅ Memory 更新完成：{memory_file}")
    return memory_file

def commit_and_push():
    """提交并推送变更"""
    log("🔄 提交并推送变更...")
    
    # 检查是否有变更
    success, output = run_command("git status --porcelain")
    if not output.strip():
        log("ℹ️ 没有变更需要提交")
        return True
    
    # 添加变更
    success, output = run_command("git add -A")
    if not success:
        log(f"❌ git add 失败：{output}")
        return False
    
    # 提交
    today = datetime.now(CST).strftime("%Y-%m-%d")
    commit_msg = f"🤖 自动更新 - {today}"
    success, output = run_command(f'git commit -m "{commit_msg}"')
    if not success:
        log(f"❌ git commit 失败：{output}")
        return False
    
    # 推送
    success, output = run_command("git push")
    if not success:
        log(f"❌ git push 失败：{output}")
        return False
    
    log("✅ 推送成功")
    return True

def main():
    """主函数"""
    log("=" * 50)
    log("🚀 UAV-Stack-Knowledge-Base 自动更新开始")
    log("=" * 50)
    
    try:
        # 1. 获取 GitHub 项目
        github_projects = fetch_github_projects()
        
        # 2. 获取微信公众号文章
        wechat_articles = fetch_wechat_articles()
        
        # 3. 更新 resources 目录
        update_resources(github_projects)
        
        # 4. 更新 memory 目录
        update_memory(github_projects, wechat_articles)
        
        # 5. 提交并推送
        commit_and_push()
        
        log("=" * 50)
        log("✅ 自动更新完成")
        log("=" * 50)
        
    except Exception as e:
        log(f"❌ 更新失败：{str(e)}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
