# 05 · PPT 动画（本地 editor SDK + timing XML 后处理）

给已经做好的 `.pptx` 加"入场动画"，让观感更好。这一页记录**踩过的坑**和**可复现流程**，
因为本地 editor SDK 的动画 API 有一处硬限制，必须绕过。

---

## 1. 为什么需要"两步走"

本地 `tencent-local-office-edit` skill 通过 `editor_sdk`（MCP，端口 39099–39108）操作
本机磁盘上的 office 文件。它的动画相关工具：

| 工具 | 参数 |
| :-- | :-- |
| `slide_add_anim` | `file_id, page_index, shape_id, anim_type, anim_subtype, index` |
| `slide_set_anim_properties` | 同上 + 改类型 |
| `slide_set_anim_trigger` | `file_id, page_index, shape_id, index, trigger` |
| `slide_remove_anim` | `file_id, page_index, shape_id, index` |
| `slide_move_anim` | 调整顺序 |

**硬限制**：`slide_add_anim` 只接受「类型」，没有 `startType` / `duration` 参数。
它写出来的每个节点都固定是：

```xml
<p:cond delay="indefinite"/>            <!-- = 等待点击 -->
... nodeType="clickEffect"              <!-- 点击触发 -->
<p:cTn dur="1000">                      <!-- 淡入固定 1000 ms -->
```

后果：**一页有几个动画就要点几次鼠标**，而且 1000 ms 的淡入偏拖沓。
公开 API 无法表达"上一动画之后 / 与上一动画同时"，也无法改时长。

所以流程拆成两步：

1. **SDK 负责"加"** —— 用 `slide_add_anim` 决定"哪些形状、什么效果"。
2. **脚本负责"时序"** —— 直接改写保存后的 `ppt/slides/slideN.xml` 里的 `<p:timing>`，
   把第 2..N 个效果从 `clickEffect` 改成 `afterEffect` + 数值延迟，并收短时长。

这样最终效果是：**一页一次点击，页面自己铺开**。

---

## 2. 关键 XML 事实（别用正则猜）

- `<p:cTn>` **没有 `id` 属性**，所以千万不要写 `id="\d+"` 的正则去锚定，会全部匹配失败、
  得出"文件里没有动画"的错误结论。
- 一个"点击组"的固定开头是：

  ```xml
  <p:par><p:cTn fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>
  ```

  数这段出现的次数 = 该页要点几次。把它替换成 `delay="300"`、并把组内第一个
  `nodeType="clickEffect"` 改成 `afterEffect`，就变成"上一动画之后 300 ms"。
- 效果节点靠 `presetID=` + `nodeType=` 识别。常用：

  | presetID | 效果 | 由哪个 anim_type 产生 |
  | :-- | :-- | :-- |
  | 10 | 淡入 | `anim_type=1` (FADE_IN) |
  | 53 | 缩放出现 | `anim_type=18` (ENTER_SCALE) |

- 动画目标写成 `<p:spTgt spid="N"/>`，这里的 `N` 是形状的内部数字 id，
  **不是** SDK `slide_get_page_info` 返回的那种 `00002e` 字符串（那是十六进制形态）。
  所以**不要手工拼 spid**，交给 SDK 写。
- 每个效果通常有 2 个 `spTgt`（`<p:set>` 里一个、`<p:animEffect>` 里一个），
  所以按下标取 targets 会错位 —— 只看数量，不要按位置配。

---

## 3. 可复现流程

```bash
PY=C:/Users/24560/.workbuddy/binaries/python/versions/3.13.12/python.exe
EDS=~/.workbuddy/plugins/cache/workbuddy-builtin/skill-tencent-local-office-edit/*/edsdk.py

# ① 备份
cp deck.pptx work/backup/deck.pre-anim.pptx

# ② 打开（返回的 file_id 是"路径串"形态，带重复斜杠，原样使用即可）
$PY $EDS call open_file --json '{"file_path":"C:\\...\\deck.pptx","open_with_existing":true}'

# ③ 读每页 shape：挑动画目标（巨型数字 / KPI 数字 / 标题）
$PY $EDS call slide_get_page_info --json '{"file_id":"<file_id>","page_index":2}'

# ④ 加动画（脚本里硬编码 页面→shape_id 计划，见 examples/bupt-isac/work/apply_animations.py）
$PY apply_animations.py --file-id "<file_id>" --dry-run   # 先看
$PY apply_animations.py --file-id "<file_id>"             # 再跑，只跑一次

# ⑤ 核对计数
$PY inspect_anim.py deck.pptx | grep -E "effects=|page"

# ⑥ 保存
$PY $EDS call save_file --json '{"file_id":"<file_id>"}'

# ⑦ 时序后处理（把 click 变 cascade + 收短淡入）
$PY retime_animations.py deck.pptx --check
$PY retime_animations.py deck.pptx --stagger 300 --fade-ms 600
```

---

## 4. 三个真实踩过的坑

| 坑 | 现象 | 原因 / 对策 |
| :-- | :-- | :-- |
| **重复执行导致动画翻倍** | 每页序列精确重复一遍 | 脚本跑了两遍。→ `apply_animations.py` 内置幂等守卫：目标页已有动画则**拒绝执行**，要绕过必须显式 `--force` |
| **"动画不见了"** | zip 里查不到 timing | 正则锚定了不存在的 `id="\d+"`。→ 见 §2，改用 `presetID`/`nodeType` 锚定 |
| **`presentation is not open`** | `save_file` 后再操作报 `-32603` | 保存可能释放实例。→ `get_pool_status` 找活实例；或 `open_file open_with_existing=true` 重开，再用返回的路径串 `file_id` |

另外：`editor_sdk` 的实例池里会残留指向**已删除路径**的陈实例（本项目把所有产物搬到
`newwork/` 之后就出现过），报错时先 `get_pool_status` 看清是哪个实例。

---

## 5. 动画设计约定（学术汇报调性）

原则：**只在视觉锚点上动，密集正文页保持静态**，避免"每页都在动"的廉价感。

| 页面角色 | 效果 | 对象 |
| :-- | :-- | :-- |
| 封面 | 淡入 ×3 | 主标题 / 副标题 / 落款 |
| 篇章扉页（01/02/03） | **缩放出现** + 淡入 ×2 | 巨型数字 / 标题 / 三行说明 |
| 代表文献页（KPI 页） | **缩放出现** ×2 | 两个大号 KPI 数字 |
| 对比总结页 | 淡入 ×2 | 左右栏标题 |
| 总结页 | 淡入 ×3 | 标题 / 链式说明 / 金句 |
| 目录页、方向定位、三重矛盾、四阶段、五类方法、挑战页 | 不动 | — |

时序：每页第 1 个效果点击触发，其余 `afterEffect` 级联，间隔 300 ms；
淡入 600 ms（SDK 默认 1000 ms 偏慢），缩放自带 500 ms。

---

## 6. 回滚

```bash
cp deliverables/<deck>/<deck>.pptx.bak deliverables/<deck>/<deck>.pptx   # 回滚时序
cp work/backup/<deck>.pre-anim.pptx deliverables/<deck>/<deck>.pptx      # 回滚到"无动画"版本
```
