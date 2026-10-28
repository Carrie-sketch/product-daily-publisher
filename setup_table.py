#!/usr/bin/env python3
"""在使用者自己的钉钉里创建发文记录表。"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publisher.config import CONFIG_DIR, load

FIELDS = [
    {"fieldName": "关键词", "type": "text"},
    {"fieldName": "批次", "type": "text"},
    {"fieldName": "发布日期", "type": "date"},
    {"fieldName": "状态", "type": "singleSelect", "config": {"options": [{"name": "待发布"}, {"name": "已发布"}]}},
    {"fieldName": "devto链接", "type": "url"},
    {"fieldName": "devto链接_2", "type": "url"},
    {"fieldName": "CodeLegion链接", "type": "url"},
    {"fieldName": "CodeLegion链接_2", "type": "url"},
    {"fieldName": "Medium链接", "type": "url"},
    {"fieldName": "Zenn链接", "type": "url"},
    {"fieldName": "Qiita链接", "type": "url"},
]


def main():
    if not shutil.which("dws"):
        print("未安装钉钉 CLI。按 references/dingtalk-cli.md 安装并登录后再运行。")
        return 2
    cfg = load()
    env = cfg["env"]
    if env.get("DINGTALK_BASE_ID") and env.get("DINGTALK_TABLE_ID"):
        print("keys.env 已有 DINGTALK_BASE_ID 和 DINGTALK_TABLE_ID，不重复建表。")
        return 0
    request = json.dumps([{"name": "发文记录", "fields": FIELDS}], ensure_ascii=False)
    result = subprocess.run(
        ["dws", "aitable", "+base-bootstrap", "--name", "每日发文记录", "--tables", request, "--format", "json"],
        capture_output=True, text=True, timeout=120)
    if result.returncode:
        print((result.stderr or result.stdout or "建表失败")[:500])
        return 1
    data = json.loads(result.stdout or "{}")
    found = {}

    def walk(node, parent_key=""):
        if isinstance(node, dict):
            for key, value in node.items():
                low = key.lower()
                if low in ("baseid", "base_id") and isinstance(value, str):
                    found["base"] = value
                elif low in ("tableid", "table_id") and isinstance(value, str):
                    found.setdefault("table", value)
                else:
                    walk(value, low)
        elif isinstance(node, list):
            for item in node:
                walk(item, parent_key)

    walk(data)
    if not found.get("base") or not found.get("table"):
        secret = Path.home() / ".config/product-daily-publisher/table-create.json"
        secret.parent.mkdir(mode=0o700, exist_ok=True)
        secret.write_text(result.stdout, encoding="utf-8")
        secret.chmod(0o600)
        print("建表已返回，但没解析出 ID。原始结果已写到配置目录的 table-create.json，不要外发这个文件。")
        return 1
    env_path = CONFIG_DIR / "keys.env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updates = {"DINGTALK_BASE_ID": found["base"], "DINGTALK_TABLE_ID": found["table"]}
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            out.append(key + "=" + updates[key])
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(key + "=" + value)
    env_path.parent.mkdir(mode=0o700, exist_ok=True)
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    env_path.chmod(0o600)
    print("钉钉记录表已创建，ID 已写入 keys.env。不要把 ID 发到群里。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
