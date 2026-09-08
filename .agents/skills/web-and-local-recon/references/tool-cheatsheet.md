# 工具链参数速查表 (Tool Cheatsheet)

本速查表整理了在执行多源网络检索与本地诊断时，Agent 常用工具的最佳调用参数与避坑示例。

---

## 1. 网络采集工具

### `read_url_content`（快速 HTTP 静态采集）
- **适用场景**：静态页面、API 返回、无需复杂 JS 执行的文档。
- **调用示例**：
  ```json
  { "Url": "https://raw.githubusercontent.com/owner/repo/master/README.md" }
  ```
- **注意**：遇 403、验证码或动态 SPA 页面时，立即降级至 Chrome DevTools。

### `chrome-devtools-mcp`（动态无头浏览器穿透）
- **核心工具组合**：
  - `list_pages`：查看当前已打开的标签页。
  - `new_page`：开启新标签页。
  - `navigate_page`：跳转 URL，参数 `{ "pageId": 1, "type": "url", "url": "https://..." }`。
  - `evaluate_script`：在页面内注入执行 JS。
  - `close_page`：必须调用的收尾工具，参数 `{ "pageId": 1 }`。
- **提纯正文标准代码模板**：
  ```javascript
  () => {
    // 自动寻找可能的内容主体选择器
    const selectors = ['article', 'main', '.opus-module-content', '.post-content', '.markdown-body'];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.innerText.trim().length > 100) {
        return el.innerText.trim();
      }
    }
    return document.body.innerText;
  }
  ```

---

## 2. 本地命令与环境探测（Windows PowerShell 规范）

### 查找二进制路径
```powershell
where.exe <command>
```
*避坑*：绝对不要写 `where <command>`，否则在 PowerShell 中会被作为 `Where-Object` 报错。

### 检查文件是否存在并安全读取
```powershell
if (Test-Path "<path>") { Get-Content "<path>" -Raw -Encoding utf8 } else { Write-Output "NOT_FOUND" }
```
*避坑*：
- 必须带 `-Raw`，否则返回逐行对象数组，处理大文本非常慢。
- 必须带 `-Encoding utf8`，否则中文配置文件读取出来全是乱码。

### 检查环境变量（跨进程持久化探测）
```powershell
[Environment]::GetEnvironmentVariable("<VAR_NAME>", "User")
```
*避坑*：`$env:VAR` 仅反映当前进程环境，使用 `[Environment]` 可直接读取 Windows 用户级注册表配置。

---

## 3. 任务与后台管控

### `manage_task`
- `list`：查看后台正在运行的异步长任务。
- `status`：查看特定任务的实时日志输出。
- `kill`：终止非预期卡死或进入交互式死循环的任务。
