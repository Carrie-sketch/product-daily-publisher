"""已跑通的平台对接。密钥只从配置读取。"""
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

DEVTO = "https://dev.to/api/articles"
CODELEGION = "https://coderlegion.com/api/v1/posts"
QIITA = "https://qiita.com/api/v2/items"


def _post(url, headers, payload, timeout=60):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(240).decode("utf-8", "replace").replace("\n", " ")
        raise RuntimeError("HTTP %s %s" % (error.code, detail[:180])) from None


def _get(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def devto(title, body, tags, api_key):
    clean = [re.sub(r"[^a-zA-Z0-9]", "", tag)[:20] for tag in tags if tag][:4]
    data = _post(DEVTO, {"api-key": api_key, "Content-Type": "application/json"}, {
        "article": {"title": title, "body_markdown": body, "published": True, "tags": clean},
    })
    return data.get("url") or ""


def codelegion(title, body, tags, canonical, api_key, user_id, category_id):
    data = _post(CODELEGION, {
        "X-API-Key": api_key,
        "User-Id": str(user_id),
        "Content-Type": "application/json",
    }, {
        "title": title,
        "content": body,
        "tags": tags[:4],
        "canonical_url": canonical,
        "category_id": str(category_id),
    })
    item_id = (data.get("data") or {}).get("id")
    if not item_id:
        raise RuntimeError("CodeLegion 未返回文章 id")
    return "https://coderlegion.com/%s" % item_id


def qiita(title, body, token, user):
    last = "未知错误"
    for attempt in range(4):
        try:
            data = _post(QIITA, {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            }, {
                "title": title[:255],
                "body": body,
                "private": False,
                "tweet": False,
                "tags": [{"name": tag, "versions": []} for tag in ("Tech", "Security", "Linux")],
            })
        except RuntimeError as error:
            last = str(error)
            if "HTTP 429" in last and attempt < 3:
                wait = 300 * (attempt + 1)
                print("  Qiita 限流，等待 %ss" % wait, flush=True)
                time.sleep(wait)
                continue
            raise
        author = ((data.get("user") or {}).get("id") or "")
        if author and author != user:
            raise RuntimeError("Qiita 账号不是配置中的用户")
        if not data.get("url"):
            raise RuntimeError("Qiita 未返回链接")
        return data["url"]
    raise RuntimeError(last)


def _slug(keyword):
    digest = hashlib.sha1(keyword.encode("utf-8")).hexdigest()[:8]
    day = datetime.now().strftime("%Y%m%d")
    raw = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")[:20].strip("-") or "article"
    slug = ("post-%s-%s-%s" % (raw, day, digest))[:50].strip("-")
    return slug if len(slug) >= 12 else (slug + "-article")[:50]


def zenn(title, body, keyword, env):
    repo = env["ZENN_REPO"]
    branch = env.get("ZENN_BRANCH") or "main"
    user = env["ZENN_USER"].strip("/")
    slug = _slug(keyword)
    work = Path(env.get("ZENN_WORKDIR") or "/tmp/product-daily-zenn")
    ssh = env.get("ZENN_SSH_COMMAND") or ""
    child = os.environ.copy()
    if ssh:
        child["GIT_SSH_COMMAND"] = ssh
    if not (work / ".git").exists():
        if work.exists():
            subprocess.run(["rm", "-rf", str(work)], check=True)
        subprocess.run(["git", "clone", "--depth", "1", "--branch", branch, repo, str(work)], check=True, env=child)
    else:
        subprocess.run(["git", "fetch", "origin", branch], cwd=work, check=True, env=child)
        subprocess.run(["git", "checkout", branch], cwd=work, check=True, env=child)
        subprocess.run(["git", "reset", "--hard", "origin/" + branch], cwd=work, check=True, env=child)
    articles = work / "articles"
    articles.mkdir(exist_ok=True)
    safe = title.replace('"', "")
    text = "\n".join([
        "---", 'title: "%s"' % safe, 'emoji: "📝"', 'type: "tech"',
        'topics: ["tech"]', "published: true", "---", "", body,
    ])
    path = articles / (slug + ".md")
    path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "config", "user.name", "daily-publisher"], cwd=work, check=True)
    subprocess.run(["git", "config", "user.email", "daily-publisher@localhost"], cwd=work, check=True)
    subprocess.run(["git", "add", str(path.relative_to(work))], cwd=work, check=True)
    subprocess.run(["git", "commit", "-m", "Publish " + slug], cwd=work, check=True)
    subprocess.run(["git", "push", "origin", branch], cwd=work, check=True, env=child)
    return "https://zenn.dev/%s/articles/%s" % (user, slug)


def verify(cfg):
    env = cfg["env"]
    enabled = {slot.get("id") for slot in (cfg["platforms"].get("slots") or []) if isinstance(slot, dict) and slot.get("enabled")}
    if "devto" in enabled:
        me = _get("https://dev.to/api/users/me", {"api-key": env["DEVTO_API_KEY"]})
        print("dev.to 主账号核对通过:", me.get("username") or me.get("name"))
    if "devto_2" in enabled:
        me = _get("https://dev.to/api/users/me", {"api-key": env["DEVTO_API_KEY_2"]})
        print("dev.to 副账号核对通过:", me.get("username") or me.get("name"))
    if "qiita" in enabled:
        me = _get(QIITA.replace("/items", "/authenticated_user"), {"Authorization": "Bearer " + env["QIITA_TOKEN"]})
        if me.get("id") != env["QIITA_USER"]:
            raise RuntimeError("Qiita 账号与 QIITA_USER 不一致")
        print("Qiita 账号核对通过:", me.get("id"))
