# -*- coding: utf-8 -*-
"""
Netlify 部署脚本 —— 将本站点目录以「API 直连」方式部署到 Netlify。
（复制自 us-treasury-monitor/deploy_netlify.py，按本站点调整站点名与排除项）

凭据读取优先级：
    1. 环境变量 NETLIFY_AUTH_TOKEN
    2. 同目录下的 .netlify-token 文件（已在 .gitignore 中排除）

站点 ID 读取优先级：
    1. 环境变量 NETLIFY_SITE_ID
    2. 同目录下的 .netlify-site-id 文件（首次部署自动写入）

用法：
    <python> deploy_netlify.py [--site-name hf-quant-policy-monitor]
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

import httpx

API = "https://api.netlify.com/api/v1"
HERE = Path(__file__).resolve().parent

TOKEN_FILE = HERE / ".netlify-token"
SITE_ID_FILE = HERE / ".netlify-site-id"
DEFAULT_SITE_NAME = "hf-quant-policy-monitor"

# 需要排除、不部署到线上的文件/目录
EXCLUDE_DIRS = {".git", "__pycache__", ".workbuddy", "node_modules"}
EXCLUDE_NAMES = {
    ".gitignore", ".netlify-token", ".netlify-site-id", ".github-token",
    "README.md", "netlify.toml",
    "deploy_netlify.py", "push_github.py",
}
EXCLUDE_SUFFIX = {".py", ".pyc", ".md", ".log", ".sh"}


def get_token() -> str:
    tok = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
    if tok:
        return tok
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    print("错误：未找到 Netlify 凭据（环境变量 NETLIFY_AUTH_TOKEN 或 .netlify-token 文件）", file=sys.stderr)
    sys.exit(2)


def get_site_id() -> str:
    sid = os.environ.get("NETLIFY_SITE_ID", "").strip()
    if sid:
        return sid
    if SITE_ID_FILE.exists():
        return SITE_ID_FILE.read_text(encoding="utf-8").strip()
    return ""


def collect_files() -> dict:
    """返回 {部署路径: 绝对路径}，部署路径以 / 开头。"""
    out = {}
    for p in sorted(HERE.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(HERE)
        parts = rel.parts
        if any(seg in EXCLUDE_DIRS for seg in parts[:-1]):
            continue
        if rel.name in EXCLUDE_NAMES:
            continue
        if rel.suffix.lower() in EXCLUDE_SUFFIX:
            continue
        out["/" + "/".join(parts)] = p
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-name", default=DEFAULT_SITE_NAME)
    args = ap.parse_args()

    token = get_token()
    headers = {"Authorization": "Bearer " + token}
    # trust_env=False：绕开沙箱代理，直连 api.netlify.com
    client = httpx.Client(headers=headers, timeout=120, follow_redirects=True, trust_env=False)

    # ---------- 1. 确认账户 ----------
    r = client.get(API + "/accounts")
    r.raise_for_status()
    accounts = r.json()
    acc = accounts[0] if isinstance(accounts, list) else accounts
    print(f"账户: {acc.get('name')} (slug={acc.get('slug')})")

    # ---------- 2. 站点：复用已记录 / 按名查找 / 新建 ----------
    site = None
    site_id = get_site_id()
    if site_id:
        r = client.get(f"{API}/sites/{site_id}")
        if r.status_code == 200:
            site = r.json()
            print(f"复用站点: {site.get('name')} ({site_id})")

    if site is None:
        r = client.get(API + "/sites", params={"per_page": 100})
        if r.status_code == 200:
            for s in r.json():
                if s.get("name") == args.site_name:
                    site = s
                    print(f"找到同名站点: {site.get('name')} ({site.get('id')})")
                    break

    if site is None:
        r = client.post(API + "/sites", json={"name": args.site_name})
        if r.status_code >= 400:
            print(f"错误：创建站点失败 {r.status_code} {r.text[:300]}", file=sys.stderr)
            sys.exit(3)
        site = r.json()
        print(f"已创建站点: {site.get('name')} ({site.get('id')})")

    site_id = site["id"]
    SITE_ID_FILE.write_text(site_id, encoding="utf-8")

    # ---------- 3. 计算文件摘要 ----------
    files = collect_files()
    digests = {}
    for url_path, local in files.items():
        digests[url_path] = hashlib.sha1(local.read_bytes()).hexdigest()
    print(f"待部署文件 {len(files)} 个")

    # ---------- 4. 创建 deploy（仅上传 required 中的文件） ----------
    r = client.post(f"{API}/sites/{site_id}/deploys", json={"files": digests})
    if r.status_code >= 400:
        print(f"错误：创建部署失败 {r.status_code} {r.text[:300]}", file=sys.stderr)
        sys.exit(4)
    deploy = r.json()
    deploy_id = deploy["id"]
    required = set(deploy.get("required") or [])
    print(f"部署 ID: {deploy_id} | 需上传 {len(required)} 个文件")

    # ---------- 5. 上传所需文件 ----------
    uploaded = 0
    for url_path, local in files.items():
        if required and digests[url_path] not in required:
            continue
        resp = client.put(
            f"{API}/deploys/{deploy_id}/files{url_path}",
            content=local.read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
        )
        if resp.status_code >= 400:
            print(f"错误：上传 {url_path} 失败 {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            sys.exit(5)
        uploaded += 1
    print(f"已上传 {uploaded} 个文件")

    # ---------- 6. 等待部署就绪 ----------
    final = None
    for _ in range(30):
        r = client.get(f"{API}/deploys/{deploy_id}")
        if r.status_code == 200:
            d = r.json()
            if d.get("state") == "ready":
                final = d
                break
        import time
        time.sleep(2)

    url = (final or deploy).get("ssl_url") or (final or deploy).get("url") or site.get("ssl_url")
    state = (final or deploy).get("state")
    print(f"部署状态: {state}")
    print(f"线上地址: {url}")
    print(f"管理页:   https://app.netlify.com/sites/{site.get('name')}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
