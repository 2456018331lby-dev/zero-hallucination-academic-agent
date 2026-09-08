# GB/T 7714-2015 参考文献 BibTeX 著录规范 (Standard Bibliography Specification)

本规范为《信息与文献 参考文献著录规则》（GB/T 7714-2015）在 LaTeX/BibTeX 下的标准实现，配合 `biblatex-gb7714-2015` 或 `gbt7714.bst` 使用。

---

## 1. 核心文献类型代码表

| 文献类型 | 代码 | 对应 BibTeX Entry 类型 | 必备字段 |
| :--- | :---: | :--- | :--- |
| **期刊文章 (Journal)** | `[J]` | `@article` | author, title, journal, year, volume, number, pages |
| **会议论文 (Conference)** | `[C]` | `@inproceedings` | author, title, booktitle, year, pages, address, publisher |
| **学位论文 (Dissertation)**| `[D]` | `@phdthesis` / `@mastersthesis` | author, title, school, year, address |
| **科技报告 (Report)** | `[R]` | `@techreport` | author, title, institution, year, number |
| **专著图书 (Book)** | `[M]` | `@book` | author, title, publisher, year, address |
| **电子资源/预印本 (Online)**| `[EB/OL]` | `@online` / `@misc` | author, title, year, url, urldate, eprint |

---

## 2. 标准 BibTeX 条目范例

```bibtex
% [C] 国际顶级会议论文 (如 CVPR, NeurIPS, ICML)
@inproceedings{peebles2023scalable,
  author    = {Peebles, William and Xie, Saining},
  title     = {Scalable Diffusion Models with Transformers},
  booktitle = {Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)},
  year      = {2023},
  pages     = {4195--4205},
  address   = {Paris, France},
  publisher = {IEEE}
}

% [J] 国际重要期刊论文 (如 IEEE TPAMI)
@article{he2022masked,
  author    = {He, Kaiming and Chen, Xinlei and Xie, Saining and Li, Yanghao and Doll{\'a}r, Piotr and Girshick, Ross},
  title     = {Masked Autoencoders Are Scalable Vision Learners},
  journal   = {IEEE Transactions on Pattern Analysis and Machine Intelligence},
  year      = {2024},
  volume    = {46},
  number    = {5},
  pages     = {3214--3227},
  publisher = {IEEE}
}

% [EB/OL] arXiv 预印本（对齐 GB/T 7714 电子公告类型）
@online{vaswani2017attention,
  author    = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N and Kaiser, {\L}ukasz and Polosukhin, Illia},
  title     = {Attention Is All You Need},
  year      = {2017},
  eprint    = {1706.03762},
  eprinttype= {arXiv},
  url       = {https://arxiv.org/abs/1706.03762},
  urldate   = {2026-09-06}
}

% [D] 硕博学位论文
@phdthesis{zhang2022deep,
  author    = {张三},
  title     = {面向高维非线性系统的自适应鲁棒控制方法研究},
  school    = {清华大学},
  year      = {2022},
  address   = {北京}
}
```

---

## 3. LaTeX 编译支持配置

在主文档导言区推荐使用以下配置加载标准国标样式：

```latex
% 使用 biblatex 宏包加载国标
\usepackage[backend=biber,style=gb7714-2015,gbalign=left]{biblatex}
\addbibresource{references.bib}

% 文中引用示例：
% 顺序编码制：\cite{peebles2023scalable} -> [1]
% 著者-出版年制：\textcite{peebles2023scalable} -> Peebles et al. (2023)
```
