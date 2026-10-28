"""读取使用者自己的配置。本文件不含任何密钥。"""
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("PUBLISHER_CONFIG") or Path.home() / ".config/product-daily-publisher")
ROOT = Path(__file__).resolve().parent.parent


def _env_file(path):
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _cast(value):
    value = value.strip().strip('"').strip("'")
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value in ("true", "false"):
        return value == "true"
    if value.isdigit():
        return int(value)
    return value


def _yaml(path):
    if not path.exists():
        return {}
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))

    def parse(index, indent):
        if index >= len(lines) or lines[index][0] < indent:
            return {}, index
        if lines[index][1].startswith("- "):
            items = []
            while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
                content = lines[index][1][2:]
                index += 1
                if ":" in content:
                    key, value = content.split(":", 1)
                    node = {key.strip(): _cast(value) if value.strip() else {}}
                    if not value.strip():
                        child, index = parse(index, indent + 2)
                        node[key.strip()] = child
                    while index < len(lines) and lines[index][0] > indent and not lines[index][1].startswith("- "):
                        child_indent, child_line = lines[index]
                        key, value = child_line.split(":", 1)
                        index += 1
                        if value.strip():
                            node[key.strip()] = _cast(value)
                        else:
                            child, index = parse(index, child_indent + 2)
                            node[key.strip()] = child
                    items.append(node)
                else:
                    items.append(_cast(content))
            return items, index
        mapping = {}
        while index < len(lines) and lines[index][0] == indent and not lines[index][1].startswith("- "):
            key, value = lines[index][1].split(":", 1)
            index += 1
            if value.strip():
                mapping[key.strip()] = _cast(value)
            else:
                child, index = parse(index, indent + 2)
                mapping[key.strip()] = child
        return mapping, index

    parsed, _ = parse(0, lines[0][0] if lines else 0)
    return parsed


def load():
    env = os.environ.copy()
    env.update(_env_file(CONFIG_DIR / "keys.env"))
    env.update(_env_file(CONFIG_DIR / "model.env"))
    product = _yaml(CONFIG_DIR / "product.yaml")
    platforms = _yaml(CONFIG_DIR / "platforms.yaml")
    keywords = []
    csv_path = CONFIG_DIR / "keywords.csv"
    if csv_path.exists():
        lines = [line.strip() for line in csv_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            header = [part.strip() for part in lines[0].split(",")]
            for line in lines[1:]:
                parts = [part.strip() for part in line.split(",")]
                if not any(parts):
                    continue
                row = {header[i]: parts[i] if i < len(parts) else "" for i in range(len(header))}
                if row.get("keyword"):
                    keywords.append(row)
    return {"env": env, "product": product, "platforms": platforms, "keywords": keywords}


def missing(cfg):
    gaps = []
    product = cfg["product"]
    for key in ("product_name", "one_line"):
        if not str(product.get(key) or "").strip():
            gaps.append("product.yaml: " + key)
    if not product.get("official_docs"):
        gaps.append("product.yaml: official_docs")
    links = product.get("footer_links") or []
    if not any(isinstance(item, dict) and item.get("url") and item.get("label") for item in links):
        gaps.append("product.yaml: footer_links")
    if len(cfg["keywords"]) < 2:
        gaps.append("keywords.csv: 至少 2 条已确认的长尾关键词")
    env = cfg["env"]
    if not env.get("LLM_API_KEY") or not env.get("LLM_BASE_URL") or not env.get("LLM_MODEL"):
        gaps.append("model.env: LLM_API_KEY、LLM_BASE_URL、LLM_MODEL")
    enabled = {slot.get("id"): slot for slot in (cfg["platforms"].get("slots") or []) if isinstance(slot, dict) and slot.get("enabled")}
    needed = {
        "devto": ["DEVTO_API_KEY"],
        "devto_2": ["DEVTO_API_KEY_2"],
        "codelegion": ["CODLEGION_API_KEY", "CODELEGION_USER_ID", "CODELEGION_CATEGORY_ID"],
        "codelegion_2": ["CODLEGION_API_KEY_2", "CODELEGION_USER_ID_2", "CODELEGION_CATEGORY_ID"],
        "qiita": ["QIITA_TOKEN", "QIITA_USER"],
        "zenn": ["ZENN_REPO", "ZENN_USER"],
    }
    for slot_id, keys in needed.items():
        if slot_id in enabled:
            for key in keys:
                if not env.get(key):
                    gaps.append("keys.env: " + key)
    if not env.get("DINGTALK_BASE_ID") or not env.get("DINGTALK_TABLE_ID"):
        gaps.append("keys.env: DINGTALK_BASE_ID、DINGTALK_TABLE_ID。未建表时先安装 dws 并运行 setup_table.py")
    return gaps
