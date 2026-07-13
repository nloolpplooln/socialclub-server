# GTA SocialClub 玩家查询系统 — 完整部署教程

---

## 一、安装环境（只需一次）

### 1. 装 Python

下载 Python 3.14：https://www.python.org/downloads/

安装时勾选 **Add Python to PATH**。

验证：
```bash
python --version
# Python 3.14.x
```

### 2. 解压项目

```
socialclub/
├── app/            # API 服务源码
├── plugin/         # AstrBot 插件
├── docs/           # 奖章列表、判定规则
├── static/         # Web UI
├── requirements.txt
├── cookie.txt      # 放你的 R* Cookie
├── start_api.bat   # 启动 API
└── start_bot.bat   # 启动 QQ 机器人
```

### 3. 创建虚拟环境 + 安装依赖

```bash
cd socialclub
python -m venv .venv314
.venv314\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 二、配置 Cookie

> R* BearerToken 只有 5 分钟寿命，但服务会自动续期。Cookie 约 24 小时过期，届时需重新抓取。

### 操作步骤

1. 浏览器打开 https://socialclub.rockstargames.com 并登录
2. 按 **F5** 刷新页面
3. 按 **F12** → **Application**（应用程序）→ **Cookies** → `https://socialclub.rockstargames.com`
4. 按 **Ctrl+A** 全选 → **Ctrl+C** 复制
5. 打开 `cookie.txt` → 粘贴覆盖 → 保存

---

## 三、启动 API 服务

### 双击启动（推荐）

双击 `start_api.bat`

### 或者命令行

```bash
.venv314\Scripts\python.exe -B -m uvicorn app.main:app --host 0.0.0.0 --port 8686
```

### 验证

浏览器打开 http://localhost:8686/health

```json
{"has_token":true,"refresh_ready":true,"missing_keys":[]}
```

Web 面板：http://localhost:8686/ui

## API 接口

```bash
# 完整查询（含异常检测）
curl "http://localhost:8686/api/player?nickname=oolpploo"

# 奖章查询（含异常检测）
curl "http://localhost:8686/api/player/awards?nickname=oolpploo"
```

---

## 四、接入 QQ 机器人

### 前提

- 已部署 [AstrBot](https://github.com/Soulter/AstrBot) + NapCat QQ 连接器
- AstrBot 使用 Python 3.14 运行（关键！）

### 安装插件

1. 复制 `plugin/` 目录下的所有文件到 AstrBot 的 `data/plugins/astrbot_plugin_gta_online_helper/`
2. 重启 AstrBot

### AstrBot 启动命令

```bash
# 在 AstrBot 目录下执行：
export PYTHONDONTWRITEBYTECODE=1
"/path/to/.venv314/Scripts/python.exe" main.py
```

### 注入 Cookie 到机器人

私聊机器人发送：
```
/gta 更新ck <从浏览器复制的完整Cookie>
```

---

## 五、插件命令

| 命令 | 功能 |
|---|---|
| `帮助` | 显示全部命令 |
| `查生涯 <昵称>` | 完整生涯数据 + 30项异常检测 |
| `查奖章 <奖章名> [昵称]` | 奖章定义 + 玩家进度 |
| `查战眼 <RID/昵称>` | 查封禁状态 |
| `pk <玩家1> <玩家2>` | 双方数据对比 |
| `查统计/战斗/犯罪/载具/收支/技能/武器 <昵称>` | 单项统计 |
| `/gta 绑定 <昵称>` | 绑定你的 GTA ID |
| `/gta me` | 查看绑定玩家 |

---

## 六、常见问题

### Q: 启动报 "cookie.txt 不存在"

先完成**第二步**。

### Q: 查询报 401

Cookie 过期了，重新做**第二步**。

### Q: 查询报 429

R* 限流，等 15-30 分钟。

### Q: AstrBot 启动 segfault

必须用 `export PYTHONDONTWRITEBYTECODE=1` 且 Python 3.14。
