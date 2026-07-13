# SocialClub Query — GTA Online 玩家数据查询

自建 R星 玩家数据查询服务，直连 Rockstar 私有 API，获取 **等级/金钱 + 240 项深度生涯统计**。

## 功能一览

| 功能 | 说明 |
|---|---|
| 等级/金钱 | 等级、RP、现金、银行存款、帮会 |
| 深度统计 | 240+ 项：收支、技能、犯罪、载具、武器、战斗 |
| 基础资料 | 昵称、RID、所在地、好友数、帮会列表、游戏、关联账号 |
| Web 面板 | `http://localhost:8686/ui` 深色主题，搜索即用 |
| REST API | `/api/player?nickname=` 返回 JSON |
| QQ 机器人 | OneBot v11 协议 `/onebot` |
| 自动续期 | BearerToken 每 3 分钟自动刷新，一次注入长期有效 |

## 快速开始（3 步）

### 1. 安装环境

需要 **Python 3.10+**，推荐 3.14：

```bash
py -3.14 -m venv .venv314
.venv314\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 获取 R星 Cookie

1. 浏览器打开 https://socialclub.rockstargames.com 并登录
2. **F5 刷新页面**（确保 BearerToken 是全新的）
3. F12 → Application → Storage → Cookies
4. 全选所有 Cookie → 复制
5. 粘贴到项目根目录的 `cookie.txt`，保存

> ⚠️ BearerToken 只有 **5 分钟有效期**，请在 F5 刷新后 3 分钟内完成复制和后续步骤。

### 3. 启动服务

双击 `start.bat`，浏览器打开 http://localhost:8686/ui

### Docker 部署（服务器）

```bash
# 1. 准备
mkdir data
# 将 cookie.txt 放入 data/ 目录

# 2. 启动
docker-compose up -d

# 3. 查看日志
docker logs socialclub-api

# 4. 访问
# http://<服务器IP>:8686/ui
```

### 更新 Cookie

```bash
# 方法1: 替换文件后重启
cp 新cookie.txt data/cookie.txt
docker restart socialclub-api

# 方法2: 直接注入
docker exec socialclub-api python -m app.cli setckf /app/data/cookie.txt
```

---

## Web 面板

```
http://localhost:8686/ui
```

输入玩家昵称 → 回车查询。结果分三块：

- **基础资料卡片**：昵称、RID、所在地、好友、帮会、游戏、绑定账号
- **等级金钱卡片**（绿色）：等级、RP、现金、银行存款、帮会
- **生涯统计卡片**：240 项数据，按分类展开

---

## REST API

### 完整查询

```bash
GET /api/player?nickname=oolpploo

# 返回
{
  "code": 200,
  "message": "fresh",
  "body": {
    "nickname": "oolpploo",
    "profile": { "nickname": "...", "rockstar_id": 214946702, ... },
    "overview": { "rank": "370", "cash": "$1,366,649", "bank": "$25,517,361", ... },
    "stats": { "categories": { "career": {...}, "skills": {...}, ... } },
    "cached": false,
    "updated_at": 1783610559
  }
}
```

### 参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `nickname` | string | 玩家昵称（必填） |
| `force` | bool | `true` 跳过缓存强制刷新 |

### 其他端点

| 端点 | 说明 |
|---|---|
| `GET /api/player/profile?nickname=` | 仅基础资料 |
| `GET /api/player/stats?nickname=` | 仅深度统计 |
| `GET /health` | 服务健康检查（token 状态） |
| `GET /docs` | Swagger API 文档 |

---

## CLI 命令行

```bash
PY=.venv314\Scripts\python.exe

# 从文件注入 Cookie
$PY -m app.cli setckf cookie.txt

# 综合查询
$PY -m app.cli query oolpploo

# 仅查资料
$PY -m app.cli profile oolpploo

# 仅查等级和统计
$PY -m app.cli stats oolpploo

# 查看凭证状态
$PY -m app.cli show

# 手动刷新 token
$PY -m app.cli refresh
```

---

## QQ 机器人

支持 OneBot v11 HTTP 协议。配置机器人框架将上报地址指向：

```
POST http://localhost:8686/onebot
```

支持的指令：

| 指令 | 示例 |
|---|---|
| `查生涯 <昵称>` | `查生涯 oolpploo` |
| `查资料 <昵称>` | `查资料 oolpploo` |
| `查询 <昵称>` | `查询 oolpploo` |
| `help` | 显示帮助 |

---

## 架构

```
cookie.txt  →  auth.py  (JWT 5min TTL / 每3分钟自动刷新)
                  ↓
       ┌──────────┼──────────┐
   scapi.py    webstats.py   parser.py
   (基础资料)   (等级+统计)    (HTML解析)
       └──────────┼──────────┘
                  ↓
             query.py  (统一编排 + SQLite缓存)
                  ↓
       ┌──────────┼──────────┐
    REST API    QQ Bot     Web UI
```

### 三大数据源

| 数据源 | 端点 | 返回 | 认证方式 |
|---|---|---|---|
| SCAPI | `scapi.rockstargames.com/profile/getprofile` | 昵称/RID/所在地/好友/帮会/游戏/关联账号 | `Authorization: Bearer` 头 |
| overviewAjax | `socialclub.../games/gtav/career/overviewAjax` | 等级/RP/现金/银行存款 | Cookie + `X-Requested-With` |
| StatsAjax | `socialclub.../games/gtav/statsajax` | 240+ 项深度生涯数据 | Cookie + `X-Requested-With` |

### 项目结构

```
app/
├── main.py              # FastAPI 入口（路由 + 生命周期 + 自动续期）
├── cli.py               # 命令行工具
├── config.py            # 配置（读取 .env）
├── db.py                # SQLite 建表
├── models.py            # 快照 + 凭证 CRUD
├── schemas.py           # Pydantic 数据模型
├── routers/
│   ├── query.py         # REST API 路由
│   └── onebot_router.py # QQ 机器人路由
├── adapters/
│   └── onebot.py        # QQ 消息处理
└── services/
    ├── auth.py          # 认证引擎（token 持久化 + refreshaccess 刷新）
    ├── scapi.py         # SCAPI 客户端（401 自动刷新重试）
    ├── webstats.py      # StatsAjax + overviewAjax 客户端
    ├── parser.py        # HTML 解析（中英文双语适配）
    ├── query.py         # 统一查询编排
    └── collector.py     # [已废弃] 网页抓取方案
static/
└── index.html           # Web 查询面板
tests/
└── test_parser.py       # 离线解析测试（5个用例）
```

---

## 接入 AstrBot QQ 机器人

项目 `plugin/` 目录包含完整的 [AstrBot](https://github.com/Soulter/AstrBot) 插件，已改造为优先使用自建 API。

### 接入方式

1. 将 `plugin/` 整个目录复制到 AstrBot 的 `addons/plugins/` 下
2. 确保本项目的 API 服务已启动（`start.bat`，端口 8686）
3. 启动 AstrBot，插件会自动加载

### 数据流

```
QQ消息 → AstrBot → 插件(_plugin_probe)
                      ├── 自建API(localhost:8686) ← 优先
                      └── 空桑HQSHI(api.hqshi.cn) ← 回退
```

### 命令

| 命令 | 功能 | 数据源 |
|---|---|---|
| `/gta 绑定 <昵称>` | 绑定自己的 GTA 昵称 | — |
| `/gta me` | 查自己（生涯+战眼） | 自建API |
| `/gta 生涯 [昵称]` | 完整生涯数据 | 自建API → 空桑回退 |
| `/gta 战眼 [RID/昵称]` | 查封禁状态 | BattlEye UDP |
| `/gta 更新ck <Cookie>` | 管理员更新凭证 | — |
| `查生涯 <昵称>` | 快捷查生涯 | 自建API → 空桑回退 |
| `查战眼 <RID/昵称>` | 快捷查封禁 | BattlEye UDP |

### 架构说明

```
plugin/
├── main.py               # AstrBot 插件入口（命令路由）
├── socialclub_api.py      # ★ 自建API客户端（调 localhost:8686）
├── gtaonline_helper.py    # R星认证 + 空桑API（保留作回退）
├── batteye_helper.py      # BattlEye UDP 封禁查询
├── _conf_schema.json      # 插件配置
└── metadata.yaml          # 插件元数据
```

---

## 常见问题

### Cookie 注入失败 / 查询报 401

BearerToken 过期了。解决：
1. 浏览器 F5 刷新 socialclub.rockstargames.com
2. **立即** 复制 Cookie 覆盖 `cookie.txt`
3. 重新运行 `start.bat` 或 `python -m app.cli setckf cookie.txt`

### 查询返回 403 / 跳转 error.htm

触发了 R星 WAF（Web 应用防火墙）。等 15-30 分钟后重试，正常使用不会触发。

### 端口被占用

修改 `start.bat` 中的 `--port 8686` 为其他端口，或先杀掉占用进程。

---

## ⚠️ 风险提示

- 本项目直接调用 Rockstar 私有 API，**违反 Rockstar 服务条款**
- 建议使用小号、低频查询，降低封号风险
- `cookie.txt` 和 `socialclub.db` 包含敏感登录凭证，**不要上传到公开仓库**
- 仅供学习研究使用
