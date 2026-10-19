---
name: windows-computer-use
description: Windows 桌面级物理操控与应用自动化专家（真实键鼠模拟）。用于通过实体鼠标定位与点击、物理键盘击键打字、窗口句柄查找、前台焦点置顶与屏幕高清捕获，像真实人类一样接管与操作 Windows 操作系统上的任意桌面应用（包括 Electron、Win32、UWP、WPF、Qt 等）。内置虚拟桌面沙盒穿透（exebox 穿透到 WinSta0\Default）、Windows ASFW 焦点锁解锁、高分屏（125%/150%/200%）DPI 物理像素对齐与 SendInput 硬件级输入机制。当用户要求操控桌面应用、点击输入框、启动软件交互、模拟真实键鼠或测试电脑操作时触发。
---

# Windows Computer Use (Windows 桌面级物理键鼠操控)

本技能提供对 Windows 桌面操作系统与原生应用程序的**真正物理级人类键鼠接管能力**。它不依赖目标软件是否开放网络端口或 HTTP API，而是像真实坐在电脑前的人类一样，通过**看屏幕、找窗口、移鼠标、点控件、敲键盘、验结果**完成全流程自动化。

---

## 一、 核心执行循环：观察 → 行动 → 校验 (Observe-Act-Verify)

在执行任何物理桌面操控时，必须严格执行三步闭环，**严禁盲打盲点**：

```
1. 观察 (Observe)  ->  列出/锁定目标窗口，截图获取当前控件物理坐标与状态
2. 行动 (Act)      ->  唤醒置顶窗口，物理平移鼠标点击控件，键入文本或发送按键
3. 校验 (Verify)   ->  再次截图回显，确认输入光标闪烁/文字已落入/界面生成完成
```

---

## 二、 自动化标准工具：`desktop_operator.py`

在执行桌面操作时，直接调用本技能内置的专用标准化工具：
`python <SKILL_DIR>/scripts/desktop_operator.py <command> [options]`
（或者绝对路径：`python "C:\Users\24560\.gemini\config\skills\windows-computer-use\scripts\desktop_operator.py" ...`）

### 常用命令参考

| 子命令 | 功能说明 | 核心参数与示例 |
|---|---|---|
| `list-windows` | 列出物理主桌面上所有可见运行窗口 | `python desktop_operator.py list-windows [--filter "关键词"]` |
| `focus` | 唤醒并强制夺取窗口前台焦点（解除锁屏/最小化） | `python desktop_operator.py focus --target "Xiaomi MiMo"` |
| `capture-window` | 高清抓取目标窗口的物理渲染位图（自动还原最小化） | `python desktop_operator.py capture-window --target "Xiaomi MiMo" --output "result.png"` |
| `click-client` | 在窗口客户区相对坐标 `(x, y)` 处点击（自动转换物理屏幕坐标） | `python desktop_operator.py click-client --target "Xiaomi MiMo" --x 850 --y 680` |
| `click` | 在物理屏幕绝对坐标 `(x, y)` 处点击 | `python desktop_operator.py click --x 1106 --y 703 [--button left\|right] [--clicks 1\|2]` |
| `type` | 向当前获得焦点的控件敲入文本 | `python desktop_operator.py type --text "你好世界" [--enter]` |
| `key` | 发送组合快捷键或控制键 | `python desktop_operator.py key --chord "ctrl+v"` / `"enter"` / `"esc"` |
| `dpi-info` | 打印当前主屏幕物理分辨率与 DPI 缩放信息 | `python desktop_operator.py dpi-info` |

---

## 三、 Windows 底层四大铁律（避坑指南）

如果在编写自定义扩展脚本或执行复杂操作，必须遵守以下经过实战检验的系统级铁律：

### 1. 虚拟桌面沙盒穿透铁律 (Desktop Sandbox Escape)
* **机制**：Antigravity 终端默认在专有后台虚拟桌面（`exebox-xxxx`）中执行命令。普通的 `SetCursorPos` 或按键事件若在此桌面发出，鼠标只会打在隐形空气里，用户物理屏幕毫无反应。
* **规则**：所有 Win32 调用前，必须显式调用：
  ```python
  hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
  if hDesk:
      user32.SetThreadDesktop(hDesk)
  ```
  枚举窗口必须使用 `EnumDesktopWindows(hDesk, ...)` 而非 `EnumWindows`。

### 2. 焦点保护锁绕过铁律 (ASFW Unlock)
* **机制**：如果用户当前正处于其他软件（如 Word、浏览器），Windows 的 `AllowSetForegroundWindow` 机制会拦截后台进程的置顶请求，直接调用 `SetForegroundWindow` 会静默失败。
* **规则**：必须使用 Alt 键菜单态穿透法：
  ```python
  user32.keybd_event(0x12, 0, 0, 0)   # Alt 按下，激活 Windows 菜单态解除焦点锁
  user32.ShowWindow(hwnd, 5)          # SW_SHOW
  user32.SetForegroundWindow(hwnd)    # 成功置顶
  user32.keybd_event(0x12, 0, 2, 0)   # Alt 抬起
  ```

### 3. 高分屏 DPI 物理像素对齐铁律 (Per-Monitor V2)
* **机制**：主流 Windows 显示器常开启 125%、150% 或 200% 缩放。若进程不声明 DPI 感知，Win32 API 会返回虚拟 96-DPI 尺寸（如 2560 变 1707），导致鼠标点击严重偏位。
* **规则**：在脚本初始化第一行执行：
  ```python
  user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
  ```
  换算窗口内相对控件坐标到屏幕物理坐标时，使用 `ClientToScreen` 换算。

### 4. 双轨输入与输入法兼容铁律 (SendInput & IME)
* **机制**：系统输入法可能处于中文拼音状态，直接发送英文字符可能被拼音拦截或丢失。
* **规则**：
  - **长文本、中文输入、代码段**：使用系统剪贴板注入 + `SendInput` 触发 `Ctrl+V`，100% 避开输入法干扰且速度极快；
  - **单键控制（Enter、Tab、Esc、方向键）**：使用 `SendInput` 硬件级按键，不要用废弃的 `keybd_event`。

---

## 四、 标准实战范式：操控桌面 AI/IM 软件发送消息并校验

以操控小米 MiMo、微信、钉钉等软件为例的标准动作链：

```bash
# 1. 查找窗口 HWND 并唤醒置顶
python <SKILL_DIR>/scripts/desktop_operator.py focus --target "Xiaomi MiMo"

# 2. 截取当前界面，获取输入框位置
python <SKILL_DIR>/scripts/desktop_operator.py capture-window --target "Xiaomi MiMo" --output "<ARTIFACTS_DIR>/step1_before.png"

# 3. 物理点击输入框（以客户区坐标或物理坐标）
python <SKILL_DIR>/scripts/desktop_operator.py click-client --target "Xiaomi MiMo" --x 850 --y 680

# 4. 键入文本并按回车提交
python <SKILL_DIR>/scripts/desktop_operator.py type --text "你好，这是一条自动化测试消息。" --enter

# 5. 等待 3-5 秒，截取最终成果验证
python <SKILL_DIR>/scripts/desktop_operator.py capture-window --target "Xiaomi MiMo" --output "<ARTIFACTS_DIR>/step2_after.png"
```
通过上述标准步骤，任何 Windows 原生窗口均可实现稳定、零失误的人工级物理交互。
