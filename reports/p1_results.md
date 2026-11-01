# P1 实验结果（hERG / DILI / Ames，全局骨架划分）

机器可读结果见 `reports/`；划分协议见 `p0_data_audit.md`；校准/覆盖见 `p2_calibration.md`；外部验证见 `p3_external.md`。

## 0. 关键结论

1. 原始 SI 的 “External validation” 子集并非独立外部集：606 个本地化合物中 458 个直接出现在 Karim 集内；原 Set I/II 也不是骨架不相交。本报告一律使用重建的全局骨架不相交划分。
2. 在完整数据上，CheMeleon 相对 scratch（默认 300×3）的 3-seed 集成 AUC 增益均不显著（hERG +0.014, p=0.76；DILI +0.040, p=0.41；Ames +0.018, p=0.050），但 hERG 上 Brier 显著更优（ΔBrier −0.039, p=0.035），ECE 的 95% CI 也偏向更好。
3. 容量归因是端点依赖的：同架构随机初始化对照（2048×6，参数量与 CheMeleon 完全相同）在 hERG 上显著低于 CheMeleon（ΔAUC +0.120 [0.012, 0.239], p=0.030，5 000 次骨架簇 bootstrap 下 p=0.148, q=0.48），数值上甚至低于 scratch（−0.106, p=0.108）；但在 DILI/Ames 上 CheMeleon 与 matched 差距接近 0（−0.002, p=0.94；+0.010, p=0.25）。即 hERG 上预训练收益超越容量，DILI/Ames 上可由容量解释；TOST 显示 DILI 仅在 compound 级等价、Ames 两级均等价（见 §6b）。长预算（300 epochs/patience 50）不改变结论：matched 仍为 0.760，CheMeleon−matched +0.131（compound p=0.034），scratch 不变（见 §6c）。
4. 低数据（hERG）：CheMeleon 相对 scratch 的 AUC 优势为 +0.15（n=50–100）与 +0.10（n=200），n=400 时 scratch 追平（0.866 vs 0.864）。固定容量下的预训练收益在 n=200/400 仍为 +0.09/+0.09（vs matched）；最佳容量对照 matched+dropout 在 n≤100 与 CheMeleon 差距仅 0.01–0.03，n=200/400 为 +0.04/+0.10。
5. 多任务不带来 AUC 收益（3-seed 集成：hERG −0.005, p=0.86；DILI −0.006, p=0.84；Ames +0.003, p=0.48），且在 Ames 上显著恶化校准（ΔECE +0.045, p<0.001；ΔBrier +0.014, p=0.001），不作为主方法。
6. split conformal 在 test 内部可交换划分下达到名义覆盖（Ames 0.90）；但以 early-stopping 所用的 valid 作校准集时 Ames 仅 0.848，失效来自模型选择乐观偏差（valid AUC 0.908 vs test 0.827）而非骨架位移；366 点/153 簇下簇条件校准不可达（见 P2）。
7. 外部 Karim 集上所有模型 AUC 仅 0.60–0.66，未达 0.80 门槛；迁移能力由骨架覆盖决定（共享骨架 0.80 vs 全新骨架 0.65），外部验证仅作附录（见 P3）。
8. 第二骨架划分（seed 2027，478/66/62，58 test scaffolds）未复现 hERG 预训练差距：CheMeleon/matched/scratch 种子均值 AUC 0.869±0.003 / 0.857±0.019 / 0.752±0.008，CheMeleon−matched +0.015 [−0.032, 0.070]（p=0.60 compound，0.61 scaffold），matched−scratch 由 −0.106 反转为 +0.097；首划分的 +0.12 应视为上界（见 §6）。

## 1. 数据与划分

| 端点 | 原始行 | 去重/冲突后 | 阳性/阴性 | 骨架数 | train/valid/test |
|---|---|---|---|---|---|
| herg | 655 | 606 | 413/193 | 366 | 485/62/59 |
| dili | 475 | 474 | 236/238 | 310 | 379/44/51 |
| ames | 7278 | 7246 | 3945/3301 | 1576 | 5802/712/732 |

全局检查：scaffold_disjoint=True，compound_disjoint=True；全局行数 6666/818/842。

## 2. 主结果（test，AUC 为多种子均值 ± 标准差）

ECE/Brier 为各种子单独评估后的均值；第 5 节与 P2 使用种子集成的概率，两者数值略有差异。

| 端点 | 模型 | 种子数 | AUC | ECE | Brier |
|---|---|---|---|---|---|
| herg | rf | 1 | 0.733 ± 0.000 | 0.188 | 0.178 |
| herg | histgb | 1 | 0.715 ± 0.000 | 0.264 | 0.252 |
| herg | logreg | 1 | 0.749 ± 0.000 | 0.174 | 0.194 |
| herg | chemprop_none | 3 | 0.871 ± 0.006 | 0.154 | 0.174 |
| herg | chemprop_matched | 3 | 0.752 ± 0.015 | 0.174 | 0.194 |
| herg | chemprop_chemeleon | 3 | 0.881 ± 0.003 | 0.115 | 0.135 |
| herg | multitask_chemeleon | 3 | 0.867 ± 0.046 | 0.160 | 0.159 |
| dili | rf | 1 | 0.861 ± 0.000 | 0.147 | 0.159 |
| dili | histgb | 1 | 0.803 ± 0.000 | 0.175 | 0.197 |
| dili | logreg | 1 | 0.826 ± 0.000 | 0.132 | 0.173 |
| dili | chemprop_none | 3 | 0.833 ± 0.002 | 0.177 | 0.171 |
| dili | chemprop_matched | 3 | 0.871 ± 0.010 | 0.159 | 0.148 |
| dili | chemprop_chemeleon | 3 | 0.875 ± 0.014 | 0.144 | 0.153 |
| dili | multitask_chemeleon | 3 | 0.867 ± 0.002 | 0.176 | 0.152 |
| ames | rf | 1 | 0.825 ± 0.000 | 0.032 | 0.171 |
| ames | histgb | 1 | 0.821 ± 0.000 | 0.071 | 0.177 |
| ames | logreg | 1 | 0.771 ± 0.000 | 0.144 | 0.215 |
| ames | chemprop_none | 3 | 0.804 ± 0.004 | 0.090 | 0.189 |
| ames | chemprop_matched | 3 | 0.809 ± 0.002 | 0.081 | 0.184 |
| ames | chemprop_chemeleon | 3 | 0.822 ± 0.003 | 0.111 | 0.184 |
| ames | multitask_chemeleon | 3 | 0.818 ± 0.005 | 0.169 | 0.206 |

### 2b. CheMeleon 种子集成 vs 最强经典基线（配对 bootstrap，2000 次）

| 端点 | 对照 | n | CheMeleon AUC | 经典 AUC | ΔAUC [95% CI] | p | ΔECE [95% CI] | p |
|---|---|---|---|---|---|---|---|---|
| herg | logreg | 59 | 0.891 | 0.749 | 0.142 [0.029, 0.275] | 0.014 | -0.075 [-0.178, 0.016] | 0.125 |
| dili | rf | 51 | 0.878 | 0.861 | 0.016 [-0.068, 0.106] | 0.733 | -0.023 [-0.132, 0.091] | 0.661 |
| ames | rf | 732 | 0.827 | 0.825 | 0.001 [-0.020, 0.021] | 0.935 | 0.059 [0.020, 0.095] | 0.003 |

hERG 上 CheMeleon 显著优于最强经典基线；DILI 与 Ames 上 ΔAUC 的 95% CI 跨 0，即与 ECFP4+RF 无法区分；Ames 上 CheMeleon 的 ECE 反而显著更差（RF ECE 0.032）。

### 2c. 预训练 vs 容量：CheMeleon 与同架构随机初始化（2048×6）对照

对照模型与 CheMeleon 编码器结构、参数量完全相同（9,329,247），只差是否载入预训练权重；概率为各种子集成平均，Δ 为配对 bootstrap（2000 次）。

| 端点 | A | B | 种子 A/B | AUC A | AUC B | ΔAUC [95% CI] | p | ΔECE | ΔBrier |
|---|---|---|---|---|---|---|---|---|---|
| herg | chemeleon | matched | 3/3 | 0.891 | 0.770 | 0.122 [0.017, 0.237] | 0.025 | -0.069 | -0.053 |
| herg | chemeleon | scratch | 3/3 | 0.891 | 0.877 | 0.015 [-0.076, 0.108] | 0.756 | -0.066 | -0.039 |
| herg | matched | scratch | 3/3 | 0.770 | 0.877 | -0.107 [-0.241, 0.019] | 0.104 | 0.003 | 0.014 |
| dili | chemeleon | matched | 3/3 | 0.878 | 0.879 | -0.002 [-0.069, 0.071] | 0.937 | -0.005 | 0.009 |
| dili | chemeleon | scratch | 3/3 | 0.878 | 0.837 | 0.040 [-0.043, 0.133] | 0.406 | -0.061 | -0.020 |
| dili | matched | scratch | 3/3 | 0.879 | 0.837 | 0.042 [-0.019, 0.112] | 0.202 | -0.056 | -0.030 |
| ames | chemeleon | matched | 3/3 | 0.827 | 0.817 | 0.010 [-0.006, 0.027] | 0.257 | 0.032 | 0.001 |
| ames | chemeleon | scratch | 3/3 | 0.827 | 0.809 | 0.018 [0.000, 0.037] | 0.050 | 0.026 | -0.004 |
| ames | matched | scratch | 3/3 | 0.817 | 0.809 | 0.007 [-0.006, 0.021] | 0.279 | -0.007 | -0.005 |

## 3. 配对 bootstrap 比较（单种子 seed 42，2000 次重采样）

| 端点 | A | B | ΔAUC [95% CI] | p | ΔECE | ΔBrier |
|---|---|---|---|---|---|---|
| herg | herg_chemeleon_s42 | herg_scratch_s42 | 0.004 [-0.088, 0.094] | 0.930 | -0.062 | -0.043 |
| dili | dili_chemeleon_s42 | dili_scratch_s42 | 0.064 [-0.019, 0.159] | 0.150 | -0.098 | -0.048 |
| ames | ames_chemeleon_s42 | ames_scratch_s42 | 0.019 [0.001, 0.037] | 0.039 | 0.016 | -0.005 |
| herg | multi_chemeleon_s42 | herg_chemeleon_s42 | 0.049 [-0.007, 0.122] | 0.100 | 0.029 | -0.013 |
| dili | multi_chemeleon_s42 | dili_chemeleon_s42 | -0.030 [-0.089, 0.021] | 0.274 | 0.050 | 0.011 |
| ames | multi_chemeleon_s42 | ames_chemeleon_s42 | -0.001 [-0.008, 0.006] | 0.862 | 0.013 | 0.004 |

### 3b. 种子集成比较（概率平均）

多任务模型同为 2048×6（`--from-foundation` 覆盖架构），100 epoch 上限；其 patience 为 25，但三次运行 best epoch 分别为 3/17/15，未触及该差异。

| 端点 | A | B | n | AUC A | AUC B | ΔAUC [95% CI] | p | ΔECE | ΔBrier |
|---|---|---|---|---|---|---|---|---|---|
| herg | herg_chemeleon_s*(3) | herg_scratch_s*(3) | 59 | 0.891 | 0.877 | 0.014 [-0.076, 0.103] | 0.766 | -0.068 | -0.039 |
| dili | dili_chemeleon_s*(3) | dili_scratch_s*(3) | 51 | 0.878 | 0.837 | 0.041 [-0.046, 0.143] | 0.389 | -0.061 | -0.021 |
| ames | ames_chemeleon_s*(3) | ames_scratch_s*(3) | 732 | 0.827 | 0.809 | 0.018 [-0.000, 0.037] | 0.052 | 0.025 | -0.004 |
| herg | multi_chemeleon_s*(3) | herg_chemeleon_s*(3) | 59 | 0.885 | 0.891 | -0.005 [-0.062, 0.055] | 0.860 | 0.005 | 0.017 |
| dili | multi_chemeleon_s*(3) | dili_chemeleon_s*(3) | 51 | 0.871 | 0.878 | -0.006 [-0.068, 0.057] | 0.838 | 0.021 | -0.002 |
| ames | multi_chemeleon_s*(3) | ames_chemeleon_s*(3) | 732 | 0.830 | 0.827 | 0.003 [-0.006, 0.012] | 0.480 | 0.045 | 0.014 |

## 4. hERG 低数据缩放（3 个抽样种子，test AUC）

| train n | scratch (300) | matched (2048×6) | matched+dropout 0.1 | CheMeleon | Δ(CheMeleon−scratch) |
|---|---|---|---|---|---|
| 50 | 0.630 ± 0.027 | 0.747 ± 0.077 | 0.750 ± 0.085 | 0.782 ± 0.085 | 0.152 ± 0.058 |
| 100 | 0.635 ± 0.025 | 0.770 ± 0.037 | 0.770 ± 0.028 | 0.782 ± 0.052 | 0.148 ± 0.027 |
| 200 | 0.747 ± 0.069 | 0.756 ± 0.043 | 0.809 ± 0.039 | 0.847 ± 0.062 | 0.100 ± 0.089 |
| 400 | 0.866 ± 0.011 | 0.774 ± 0.019 | 0.766 ± 0.056 | 0.864 ± 0.027 | -0.003 ± 0.017 |

## 5. 校准与 conformal 摘要（详见 `p2_calibration.md`）

| 模型 | 合并 raw ECE | 合并 Platt ECE | ΔECE [95% CI] |
|---|---|---|---|
| chemeleon | 0.098 | 0.058 | -0.034 [-0.047, -0.017] |
| scratch | 0.065 | 0.056 | -0.008 [-0.028, 0.010] |

| 端点 | 模型 | 标准 conformal 覆盖 | 集合大小 |
|---|---|---|---|
| herg | chemeleon | 0.864 | 1.119 |
| herg | scratch | 1.000 | 1.661 |
| dili | chemeleon | 0.922 | 1.294 |
| dili | scratch | 0.941 | 1.647 |
| ames | chemeleon | 0.848 | 1.228 |
| ames | scratch | 0.828 | 1.224 |

## 6. 第二骨架划分（hERG，seed 2027）

随机骨架顺序 + 贪心配额重建，478/66/62（352/27/34 阳性），382 骨架，compound/scaffold 均不相交；三臂同预算重训（100 epoch，patience 20，seeds 42/1/2）。机器可读结果见 `reports/second_split_results.json`，逐 run 指标见 `reports/chemprop_runs_second.csv`。

| 模型 | test AUC（种子均值 ± SD） | 集成 AUC | PR-AUC | Brier | ECE |
|---|---|---|---|---|---|
| CheMeleon | 0.869 ± 0.003 | 0.871 | 0.918 | 0.156 | 0.174 |
| matched | 0.857 ± 0.019 | 0.856 | 0.877 | 0.195 | 0.199 |
| scratch | 0.752 ± 0.008 | 0.757 | 0.699 | 0.244 | 0.020 |

配对 bootstrap（5000 次，test 62 化合物 / 58 骨架簇）：

| 对比 | ΔAUC [95% CI] | p(compound) | p(scaffold) |
|---|---|---|---|
| CheMeleon−matched | +0.015 [−0.032, 0.070] | 0.598 | 0.614 |
| matched−scratch | +0.097 [−0.032, 0.240] | 0.152 | 0.156 |
| CheMeleon−scratch | +0.112 [−0.016, 0.250] | 0.092 | 0.091 |

解读：CheMeleon 跨两次划分稳定（种子均值 0.881 → 0.869），而 matched（0.752 → 0.857）与 scratch（0.871 → 0.752）各移动约 0.10 AUC，导致首划分的容量对比在第二划分上消失、matched−scratch 排序反转。首划分在 5000 次骨架簇 bootstrap 下为 +0.104 [−0.036, 0.249]（p=0.148，q=0.48）；结合第二划分，hERG 预训练差距按上界报告，论文不将其作为已建立效应。

## 6b. 等价性检验（TOST，margin ±0.06 AUC）

复用主分析的 compound / scaffold 配对 bootstrap（5 000 次），90% 分位区间落在 ±0.06 内即判定等价；margin 取 hERG 主效应 +0.120 的一半。

| 端点 | 对比 | 层级 | ΔAUC | 90% CI | 等价 | p_TOST |
|---|---|---|---|---|---|---|
| hERG | CheMeleon−matched | compound | +0.120 | [0.029, 0.220] | 否 | 0.853 |
| hERG | CheMeleon−matched | scaffold | +0.120 | [−0.015, 0.227] | 否 | 0.713 |
| DILI | CheMeleon−matched | compound | −0.002 | [−0.057, 0.056] | 是 | 0.042 |
| DILI | CheMeleon−matched | scaffold | −0.002 | [−0.067, 0.066] | 否 | 0.066 |
| Ames | CheMeleon−matched | compound | +0.010 | [−0.004, 0.025] | 是 | <0.001 |
| Ames | CheMeleon−matched | scaffold | +0.010 | [−0.012, 0.033] | 是 | 0.0002 |

解读：Ames 在两级都等价；DILI 只在 compound 级等价，scaffold 级因 39 个簇而区间略超 margin；hERG 明确不等价。论文据此把 DILI 的“无差异”改写成“compound 级等价、scaffold 级不确定”，避免把未拒绝 null 说成等价。

## 6c. 长预算对照（hERG，300 epochs / patience 50，seeds 42/1/2）

为排除“matched 对照只是训练不足”的解释，将 matched 与 scratch 各重训 3 seeds，预算从 100/20 提升到 300/50；其余（split、特征、优化器、评估）完全不变。

| 模型 | 集成 AUC | seed 均值 ± SD | best epoch（s42/s1/s2） | 与主预算集成 AUC 差 |
|---|---|---|---|---|
| matched_long | 0.760 | 0.759 ± 0.017 | 191/98/111 | +0.010（p=0.67） |
| scratch_long | 0.877 | 0.871 ± 0.007 | 43/43/58 | 0.000（p=1.00） |

| 对比 | ΔAUC [95% CI]（compound） | p（compound） | p（scaffold） |
|---|---|---|---|
| CheMeleon−matched_long | +0.131 [0.010, 0.266] | 0.034 | 0.119 |
| matched_long−scratch_long | −0.117 [−0.271, 0.025] | 0.099 | 0.153 |

解读：scratch 在主预算下已完全收敛，加预算后逐位不变；matched 的 best epoch 从 95/98/65 移到 191/98/111，但 test AUC 没有提升（0.770 → 0.760），CheMeleon 对 matched 的差距反而略增至 +0.131（compound p=0.034，scaffold p=0.119）。训练预算不是容量对照失效的原因；matched 的问题是不可训练/泛化差，而非欠拟合。

## 7. 复现

```bash
python scripts/00_audit.py && python scripts/01_build_splits.py
python scripts/02_baselines_classical.py
python scripts/03_chemprop_run.py --endpoint herg --foundation CHEMELEON --seed 42
python scripts/04_calibration.py runs/chemprop/herg_chemeleon_s42/preds.json
python scripts/11_conformal_scaffold.py && python scripts/13_calibration_ci.py
python scripts/36_tost.py && python scripts/37_long_budget.py
python scripts/rebuild_runs.py && python scripts/08_make_report.py
```

## 6d. 第二 FM（ChemBERTa-zinc-base，44.1M）容量对照

`seyonec/ChemBERTa-zinc-base-v1`（44,104,705 参数）在全局划分上以 40 epoch / patience 8 / lr 1e-4 / batch 32 / max_len 192 微调三臂：pretrained（预训练权重）、matched（同架构随机初始化，44.1M）、scratch（Roberta 256×4，3,553,793 参数）；seeds 42/1/2。结果见 `reports/second_fm_hd_results.json`、`second_fm_hd_metrics.csv`。

| 端点 | 臂 | 集成 AUC | 种子均值 ± SD | PR-AUC | best epoch (42/1/2) |
|---|---|---|---|---|---|
| hERG | pretrained | 0.759 | 0.773 ± 0.033 | 0.893 | 1/8/6 |
| hERG | matched | 0.763 | 0.758 ± 0.020 | 0.882 | 9/14/15 |
| hERG | scratch | 0.815 | 0.760 ± 0.063 | 0.924 | 4/14/19 |
| DILI | pretrained | 0.840 | 0.834 ± 0.024 | 0.783 | 3/6/10 |
| DILI | matched | 0.851 | 0.828 ± 0.017 | 0.802 | 18/16/15 |
| DILI | scratch | 0.823 | 0.786 ± 0.045 | 0.743 | 34/9/4 |
| Ames | pretrained | 0.776 | 0.762 ± 0.010 | 0.790 | 7/4/9 |
| Ames | matched | 0.735 | 0.723 ± 0.019 | 0.738 | 14/7/8 |
| Ames | scratch | 0.734 | 0.726 ± 0.015 | 0.746 | 4/6/12 |

| 端点 | 对比 | 层级 | ΔAUC [95% CI] | p | TOST 90% CI |
|---|---|---|---|---|---|
| hERG | pretrained−matched | compound | −0.004 [−0.109, 0.097] | 0.946 | [−0.092, 0.078] |
| hERG | pretrained−matched | scaffold | +0.009 [−0.087, 0.122] | 0.916 | [−0.074, 0.102] |
| DILI | pretrained−matched | compound | −0.011 [−0.106, 0.079] | 0.833 | [−0.090, 0.065] |
| DILI | pretrained−matched | scaffold | −0.012 [−0.117, 0.077] | 0.872 | [−0.098, 0.064] |
| Ames | pretrained−matched | compound | +0.041 [0.018, 0.063] | 0.0004 | [0.022, 0.059] |
| Ames | pretrained−matched | scaffold | +0.042 [0.015, 0.070] | 0.0004 | [0.020, 0.065] |
| Ames | matched−scratch | compound | +0.001 [−0.016, 0.018] | 0.854 | [−0.013, 0.016] |
| Ames | matched−scratch | scaffold | +0.001 [−0.021, 0.024] | 0.933 | [−0.018, 0.020] |

解读：hERG/DILI 上同架构随机初始化对照与预训练模型不可区分（−0.004、−0.011，scaffold p=0.92/0.87），而 Ames 上预训练相对同架构对照 +0.042 [0.016, 0.070]（scaffold p=0.0004，compound p=0.0014），且 matched 与 scratch 等价（+0.001，p=0.93）——增益不是容量。这是关键的阳性对照：同一协议在可检测的端点上确实检测到预训练效应，因此 hERG/DILI 的零结果不是工具失灵；CheMeleon 的 hERG +0.120 是模型特异的（ChemBERTa 在 hERG 上甚至 scratch 最好）。

## 6e. 全端点第二骨架划分（DILI seed 2030；Ames 待补）

DILI 第二划分 380/47/47（189/23/24 阳性），47 个 test 骨架。三臂同预算重训（100/20，seeds 42/1/2），bootstrap 5000 次。

| 模型 | 集成 AUC | 种子均值 ± SD | PR-AUC | Brier | ECE |
|---|---|---|---|---|---|
| CheMeleon | 0.938 | 0.934 ± 0.007 | 0.947 | 0.111 | 0.103 |
| matched | 0.949 | 0.925 ± 0.026 | 0.947 | 0.118 | 0.135 |
| scratch | 0.909 | 0.877 ± 0.056 | 0.930 | 0.142 | 0.151 |

| 对比 | ΔAUC [95% CI] | p(compound) | p(scaffold) |
|---|---|---|---|
| CheMeleon−matched | −0.011 [−0.082, 0.056] | 0.765 | 0.776 |
| matched−scratch | +0.040 [−0.025, 0.124] | 0.302 | 0.304 |
| CheMeleon−scratch | +0.029 [−0.042, 0.118] | 0.522 | 0.518 |

解读：DILI 的容量零结果在第二划分上复现（−0.011 vs 主划分 −0.002），方向与幅度一致，不受划分选择驱动。注意该划分整体更易（AUC 0.94 vs 0.875），但对比量是划分内配对的。

## 6f. ChemBERTa 学习率敏感性（5e-5 与 2e-4）

主表用统一的 1e-4（预训练与随机初始化同预算）。为检查该选择是否制造了 hERG/DILI 的零结果，补跑 lr=5e-5（hERG、DILI 全三臂 ×3 seeds）与 lr=2e-4（hERG、Ames，运行中）。lr=5e-5 的 hERG 结果：

| 臂 | 集成 AUC | 种子均值 ± SD | best epoch |
|---|---|---|---|
| pretrained | 0.829 | 0.821 ± 0.057 | 4/4/9 |
| matched | 0.714 | 0.716 ± 0.046 | 1/2/2 |
| scratch | 0.756 | 0.731 ± 0.048 | 7/6/33 |

pretrained−matched: +0.112 集成，compound 95% CI [−0.014, 0.255]（p=0.086），scaffold [−0.048, 0.306]（p=0.20）。DILI 在 5e-5：预训练 0.831、matched 0.848，差 −0.017（scaffold p=0.74），仍为零。但 5e-5 下 matched 臂 best epoch 为 1/2/2，属欠训练，不能作为“预训练在低学习率下有效”的证据；论文不采用该点，只把它作为预算敏感性的内部记录。

lr=2e-4 的 hERG（三臂 ×3 seeds，均正常收敛，matched best epoch 8/14/8）：

| 臂 | 集成 AUC | 种子均值 ± SD | best epoch |
|---|---|---|---|
| pretrained | 0.794 | 0.788 ± 0.035 | 2/7/4 |
| matched | 0.761 | 0.716 ± 0.047 | 8/14/8 |
| scratch | 0.768 | 0.760 ± 0.042 | 17/14/12 |

pretrained−matched: +0.034 集成，compound 95% CI [−0.068, 0.137]（p=0.52），scaffold [−0.066, 0.150]（p=0.50）。论文据此写“把学习率加倍后 hERG 对比仍不显著（+0.034, scaffold p=0.50）”，5e-5 的欠训练点只在内部记录。解读：hERG 上预训练优势对预算敏感（1e-4 时 −0.004，2e-4 时 +0.034，5e-5 时 +0.112 但对照欠训练），三档均不通过 scaffold bootstrap；Ames 的 +0.042 是目前唯一在 scaffold 级显著的预训练效应。论文将其写成“hERG 估计脆弱/未定、Ames 效应稳健”的证据，而不是“第二 FM 在所有预算下完全无收益”。
