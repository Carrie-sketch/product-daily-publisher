#!/usr/bin/env python3
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = Path.home() / ".config/product-daily-publisher"

def main():
    CONFIG.mkdir(mode=0o700, exist_ok=True)
    copied = []
    for src in (ROOT / "templates").iterdir():
        if not src.is_file():
            continue
        name = src.name.removesuffix(".example")
        dest = CONFIG / name
        if dest.exists():
            continue
        shutil.copy(src, dest)
        copied.append(dest.name)
    blanks = {
        "keys.env": "DEVTO_API_KEY=\nDEVTO_API_KEY_2=\nCODLEGION_API_KEY=\nCODLEGION_API_KEY_2=\nCODELEGION_USER_ID=\nCODELEGION_USER_ID_2=\nCODELEGION_CATEGORY_ID=\nQIITA_TOKEN=\nQIITA_USER=\nZENN_REPO=\nZENN_USER=\nZENN_BRANCH=main\nZENN_SSH_COMMAND=\nDINGTALK_BASE_ID=\nDINGTALK_TABLE_ID=\n",
        "model.env": "LLM_API_KEY=\nLLM_BASE_URL=\nLLM_MODEL=\nLLM_FALLBACK_MODEL=\nLLM_PROVIDER=http\nLLM_CODEX_PROVIDER=\n",
    }
    for name, content in blanks.items():
        path = CONFIG / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            copied.append(name)
        path.chmod(0o600)
    print("配置目录:", CONFIG)
    if copied:
        print("已复制空模板:", ", ".join(copied))
    else:
        print("配置文件已存在，没有覆盖。")
    print("命令检查:")
    for cmd in ("python3", "node", "npm", "dws"):
        found = shutil.which(cmd)
        print("-", cmd, found or "未安装")
    if not shutil.which("dws"):
        print("下一步先安装钉钉 CLI：")
        print("  npm i -g dingtalk-workspace-cli")
        print("  dws auth login")
        print("服务器没有浏览器时用: dws auth login --device")
    print("然后填写这些文件，不要把内容发到群里：")
    for name in ("product.yaml", "keywords.csv", "keys.env", "model.env"):
        print("-", CONFIG / name)
    print("填完后运行: python3 run_daily.py --check")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
