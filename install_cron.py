#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def cron_text():
    python = shutil.which("python3") or "/usr/bin/python3"
    dws = shutil.which("dws")
    path = "/usr/local/bin:/usr/bin:/bin"
    if dws:
        path = str(Path(dws).parent) + ":" + path
    lines = [
        "SHELL=/bin/bash",
        "PATH=" + path,
        "*/30 10-21 * * * root cd %s && %s run_daily.py >> state/cron.log 2>&1" % (ROOT, python),
        "",
    ]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    text = cron_text()
    print(text)
    if not args.install:
        print("上面是定时任务内容。在服务器上用 root 执行 python3 install_cron.py --install 才会装上。")
        return 0
    if os.geteuid() != 0:
        print("当前不是 root，没有安装。", file=sys.stderr)
        return 1
    dest = Path("/etc/cron.d/product-daily-publisher")
    dest.write_text(text, encoding="utf-8")
    dest.chmod(0o644)
    print("已安装", dest)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
