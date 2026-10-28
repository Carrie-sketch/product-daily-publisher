"""调用使用者自己的模型。网关地址只来自 model.env。"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise RuntimeError("模型没有返回 JSON")


def _http(prompt, env, model_name):
    base = env["LLM_BASE_URL"].rstrip("/")
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + env["LLM_API_KEY"], "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.load(response)
    return data["choices"][0]["message"]["content"]


def _codex(prompt, env, model_name):
    provider = env.get("LLM_CODEX_PROVIDER") or ""
    if not provider:
        raise RuntimeError("LLM_PROVIDER=codex 时必须设置 LLM_CODEX_PROVIDER")
    fd, name = tempfile.mkstemp(prefix="publisher-model-", suffix=".txt")
    os.close(fd)
    out = Path(name)
    work = Path(tempfile.mkdtemp(prefix="publisher-codex-"))
    try:
        child = os.environ.copy()
        child["LLM_API_KEY"] = env["LLM_API_KEY"]
        child["LLM_BASE_URL"] = env["LLM_BASE_URL"]
        child["LLM_MODEL"] = model_name
        result = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only",
             "--color", "never", "-m", model_name, "-c", "model_provider=" + provider, "-o", str(out), prompt],
            capture_output=True, text=True, timeout=240, stdin=subprocess.DEVNULL, env=child, cwd=work)
        if result.returncode or not out.exists():
            detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")
            raise RuntimeError(detail[:240] or "codex 失败")
        return out.read_text(encoding="utf-8")
    finally:
        out.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)


def complete(prompt, env):
    provider = (env.get("LLM_PROVIDER") or "http").lower()
    models = [env["LLM_MODEL"]]
    if env.get("LLM_FALLBACK_MODEL"):
        models.append(env["LLM_FALLBACK_MODEL"])
    last = "未知错误"
    for model_name in models:
        for attempt in range(2):
            try:
                text = _codex(prompt, env, model_name) if provider == "codex" else _http(prompt, env, model_name)
                return _parse(text)
            except Exception as error:
                last = str(error)[:240]
                if attempt == 0:
                    time.sleep(10)
        print("模型失败，尝试备用:", model_name, flush=True)
    raise RuntimeError("模型接口失败：" + last)
