# P0 数据审计与拆分卡

日期：2026-10-28  
输入：`data/raw/mp6b00471_si_001.xlsx`（MD5 `e1dee9497f1fda95312acfd4cb61bec5`）  
脚本：`scripts/00_audit.py`、`scripts/01_build_splits.py`  
机器可读清单：`reports/p0_audit.json`、`reports/p0_split_manifest.json`

## 1. 数据身份

本地 SI 与 TDC `hERG`（Dataverse file 4259588）**完全同源**：

- 两边都是 655 行、615 个唯一 InChIKey，按 InChIKey 双向覆盖率均为 1.00。
- 来源论文：Wang et al., *Mol. Pharmaceutics* 2016, DOI 10.1021/acs.molpharmaceut.6b00471。
- 因此不能把本地表当作“新数据集”；可主张的是**清洗、去重与统一拆分协议**。
- 68 条 “External validation” 是 TDC hERG 的子集，**不是独立外部验证集**；去重后 66 条，按本次全局拆分落入 train 48 / valid 8 / test 10。论文中不得称其为 independent external validation。

## 2. 原始数据问题

| 问题 | 数值 |
|---|---|
| 原始行数 / 唯一 InChIKey | 655 / 615（40 行重复，40 组） |
| 重复组内标签冲突 | 9 组（已剔除） |
| 含盐/混合物 SMILES | 12 |
| 含形式电荷 SMILES | 302 |
| pIC50 可用行 | 526（483 个唯一化合物） |
| Class 阈值 | pIC50 = 4.4（40 µM）；class0 最大 4.38，class1 最小 4.40 |
| 原始 Set I/II | 392 / 195 / 68，两套拆分只共享 68 条外部集 |
| Set I train/test 化合物重叠 | 21 |
| Set II train/test 化合物重叠 | 16 |
| Set I test scaffold 覆盖率 | 0.377 |
| Set II test scaffold 覆盖率 | 0.307 |

结论：原始 Set I/II **都不是骨架拆分**，且存在跨集重复化合物；不能直接用于论文主实验。

## 3. 清洗规则

- RDKit `LargestFragmentChooser` → `Uncharger` → canonical SMILES → 标准 InChIKey → Murcko scaffold。
- 以完整 InChIKey 去重；同一化合物多条记录取 pIC50 中位数、标签多数票。
- 标签冲突组整组剔除（hERG 9 组、Ames 2 组、DILI 0 组）。
- 无环分子在拆分层使用 `ACYCLIC:<InChIKey>` 唯一键，避免所有无环分子落入同一组。

## 4. 端点规模（清洗后）

| 端点 | 行数 | 正/负 | scaffold | pIC50 可用 | 备注 |
|---|---:|---:|---:|---:|---|
| hERG | 606 | 413 / 193 | 366 | 483 | 主端点；123 条仅二分类标签 |
| DILI | 474 | 236 / 238 | 310 | 0 | 小样本端点 |
| Ames | 7246 | 3945 / 3301 | 1576 | 0 | 大样本辅助端点 |

## 5. 拆分协议

- **全局 scaffold 分区**：三个端点共用同一套 scaffold → train/valid/test 映射，保证多任务训练时测试端点的骨架不会出现在任何端点的训练集里。
- 目标比例 80/10/10；确定性贪心（按组大小降序、按正例数、再按 scaffold 字典序），无随机种子。
- 校验：`scaffold_disjoint = true`，`compound_disjoint = true`。
- 同一 InChIKey 因互变异构产生不同 Murcko 时，取该化合物出现次数最多的 scaffold 作为规范 scaffold。

### 实际划分

| 端点 | train | valid | test | train 正例 | valid 正例 | test 正例 |
|---|---:|---:|---:|---:|---:|---:|
| hERG | 485 | 62 | 59 | 335 | 36 | 42 |
| DILI | 379 | 44 | 51 | 191 | 23 | 22 |
| Ames | 5802 | 712 | 732 | 3142 | 426 | 377 |
| 合计 | 6666 | 818 | 842 | 3668 | 485 | 441 |

hERG 训练集中 385 个化合物有 pIC50，可承载“二分类 + pIC50 辅助回归”的部分标签多任务实验。低数据曲线建议取 n = 50 / 100 / 200 / 400（不超过 hERG 训练集 485）。

文件：
- `data/processed/global_split.csv`
- `data/processed/splits/{herg,dili,ames}_splits.csv`
- `data/processed/*_standardized.csv`

## 6. 仍待解决

1. **独立外部验证**：需另取 TDC `herg_karim`（或 ChEMBL/hERG Central）。本地 68 条不可用；阈值 10 µM 与本地 40 µM 不一致，需在外部验证实验中单独说明或做阈值协调。
2. 原始论文的 32 个基线（RP/NBC/SVM）在新拆分上不可直接比较；需在新拆分上复跑经典基线。
3. CheMeleon 预训练语料可能覆盖测试化合物，论文局限性中需披露（其预训练目标是 Mordred 描述符，不是 hERG 标签）。
