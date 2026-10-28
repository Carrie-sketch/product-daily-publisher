"""按配置生成不同角度的文章。不包含任何产品事实。"""
from publisher.model import complete

ANGLES = {
    "devto": "How to 操作步骤。写给第一次部署的人。",
    "devto_2": "Why I 决策说明。写为什么这样放、不这样放会怎样。",
    "codelegion": "A vs B 取舍。写什么情况下需要它，什么情况下先不要上。",
    "codelegion_2": "故障排查。写一个具体误配置，以及用什么日志或页面确认已经修好。",
    "zenn": "日语操作步骤。不要翻译其他槽位。",
    "qiita": "日语排查清单。不要翻译 Zenn 稿。",
}


def footer(product, language):
    lines = ["---", ""]
    intro = "想继续看这个产品，可以从这里开始：" if language != "ja" else "この製品を続けるなら、ここから確認してください："
    lines.append(intro)
    lines.append("")
    for item in product.get("footer_links") or []:
        if isinstance(item, dict) and item.get("label") and item.get("url"):
            lines.append("- %s: %s" % (item["label"], item["url"]))
    return "\n".join(lines) + "\n"


def article(cfg, keyword, slot):
    product = cfg["product"]
    language = "ja" if slot in ("zenn", "qiita") else "en"
    prompt = (
        "Return JSON only with keys title, body, tags. "
        "Write one original article. "
        "Product: %s. %s. "
        "Keyword: %s. Angle: %s. Language: %s. "
        "Use only these official docs and allowed facts. Do not invent numbers, customers, prices, or features. "
        "Forbidden: %s. Forbidden phrases: %s. "
        "Body needs numbered steps, one concrete failure, and what confirms the fix. "
        "Add 3 to 5 FAQ items as level-3 headings. Do not add a link list; the publisher appends it. "
        "Tags: exposure %s, precise %s, competitive %s. Use at most 4. Do not use disabled tags %s. "
        "Docs: %s. Facts: %s."
    ) % (
        product.get("product_name"), product.get("one_line"), keyword, ANGLES[slot], language,
        product.get("forbidden") or [], product.get("forbidden_phrases") or [],
        (product.get("tag_layers") or {}).get("exposure") or [],
        (product.get("tag_layers") or {}).get("precise") or [],
        (product.get("tag_layers") or {}).get("competitive") or [],
        product.get("disabled_tags") or [],
        product.get("official_docs") or [], product.get("allowed_facts") or [],
    )
    data = complete(prompt, cfg["env"])
    title = str(data.get("title") or "").strip()
    body = str(data.get("body") or "").strip()
    tags = data.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    if len(title) < 8 or len(body) < 600:
        raise RuntimeError(slot + " 稿件太短")
    body = body.rstrip() + "\n\n" + footer(product, language)
    return {"title": title[:180], "body": body, "tags": [str(tag) for tag in tags][:4]}
