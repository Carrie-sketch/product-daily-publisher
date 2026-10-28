#!/usr/bin/env python3
"""每天由服务器定时任务调用。个人电脑关机后不会自动跑。"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publisher.config import load, missing
from publisher.daily import run
from publisher.platforms import verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只检查缺什么，不发文")
    parser.add_argument("--verify", action="store_true", help="只读核对账号，不发文")
    parser.add_argument("--dry-run", action="store_true", help="不调用发布接口")
    args = parser.parse_args()
    cfg = load()
    gaps = missing(cfg)
    if gaps:
        print("还缺这些信息，不能发文：")
        for item in gaps:
            print("-", item)
        return 2
    if args.check:
        print("配置完整。下一步部署到服务器，并安装每天 10:00 的定时任务。")
        return 0
    if args.verify:
        verify(cfg)
        return 0
    return run(cfg, dry_run=args.dry_run)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BlockingIOError:
        print("已有一次发文在跑，本次退出")
        raise SystemExit(0)
