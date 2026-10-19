# MiMo 回执交叉核对记录

> 规则：**MiMo 的输出只是"主张"，不是"事实"**。每一条都要回到 `work/pdftext/` 的原文核对。
> 核对方式：主代理自己先读过同一批 PDF（见 `literature_table.json` 的 12 篇深读），再逐条对照。

---

## 第 2 批（`mimo_batch2_result.md`）—— 6 篇：[39] [38] [35] [25] [23] [05]

**结论：整体可信，并抓出主代理表中 1 处真实错误。**

### 核对通过项

| 项 | MiMo 给出 | 回原文核对 | 判定 |
| :-- | :-- | :-- | :-- |
| [38] 标题 | General I/O Relations and Low-Complexity Universal MRC Detection for All OTFS Variants | 与首页标题逐字一致 | ✅ |
| [38] 第一作者 | THARAJ THAJ | 与作者行一致 | ✅ |
| [35] 第一作者/年份/DOI | Franz Lampel / 2022 / 10.3390/e24121704 | 一致 | ✅ |
| [25] 第一作者 | Ruoxi Chong | 一致（Chong, R.） | ✅ |
| [05] 第一作者 | Yifeng Xiong | 首页作者行首名一致 | ✅ |
| [05] 刊物 | IEEE TRANSACTIONS ON INFORMATION THEORY, VOL. 69, NO. 9, SEPTEMBER 2023 | 与页眉逐字一致 | ✅ |
| [25] p3 原句 | "around 20% performance improvement in the 95%-likely SE can be achieved for LM-UEs with the help of the USC." | 原文可检索到 | ✅ |
| [23] p3 原句 | "conventional OFDM systems suffer from a substantial error floor even at typical highway speeds of 50 km/h … up to 1000 km/h" | 原文可检索到 | ✅ |
| [39] p6 原句 | "fc = 60 GHz, B = 50 MHz, N = 2048, ∆f = 24.41 kHz …" | 原文可检索到 | ✅ |

此外，[39] 第 6 页给出的目标参数 `velocities (−60, 30, 120) m/s` 与主代理读到的
「|vk| < 150 m/s 属窄带近似」相互印证，说明该文的场景设定确在百 m/s 量级。

### ❗ 抓出的错误（已修正交付物）

**1. `[39]` 的作者被张冠李戴。**

- 主代理表中原写：`M. F. Keskin, C. Marcus, O. Eriksson, A. Alvarado, H. Wymeersch`
  —— 这其实是 **[04]** 的作者列表，被误复制到了 [39]。
- MiMo 回执给出第一作者 `Musa Furkan Keskin`，触发复核；回原文首页确认真实作者为：
  **Musa Furkan Keskin\*（Chalmers）、Henk Wymeersch\*（Chalmers）、Visa Koivunen†（Aalto）**，
  刊物页码 `ICASSP 2021, 2021-June: 8248-8252`。
- **处置**：`literature_table.json` 的 `[39].authors` 已改为 `M. F. Keskin, H. Wymeersch, V. Koivunen (Chalmers / Aalto)`，
  `venue` 补上页码。

**2. `[23]` 的标题在"Towards / Toward"上不一致。**

- 登记库（OpenAlex manifest）写 `Toward Standardizing OTFS…`；
- **PDF 首页与大写标题两处都写 `Towards Standardizing OTFS…`**（MiMo 也读作 Towards）。
- **处置**：以 PDF 为准，`literature_table.json` 的 `[23].title` 改为 `Towards Standardizing OTFS…`；
  文件名保留登记库形态不动（门禁靠 `file` 字段定位）。

### 一个值得注意的观察（不是错误）

MiMo 在 [23] 与 [25] 两篇上各抄出了**超过 brief 上限 12 条**（各 10–13 条）的句子，
但都控制在"信息量大、含具体数值对比"的范围内，且**没有自行计算或换算**——
说明 brief 里"每篇最多 12 条、优先选信息量最大的"这条规则被理解正确了。

---

## 第 1 批（`mimo_batch1_result.md`）—— 6 篇：[04] [06] [20] [30] [34] [37]

**结论：元数据整体可信；并且正是这批回执让主代理发现了「整篇漏项」`[30]`。**

### 核对通过项

| 项 | MiMo 给出 | 回原文核对 | 判定 |
| :-- | :-- | :-- | :-- |
| [04] 标题/年份/刊物/DOI | Integrated Sensing and Communications with MIMO-OTFS… / 2024 / IEEE TWC / 10.1109/TWC.2024.3370501 | 与首页逐字一致 | ✅ |
| [04] 第一作者 | Musa Furkan Keskin | 与作者行一致 | ✅ |
| [06] 标题/第一作者/年份/DOI | OTFS vs. OFDM in the Presence of Sparsity: A Fair Comparison / Lorenzo Gaudio / 2022 / 10.1109/TWC.2021.3129975 | 一致 | ✅ |
| [37] 标题/第一作者/年份/刊物/DOI | …High Doppler Airborne Communication Networks / Thi My Chinh Chu / 2022 / Mobile Networks and Applications / 10.1007/s11036-022-01928-4 | 一致 | ✅ |
| [34] 年份/刊物/DOI | 均报「未标注」 | 与主代理判断一致：该 PDF 为作者稿，正文未印年份与 DOI | ✅（互为印证） |
| [30] 标题/第一作者/年份/刊物/DOI | Time Domain Channel Estimation and Equalization of CP-OTFS… / SUVRA SEKHAR DAS / 2020 / IEEE Access / 10.1109/ACCESS.2020.3046487 | 与首页逐字一致 | ✅ |
| [30] 任务 B 的定量句 | 含单位原句逐条列出 | 抽样回原文可检索；门禁对 [30] 判 12 条量化声明**全部落地** | ✅ |

### ❗ 由本批回执抓出的问题（已修正交付物）

**1. 整篇漏项：`[30]` 从未进入对比表。**

- 派发给 MiMo 的是 **12 个文件**（batch1 6 + batch2 6），但 `literature_table.json` 只有 11 行，
  缺的正是 `[30]`（Das, IEEE Access 2020, `10.1109/ACCESS.2020.3046487`）。
- 更麻烦的是：`方向调研报告.md` 与 PPT 的分类表**都早已引用 `[30]`**
  （如 PPT slide 8「C 信道估计与低复杂度接收机…（[30] [38]）」、报告 §4 类别 C），
  于是出现「表 11 篇、正文引 12 篇」的自相矛盾。
- 触发点：batch1 回执里出现了 `[30]` 的行，与表内 11 篇对不上，才回头复核。
- **处置**：把 `[30]` 补进 `literature_table.json`（→ 12 篇），相应同步
  `文献阅读对比表格.md` / `.xlsx`、`方向调研报告.md`（深读 11→12、背景 28→27）、
  PPT 计数（11→12、门禁 11/11→12/12；含 slidep 源 `slides/01,13,15.slide`）。
  重跑接地门禁 **12/12 通过**（[30] 单篇贡献 12 条量化声明）。

### 一处口径差异（不是错误）

**`[20]` 的年份：MiMo 读作 2023，主代理表记为 2024。**

- PDF 首页日期：投稿 2023-05-06、修回 2023-08-23、接收 2023-09-02；DOI 亦为 `TST.2023.9010093`。
- 但版权行为 `© The author(s) 2024`，正式出版年取 **2024**。
- **处置**：保留 2024（与版权/出版年一致），此处仅记录两种口径并存，避免将来误改。
