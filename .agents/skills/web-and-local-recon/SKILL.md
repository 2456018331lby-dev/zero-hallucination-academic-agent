---
name: web-and-local-recon
description: >-
  多源信息采集与本地环境诊断强化工作流。当需要同时读取复杂网络内容（含反爬/风控的B站、知乎、GitHub、动态技术博客）、
  全网信息检索、探测 Windows 本地开发环境（版本、二进制、配置文件、环境变量）并进行方案对比与自动修复时使用。
  核心能力：双阶网络采集（轻量读取优先 + Chrome DevTools 动态穿透）、智能正文提纯（避免导航噪点）、
  Windows PowerShell 严格防错规范、首轮多路并发、长文本分页分块，以及环境差异对比与自动落地闭环。
metadata:
  version: "2.0.0"
  role: recon-and-environment-diagnostician
  triggers: 解析帖子, 查看仓库并对比本地, 诊断配置, 检查环境, web-recon, local-recon
---

# 多源信息采集与本地环境诊断 (Web & Local Recon 2.0)

本规范用于指导 Agent 在面对“复杂网页解析 + 代码仓库调研 + 本地环境排查 + 落地改造”混合任务时的最高效、低消耗、防踩坑作业标准。

---

## 核心工作流：五步闭环

### 第 1 步：首轮并发采集（Zero-Dependency Parallelism）
将所有**互相没有输入输出依赖**的工具在第一轮中**并发发起**，严禁串行轮询等待：
- 并发任务 A：网页/技术文章采集
- 并发任务 B：GitHub 仓库/README 解析
- 并发任务 C：本地软件版本、路径与配置文件初步探测

---

### 第 2 步：双阶梯网络采集协议（Dual-tier Web Pipeline）

不要盲目一上来就启动重量级无头浏览器，也不要因为单一请求被拦截就束手无策：

#### Tier 1：轻量静态抓取（低延迟、零资源占用）
- 优先发起轻量 HTTP 请求（如 `read_url_content` 或对应文本接口）。
- 若返回包含正文且状态正常，直接消费，节约 Token 与系统内存。

#### Tier 2：Chrome DevTools 动态穿透（高阶抗反爬与动态渲染）
当 Tier 1 触发风控（如 B 站 `-352`、验证码拦截、Cloudflare 挑战）、页面高度依赖 JS 动态渲染或需要真实会话态时，升级至 Chrome DevTools 流程：
1. **导航与等待**：使用 `navigate_page` 载入目标 URL。
2. **智能 DOM 提纯（关键优化）**：
   - **严禁**直接抓取 `document.body.innerText`（会把全站导航、页脚、推广弹窗等数千 Token 垃圾信息混入）。
   - **必须**使用精确的选择器提取正文容器，并在 JS 端清洗噪点：
     ```javascript
     () => {
       const targets = document.querySelectorAll('article, main, .opus-module-content, .post-content, .markdown-body, #article-root');
       let el = targets.length > 0 ? targets[0] : document.body;
       // 移除脚本、样式与导航
       const clone = el.cloneNode(true);
       clone.querySelectorAll('nav, header, footer, script, style, .sidebar, .banner, .ad').forEach(n => n.remove());
       return clone.innerText.trim();
     }
     ```
3. **标签页生命周期回收**：
   - 提取完毕后，**必须及时调用 `close_page` 关闭标签页**，杜绝 Chromium 页面常驻占用内存与句柄。
4. **长文本分块处理（Pagination / Chunking）**：
   - 单次提取文本若超过 6000 字符，应分块或针对核心结构化章节（如二级标题）进行切片提取，防止挤爆思考上下文。

---

### 第 3 步：Windows PowerShell 严格防错规范（避坑核心）

在 Windows 终端执行检测时，环境默认为 PowerShell，必须遵守以下 5 大强制准则：

| 场景 | 严禁写法（Linux 思维陷阱） | 强制规范写法（PowerShell 兼容） | 致命原因说明 |
|---|---|---|---|
| **路径检测** | `where bash` | `where.exe bash` | `where` 是 `Where-Object` 别名，不带 `.exe` 会静默失败或语法报错。 |
| **文件罗列** | `ls -la` | `Get-ChildItem -Force` | PowerShell 的 `ls` 不支持 Linux 参数 `-la`。 |
| **文件读取** | `cat file` | `Get-Content "file" -Raw -Encoding utf8` | 默认编码会导致中文乱码，`-Raw` 保证作为单字符串读取。 |
| **安全探测** | 直接读取不存在的文件 | `if (Test-Path "路径") { Get-Content "路径" -Raw -Encoding utf8 } else { Write-Output "不存在" }` | 避免因文件不存在导致进程抛出非零退出码。 |
| **环境探测** | `echo $VAR` | `[Environment]::GetEnvironmentVariable("VAR", "User")` | 保证能跨进程读取到注册表级别的用户环境变量。 |

---

### 第 4 步：后台长任务稳健管控
当命令可能执行较长时间（如 npm 安装、仓库 clone、递归扫描）时：
1. 观察工具返回的 `TaskId`。
2. 严禁死循环高频轮询 `status`，合理使用系统的异步通知机制或有条件的轻量调度。
3. 发现挂死或非预期 TUI 交互时，果断执行 `kill` 终止并切换方案。

---

### 第 5 步：差距诊断与闭环落地
采集分析完成后，产出物必须包含：
1. **真实能力断层对照表**：官方/先进推荐方案 vs 本机现状。
2. **风险/冗余项明细**：点出违背设计初衷的性能杀手（如无效 MCP、冲突扩展、错误 PATH 顺序）。
3. **可执行的行动方案**：给出明确的落地步骤（备份、清理、依赖补齐、配置校验）。

---

> **四副本同步铁律**：本技能为多平台工作流资产。平台开发者在 `.agents/skills/` 对本技能源码或文档做任何改动后，必须运行 `python .agents/skills/sync_skills.py` 保持 Gemini/Codex/Claude 三大全局镜像区完全一致。
