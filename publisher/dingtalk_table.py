"""把链接回填到使用者自己的钉钉 AI 表格。"""
import json
import shutil
import subprocess
from datetime import datetime

FIELDS = {
    "devto": "devto链接",
    "devto_2": "devto链接_2",
    "codelegion": "CodeLegion链接",
    "codelegion_2": "CodeLegion链接_2",
    "medium": "Medium链接",
    "zenn": "Zenn链接",
    "qiita": "Qiita链接",
}


def _dws(*args):
    if not shutil.which("dws"):
        raise RuntimeError("未安装钉钉 CLI。先按 references/dingtalk-cli.md 安装并登录")
    result = subprocess.run(["dws", *args, "--format", "json"], capture_output=True, text=True, timeout=90)
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")
        raise RuntimeError(detail[:240] or "钉钉命令失败")
    return json.loads(result.stdout or "{}")


def _fields(env):
    data = _dws("aitable", "field", "get", "--base-id", env["DINGTALK_BASE_ID"], "--table-id", env["DINGTALK_TABLE_ID"])
    found = {}

    def walk(node):
        if isinstance(node, dict):
            name = node.get("name") or node.get("fieldName")
            field_id = node.get("fieldId") or node.get("id")
            if name and field_id and str(field_id).startswith("fld"):
                found[name] = field_id
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    if "关键词" not in found:
        raise RuntimeError("钉钉表缺少「关键词」字段，请先运行 setup_table.py")
    return found


def _record_ids(node, found):
    if isinstance(node, dict):
        record_id = node.get("recordId") or node.get("id")
        if record_id and str(record_id).startswith("rec"):
            found.append(record_id)
        for value in node.values():
            _record_ids(value, found)
    elif isinstance(node, list):
        for item in node:
            _record_ids(item, found)


def sync(env, keyword, batch, links):
    fields = _fields(env)
    filters = json.dumps({"operator": "and", "operands": [
        {"operator": "eq", "operands": [fields["关键词"], keyword]}
    ]}, ensure_ascii=False)
    data = _dws("aitable", "record", "query", "--base-id", env["DINGTALK_BASE_ID"],
                "--table-id", env["DINGTALK_TABLE_ID"], "--filters", filters)
    ids = []
    _record_ids(data, ids)
    ids = list(dict.fromkeys(ids))
    if len(ids) > 1:
        raise RuntimeError("钉钉表里同一个关键词有多行，停止写入")
    cells = {}
    if "批次" in fields:
        cells[fields["批次"]] = batch
    if "状态" in fields:
        cells[fields["状态"]] = "已发布"
    if "发布日期" in fields:
        cells[fields["发布日期"]] = datetime.now().strftime("%Y-%m-%d %H:%M:%S+08:00")
    for slot, url in links.items():
        name = FIELDS.get(slot)
        if name and url and name in fields:
            cells[fields[name]] = url
    if ids:
        records = json.dumps([{"recordId": ids[0], "cells": cells}], ensure_ascii=False)
        _dws("aitable", "record", "update", "--base-id", env["DINGTALK_BASE_ID"],
             "--table-id", env["DINGTALK_TABLE_ID"], "--records", records)
    else:
        cells[fields["关键词"]] = keyword
        records = json.dumps([{"cells": cells}], ensure_ascii=False)
        _dws("aitable", "record", "create", "--base-id", env["DINGTALK_BASE_ID"],
             "--table-id", env["DINGTALK_TABLE_ID"], "--records", records)
