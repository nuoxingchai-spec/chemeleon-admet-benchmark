# P1 实验结果（hERG / DILI / Ames，全局骨架划分）

机器可读结果见 `reports/`；划分协议见 `p0_data_audit.md`；校准/覆盖见 `p2_calibration.md`；外部验证见 `p3_external.md`。

## 0. 关键结论

1. 原始 SI 的 “External validation” 子集并非独立外部集：606 个本地化合物中 458 个直接出现在 Karim 集内；原 Set I/II 也不是骨架不相交。本报告一律使用重建的全局骨架不相交划分。
2. 在完整数据上，CheMeleon 相对 scratch（默认 300×3）的 3-seed 集成 AUC 增益均不显著（hERG +0.014, p=0.76；DILI +0.040, p=0.41；Ames +0.018, p=0.050），但 hERG 上 Brier 显著更优（ΔBrier −0.039, p=0.035），ECE 的 95% CI 也偏向更好。
3. 容量归因是端点依赖的：同架构随机初始化对照（2048×6，参数量与 CheMeleon 完全相同）在 hERG 上显著低于 CheMeleon（ΔAUC +0.122 [0.017, 0.237], p=0.025），数值上甚至低于 scratch（−0.107, p=0.104）；但在 DILI/Ames 上 CheMeleon 与 matched 差距接近 0（−0.002, p=0.94；+0.010, p=0.26）。即 hERG 上预训练收益超越容量，DILI/Ames 上可由容量解释。
4. 低数据（hERG）：CheMeleon 相对 scratch 的 AUC 优势为 +0.15（n=50–100）与 +0.10（n=200），n=400 时 scratch 追平（0.866 vs 0.864）。固定容量下的预训练收益在 n=200/400 仍为 +0.09/+0.09（vs matched）；最佳容量对照 matched+dropout 在 n≤100 与 CheMeleon 差距仅 0.01–0.03，n=200/400 为 +0.04/+0.10。
5. 多任务不带来 AUC 收益（3-seed 集成：hERG −0.005, p=0.86；DILI −0.006, p=0.84；Ames +0.003, p=0.48），且在 Ames 上显著恶化校准（ΔECE +0.045, p<0.001；ΔBrier +0.014, p=0.001），不作为主方法。
6. split conformal 在 test 内部可交换划分下达到名义覆盖（Ames 0.90）；但以 early-stopping 所用的 valid 作校准集时 Ames 仅 0.848，失效来自模型选择乐观偏差（valid AUC 0.908 vs test 0.827）而非骨架位移；366 点/153 簇下簇条件校准不可达（见 P2）。
7. 外部 Karim 集上所有模型 AUC 仅 0.60–0.65，未达 0.80 门槛；迁移能力由骨架覆盖决定（共享骨架 0.80 vs 全新骨架 0.65），外部验证仅作附录（见 P3）。

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

## 6. 复现

```bash
python scripts/00_audit.py && python scripts/01_build_splits.py
python scripts/02_baselines_classical.py
python scripts/03_chemprop_run.py --endpoint herg --foundation CHEMELEON --seed 42
python scripts/04_calibration.py runs/chemprop/herg_chemeleon_s42/preds.json
python scripts/11_conformal_scaffold.py && python scripts/13_calibration_ci.py
python scripts/rebuild_runs.py && python scripts/08_make_report.py
```
