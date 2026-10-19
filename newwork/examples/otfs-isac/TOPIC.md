# 选题说明 · 高机动低空场景下的时延-多普勒域（OTFS）通感一体化

> 这是 `newwork` 工作流的**第二个实例**（第一个是 `examples/bupt-isac`）。
> 目的有两个：① 给用户的论文提供一条相邻但不同的方向；② 用新数据检验流水线能否复现。

## 一、为什么选这个题（与既有 ISAC 工作的关系）

第一个实例（低空经济 ISAC 综述）得出的结论是：

- 低空 ISAC 的全部工作都在回答「如何把通信与感知的相互干扰转化为相互支撑」；
- 折中落在**波形层 / 空间层 / 系统层**三个层面；
- 两个根本缺口：**感知指标不可比**、**全链路无实测**。

而在**波形层**，既有池子里的方法（[8] 免专用资源 MIMO-OFDM、[6] UW-OCDM）都是**在 OFDM 家族内部做改良**。
它们共同的隐含前提是：信道在符号周期内近似不变。**低空场景恰恰违反这个前提**——无人机高机动带来大
多普勒与快时变信道，OFDM 会出现严重的子载波间干扰（ICI），波形改良的收益被信道时变吃掉。

**OTFS（Orthogonal Time Frequency Space）** 把调制搬到**时延-多普勒域**，恰好是这组场景的"原生适配器"：
时变信道在该域变得稀疏且近似时不变。所以这不是"再优化一次 OFDM"，而是**换一个维度描述信道**。

因此本题与既有工作是**同一主线的相邻分支**：
沿用「通信与感知如何互相支撑」的问题意识，但把战场从 OFDM 家族换到 OTFS 家族。

## 二、对研一学生为什么可做

OTFS-ISAC 有三条清晰、门槛递增的线，前两条适合研一起步：

| 线 | 内容 | 起步难度 |
| :-- | :-- | :-- |
| ① 感知参数估计 | 在时延-多普勒域做时延/多普勒/角度估计，替代 OFDM 的 ICI 受限方案 | 低（有成熟 OTFS 信道估计可借） |
| ② 波形/导频/资源设计 | 为兼顾感知精度与通信速率设计导频图样、叠加或复用方案 | 中 |
| ③ 与低空协同系统耦合 | 多机协同、轨迹优化、与低空监管/认证系统结合 | 高（需系统级仿真） |

## 三、本实例要回答的问题

1. OTFS-ISAC 相对 OFDM-ISAC，**在什么条件下真的赢**？赢多少？（要数字，要可回溯）
2. 感知与通信的折中在时延-多普勒域里**被如何重新表述**？
3. 这一支方向**还没解决什么**——尤其是第一个实例点出的「指标不可比」在这里是否同样成立？

## 四、检索口径（可复现）

OpenAlex，`is_oa:true`，2021 年起；第二轮统一加 `title_and_abstract.search:OTFS OR delay-Doppler OR AFDM`
过滤器强制切题（第一轮纯关键词检索会拖进卫星 / THz / 引力波等离题命中）。检索词：

```
OTFS integrated sensing and communication
orthogonal time frequency space radar sensing
delay-Doppler waveform joint radar communication
AFDM sensing integrated sensing communication
OTFS channel estimation OR waveform OR detection
```

采集脚本：`newwork/scripts/litpool_fetch.py`；来源与许可逐篇记录在 `input/manifest.json`。
最终池：**39 篇**（`[01]`–`[39]`）。

> ⚠️ **采集环境差异（必须如实记录）**
>
> 1. 本机 `arxiv.org` / `export.arxiv.org` / `dl.acm.org` / `sciencedirect` 不可达（SSL EOF / 502），
>    故本池**不含 arXiv 预印本**——而 OTFS-ISAC 恰好是 arXiv 上的活跃方向，这是最大的取样偏差。
>    补偿办法：改由 IEEE Xplore（OA 刊）、Springer / SpringerOpen、TechRxiv、以及 Essex /
>    Chalmers / LU / QMUL / Polimi 等机构库补足。
> 2. **HAL 全文本下载已不可用**：`hal.science/<id>/document` 现在挂在 **Anubis 工作量证明**
>    机器人门（返回 `Making sure you're not a bot!` HTML），脚本无法通过。HAL 的**检索 API**
>    （`api.archives-ouvertes.fr`）仍可正常调用，因此 HAL 仅用于**发现**、不再作为下载源。
>    详见 `input/manifest.json` 中 `reason = "download failed: not a PDF (got b'<!doctype html>…')"` 的 45 条记录。
> 3. 下载走 Python `urlopen` 时必须用 **系统证书库**上下文（`load_default_certs()`），
>    否则 `hal.science` / `orbilu.uni.lu` 等会报 `CERTIFICATE_VERIFY_FAILED`；
>    `litpool_fetch.py::_ssl_ctx()` 已固化该处理。
>
> 这既是限制也是好处：它顺带检验了流水线在**非 arXiv、非单栏、多机构库**版式上的表现。
