# 安装钉钉 CLI

记录表使用钉钉 AI 表格。命令行工具名是 `dws`，安装包名是 `dingtalk-workspace-cli`。

## 检查是否已安装

```bash
command -v dws && dws --version && dws auth status --format json
```

`command -v dws` 没有输出，就是没安装。`auth status` 失败，就是还没登录。

## 没有安装时

1. 先安装 Node.js 18 或更高版本，并确认 `node -v`、`npm -v` 可用。
2. 安装钉钉 CLI：

```bash
npm i -g dingtalk-workspace-cli
```

3. 再次确认：

```bash
command -v dws
dws --version
```

如果 `npm i -g` 后仍然找不到 `dws`，把 npm 全局 bin 目录加进 PATH。可用 `npm prefix -g` 查看，再把该目录下的 `bin` 加进服务器定时任务的 PATH。

## 登录

本机有浏览器：

```bash
dws auth login
```

服务器没有浏览器：

```bash
dws auth login --device
```

按命令提示完成扫码或设备码登录。登录完成后执行：

```bash
dws auth status --format json
```

必须看到已登录，才能建表和回填。不要把登录令牌写进技能包、聊天或日志。

国际版或海外版登录使用 `dws auth login --intl`。无浏览器时加 `--device`。
