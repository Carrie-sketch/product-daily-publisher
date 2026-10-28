# 用「百智办公」写的海外技术内容生成与分发系统

这是每日发文的任务壳，不绑定任何一个产品。拿到后先看 `落地.md`，按里面的命令做到定时任务安装成功。

把整个目录复制到自己的技能目录，例如 `~/.claude/skills/product-daily-publisher/`。

复制 `templates/` 到 `~/.config/product-daily-publisher/`，按自己的产品改名。

自己申请各平台密钥，写入 `keys.env` 和 `model.env`，权限设为 `600`。

不要向他人索要或转发别人的密钥、账号主页、活动短链、钉钉登录令牌或服务器地址。

长尾词写在 `keywords.csv`。换产品就换这份表，不要沿用别人的关键词。

英文平台默认一天 2 个关键词、每个关键词 4 个槽位。Zenn 和 Qiita 默认每个账号一天 1 篇（文章风控较严，有多发删文现象，所以每个账号每个平台先发 1 篇），是新增日语博客平台。

每天自动发文必须部署到一台你自己的服务器上，用系统定时任务在每天 10:00 启动。只放在聊天或个人电脑上，关机或关掉对话后不会自动跑。

## 交给 AI 时怎么说

把本目录和下面这句话一起给 AI：

> 按 product-daily-publisher 的 SKILL.md 从第 1 步做到最后。每一步先检查缺什么。缺信息就停下来问我，不要猜测，不要发文。密钥只写入配置文件，不要出现在回复里。最后部署到我的服务器，并确认每天 10:00 会自动跑。

AI 必须按 `references/steps.md` 的顺序执行。没有「完成标准」就不得进入下一步。

记录表表头和写文章规则已经固定，AI 不要自行改名或省略。

表头是：关键词、批次、发布日期、状态、devto链接、devto链接_2、CodeLegion链接、CodeLegion链接_2、Medium链接、Zenn链接、Qiita链接。

每篇文章文末必须加引流链接。链接只来自 `product.yaml` 的 `footer_links`。这里没填，AI 必须停下来问，不能发文。

## 这个技能给你什么

不是空模板。你不需要重新摸索平台接法、发文顺序、限流间隔、日语平台限制、记录表表头和失败后能不能重发。

这些都写在 `references/playbook.md`。使用者只补自己的产品资料、长尾词和密钥。AI 必须按这份资料实现和部署，不能另起一套发文流程。

## 直接运行

配置补齐后，在技能目录执行：

```bash
python3 run_daily.py --check
python3 run_daily.py --verify
```

`--check` 只列出还缺什么。`--verify` 只读核对账号，不发文。确认无误后，把整个技能目录和 `~/.config/product-daily-publisher/` 放到常开的服务器，按 `cron.example` 安装每天 10:00 开始的定时任务。

服务器上真正发文的命令是 `python3 run_daily.py`。已成功的槽位记在 `state/progress.json`，重试不会重发。

记录表用钉钉 AI 表格。没有安装钉钉 CLI 时，先按 `references/dingtalk-cli.md` 执行 `npm i -g dingtalk-workspace-cli`，再 `dws auth login`。服务器没有浏览器时用 `dws auth login --device`。登录后再运行 `python3 setup_table.py`。
