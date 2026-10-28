"""按固定顺序发当天文章。已成功的槽位不会重发。"""
import datetime
import fcntl
import json
import time
from pathlib import Path

from publisher.config import ROOT
from publisher.generate import article
from publisher.platforms import codelegion, devto, qiita, zenn
from publisher import dingtalk_table as table

STATE = ROOT / "state"
ORDER = ("devto", "devto_2", "codelegion", "codelegion_2")


def _enabled(cfg):
    return {slot.get("id"): slot for slot in (cfg["platforms"].get("slots") or []) if isinstance(slot, dict) and slot.get("enabled")}


def _state():
    path = STATE / "progress.json"
    if not path.exists():
        return {"done_keywords": [], "days": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(data):
    STATE.mkdir(mode=0o700, exist_ok=True)
    path = STATE / "progress.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _publish_slot(cfg, slot, draft, links):
    env = cfg["env"]
    if slot == "devto":
        return devto(draft["title"], draft["body"], draft["tags"], env["DEVTO_API_KEY"])
    if slot == "devto_2":
        return devto(draft["title"], draft["body"], draft["tags"], env["DEVTO_API_KEY_2"])
    if slot == "codelegion":
        if not links.get("devto"):
            raise RuntimeError("主 CodeLegion 缺少主 dev.to 链接")
        return codelegion(draft["title"], draft["body"], draft["tags"], links["devto"],
                          env["CODLEGION_API_KEY"], env["CODELEGION_USER_ID"], env["CODELEGION_CATEGORY_ID"])
    if slot == "codelegion_2":
        if not links.get("devto_2"):
            raise RuntimeError("副 CodeLegion 缺少副 dev.to 链接")
        return codelegion(draft["title"], draft["body"], draft["tags"], links["devto_2"],
                          env["CODLEGION_API_KEY_2"], env["CODELEGION_USER_ID_2"], env["CODELEGION_CATEGORY_ID"])
    if slot == "qiita":
        return qiita(draft["title"], draft["body"], env["QIITA_TOKEN"], env["QIITA_USER"])
    if slot == "zenn":
        return zenn(draft["title"], draft["body"], draft["keyword"], env)
    raise RuntimeError("未知槽位 " + slot)


def run(cfg, dry_run=False):
    lock_path = STATE / "lock"
    STATE.mkdir(mode=0o700, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _run_locked(cfg, dry_run)


def _run_locked(cfg, dry_run):
    today = datetime.date.today().isoformat()
    progress = _state()
    day = progress["days"].setdefault(today, {"keywords": [], "slots": {}, "complete": False})
    if day.get("complete"):
        print("今天已完成，跳过")
        return 0
    enabled = _enabled(cfg)
    if not day["keywords"]:
        pending = [row for row in cfg["keywords"] if row["keyword"] not in progress["done_keywords"]]
        day["keywords"] = pending[: int(cfg["platforms"].get("keywords_per_day") or 2)]
        _save(progress)
    if len(day["keywords"]) < 1:
        raise RuntimeError("没有待发关键词")
    for index, row in enumerate(day["keywords"]):
        keyword = row["keyword"]
        print("==", keyword, flush=True)
        links = {}
        slots = [slot for slot in ORDER if slot in enabled]
        if index == 0:
            slots += [slot for slot in ("zenn", "qiita") if slot in enabled]
        for slot in slots:
            key = keyword + "|" + slot
            if key in day["slots"]:
                links[slot] = day["slots"][key]
                print("  已有", slot, links[slot])
                continue
            if slot in ("zenn", "qiita") and any(key.endswith("|" + slot) for key in day["slots"]):
                print("  今天已发过", slot)
                continue
            if slot == "codelegion_2" and "codelegion" in links:
                time.sleep(30)
            draft = {"title": keyword, "body": "dry-run", "tags": ["tech"], "keyword": keyword}
            if not dry_run:
                draft = article(cfg, keyword, slot)
                draft["keyword"] = keyword
                url = _publish_slot(cfg, slot, draft, links)
                if not url:
                    raise RuntimeError(slot + " 未返回链接")
                links[slot] = url
                day["slots"][key] = url
                _save(progress)
                print("  ✓", slot, url, flush=True)
            else:
                print("  (dry-run)", slot)
        if not dry_run:
            table.sync(cfg["env"], keyword, row.get("batch") or "", links)
            if keyword not in progress["done_keywords"]:
                progress["done_keywords"].append(keyword)
            _save(progress)
        if index + 1 < len(day["keywords"]):
            time.sleep(int(cfg["platforms"].get("gap_between_keywords_seconds") or 60))
    if not dry_run:
        day["complete"] = True
        _save(progress)
        print("当天发布完成")
    return 0
