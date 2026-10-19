# 02 · MiMo Desktop 本地 API 逆向笔记

> 小米 MiMo Desktop 是一个 Electron 应用（安装目录 `%LOCALAPPDATA%\Programs\Xiaomi MiMo\`），
> 内部跑一个 opencode 派生引擎，并在**随机端口**上暴露一个**未公开的 localhost HTTP API**，
> 用**每次启动轮换**的 bearer token 保护。本文件记录其完整可用面，便于在 API 变更后重新适配。

## 一、端点发现

每次启动会写一份凭证文件：

```
%APPDATA%\Xiaomi MiMo\desktop-api.json
{"api":1,"port":41166,"token":"<64-hex>","pid":23328}
```

- 端口随机、token 轮换 → **每次都要重新读文件，绝不要硬编码**。
- 服务端要求 `Host` 头精确等于 `127.0.0.1:<port>` 或 `localhost:<port>`。
- 认证头：`Authorization: Bearer <token>`；缺失/错误 → `401 {"code":"unauthorized"}`。
- 存活探测：`GET /health` → `{"ok":true,"api":1,"app":"<ver>","engine":"ready"}`。

> 沙箱环境可能读不到 `%APPDATA%`，因此 `mimo_bridge.py` 里做了 `~\AppData\Roaming\Xiaomi MiMo` 兜底。

## 二、完整路由表（api v1，仅 6 条）

| Method | Path | 用途 |
| :-- | :-- | :-- |
| GET | `/v1/health` | 存活 + 引擎状态 |
| GET | `/v1/sessions?limit=N` | 列会话（limit 默认 200，上限 2000） |
| GET | `/v1/sessions/{sid}/messages?dir=` | 完整消息记录 |
| GET | `/v1/sessions/{sid}/events?dir=` | **SSE 实时事件流** |
| POST | `/v1/sessions/{sid}/turns` | **提交任务** → `202 {"ok":true}` |
| GET | `/v1/sessions/{sid}/files?u=<path>&dir=` | 读取会话产出的文件 |

`{sid}` 必须匹配 `^[A-Za-z0-9_.-]+$`。

### POST /turns 请求体

```json
{
  "message": "必填，非空字符串",
  "model":   "必填，如 mimo-x-pro-preview",
  "dir":     "可选，工作目录",
  "perm":    "可选，权限模式，如 完全访问权限",
  "origin":  "可选",
  "files":   ["可选", "附件路径"],
  "plugins": ["可选", "插件 id"]
}
```

`message` 与 `model` 均必填，缺任一 → `400 {"code":"bad-request"}`。
默认值可从 `%APPDATA%\Xiaomi MiMo\preferences.json` 读取：`model` / `perm` / `fullAccessEnabled`。

### GET /events 的 SSE 事件类型

`meta`、`busy`、`permission`、`ui`、`text-partial`、`idle`、`closed`。

- `ui` 负载带 `{kind: "title"|"text"|"tool"|"usage", ...}`；`ui.kind=="usage"` 是每次模型调用的 token 统计。
- **一轮结束的判据**：至少出现一次 `busy` 之后收到 `idle`。
- 连接保持打开，服务端每 25s 发一次 `: ping`。

## 三、硬限制（务必先知道）

1. **没有创建/删除会话的端点**。只能驱动 UI 里**已存在**的会话；会话一旦在 UI 里建好（并钉住工作目录），之后就能被无头驱动。
2. **提交内容会写进用户真实会话历史**，并消耗其额度。
3. 引擎可能报 `not-logged-in`（503）——需要已登录的小米账号或已配置的 API key。
4. **权限模式决定会不会卡住**：若会话不在「完全访问权限」，遇到工具调用会阻塞等待人工点击，脚本会一直等到 timeout。派发前先确认（见 `preferences.json` 的 `permByConvo`）。

## 四、CLI 用法（`mimo_bridge.py`，纯标准库）

```bash
PY=<python>
$PY mimo_bridge.py health
$PY mimo_bridge.py sessions
$PY mimo_bridge.py messages <sid> --max-chars 500
$PY mimo_bridge.py events   <sid> --timeout 600
$PY mimo_bridge.py run      <sid> "<自包含的详细任务简报>" --timeout 1800
$PY mimo_bridge.py file     <sid> <relative/path> --out local_copy
```

`run` = 提交 + 一直订阅到 idle，即「一次调用完成整个交接」。

## 五、API 变更时如何重新逆向

路由定义在 `resources/app.asar`（尽管扩展名如此，其实是纯文本 JS）：

```bash
grep -a -b -o "invalid or missing token" resources/app.asar   # 定位服务端代码
```

路由匹配函数就在那张错误码表之后；route kind 由一个小的路径解析器产出，
它把 `v1/health`、`v1/sessions`、`v1/sessions/{sid}/{messages|events|turns|files}` 列入白名单。
turns 的 body schema 在 `sendTurn(...)` 附近的 `case"turns"` 分支里解析。

探针脚本留存于 `../skills/mimo-desktop-bridge/examples/`：
`probe_mimo_asar.py`、`extract_route_table.py`、`_mimo_dump.py`、`_recon.txt`。

## 七、其他发现

- MiMo Desktop 的 **MCP 配置**位于 `C:\Users\24560\.config\mimocode\mimocode.jsonc` 顶层 `mcp` 段，
  可直接用文件工具编辑（本地 stdio 用 `{"type":"local","command":[...],"environment":{...},"enabled":true}`，
  远程用 `{"type":"remote","url":"...","headers":{...},"enabled":true}`）；改完需**重启引擎或新开对话**才生效。
- MiMo Desktop 的 skill 根目录为 `~/.claude/skills/<name>/SKILL.md`。
