# -*- coding: utf-8 -*-
"""Insert the accidentally-dropped deep-read row [30] into literature_table.json.

Why: MiMo was handed 12 files (batch1 6 + batch2 6); the table held only 11, and
the missing one was exactly [30] (Das, IEEE Access 2020) -- which the report and
PPT nonetheless cite as a category-C representative ("[30] [38]"). The cross-check
with MiMo's batch1回执 surfaced the omission, so we add it back -> 12 deep-read.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(HERE, "..", "deliverables", "literature_table.json")

ROW = {
    "id": "[30]",
    "title": "Time Domain Channel Estimation and Equalization of CP-OTFS Under Multiple Fractional Dopplers and Residual Synchronization Errors",
    "authors": "S. S. Das, V. Rangamgari, S. Tiwari, S. C. Mondal (IIT Kharagpur / Wipro)",
    "year": 2020,
    "venue": "IEEE Access, 9:10561-10576, DOI 10.1109/ACCESS.2020.3046487",
    "file": "[30]_Das_Time_Domain_Channel_Estimation_and_Equalizatio_2020.txt",
    "problem": "已有 OTFS 信道估计与均衡工作大多假设理想同步与理想信道估计；一旦存在残余帧定时偏移(frame timing offset, FTO)、载波频偏(CFO)与分数多普勒，DD 域信道矩阵结构随之改变，估计精度与复杂度都不再受控。",
    "method": "先建立含残余 FTO/CFO 的 CP-OTFS 完整信号模型并推导时域等效信道矩阵；用 DD 域嵌入式导频 + 能量门限 + 样条插值在时域估计信道，进而给出低复杂度块对角 LMMSE 均衡与 SIC 接收机（面向 LDPC 编码 CP-OTFS），并给出 OTFS 与 OFDM 的统一信号处理流程。",
    "innovation": "证明时域等效信道矩阵的结构不随多普勒取值改变、且比 DD 域矩阵更稀疏——分数多普勒下 H_DD 的非零元可达 N²N_e，而 H 恒为约 P 倍更稀疏；由此把估计与均衡放到时域，既免疫残余同步误差又把复杂度降低一个数量级；并给出 OTFS/OFDM 统一描述以支撑可重构空口。",
    "setup": "仿真：Δf=15 kHz、fc=4 GHz、N=128、M=512、速度 500 km/h；残余频偏 δfc=2.33 kHz（约 15% 子载波间隔）、最大多普勒 2.76 kHz；LDPC 编码；对比理想 MMSE、含/不含同步误差、以及 CP-OTFS 与 RCP-OTFS。",
    "results": "所提 LMMSE 接收机复杂度为 MN·log(MN)，所需复乘约为直接实现的 1/10⁷（原文：around 10⁷x lower CMs）；SIC 使性能几乎逼近理想 MMSE 均衡；相同 BLER 下 OFDM 较 OTFS 差约 3–7 dB；给出 OTFS 对残余同步误差的容忍度（原文：tolerance of OTFS to such residual synchronization errors）。",
    "pros": "首次把残余同步误差并入 OTFS 信道模型；用时域更高稀疏度把复杂度降一个数量级；给出 OTFS/OFDM 统一框架，工程落地性强。",
    "cons": "纯通信，不含任何感知指标；以蒙特卡洛仿真为主、无实测；假设残余同步误差未超过 CP 长度。",
    "relation": "信道估计与低复杂度接收机线（与 [38] 同族）——为 OTFS-ISAC 在高机动与残余同步误差下的可靠接收提供底层保障，但不涉及感知。",
    "recommend": "可选",
    "why": "OTFS-ISAC 的接收机前置能力证据：说明高机动/残余同步误差下 OTFS 仍能低复杂度可靠解调，支撑「波形可用性」这一前提。",
}


def main() -> None:
    with open(JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    ids = [p["id"] for p in data["papers"]]
    if "[30]" in ids:
        print("already present, nothing to do")
        return
    idx = ids.index("[20]") + 1          # keep batch1 ordering: ...[20] [30] then batch2
    data["papers"].insert(idx, ROW)

    # meta counts: deep-read 11 -> 12 ; background 28 -> 27
    meta = data["meta"]
    meta["source_note"] = meta["source_note"].replace("深读 11 篇", "深读 12 篇")
    notes = meta.get("notes", [])
    for i, n in enumerate(notes):
        notes[i] = n.replace("深读名单为 11 篇，其余 28 篇作为背景",
                             "深读名单为 12 篇，其余 27 篇作为背景")
    meta["notes"] = notes

    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("inserted [30]; total papers =", len(data["papers"]))
    print("order:", " ".join(p["id"] for p in data["papers"]))


if __name__ == "__main__":
    main()
