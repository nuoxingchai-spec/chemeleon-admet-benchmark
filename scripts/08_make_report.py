"""Assemble the P1 results report from experiment artifacts."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"


def fmt(x, n=3):
    return f"{x:.{n}f}" if pd.notna(x) else "–"


def main():
    manifest = json.loads((R / "p0_split_manifest.json").read_text(encoding="utf-8"))
    base = pd.read_csv(R / "baselines_classical.csv")
    runs = pd.read_csv(R / "chemprop_runs.csv")
    low = pd.read_csv(R / "lowdata.csv")
    pairs = pd.read_csv(R / "paired_comparisons.csv")

    lines = ["# P1 实验结果（hERG / DILI / Ames，全局骨架划分）", ""]
    lines.append("机器可读结果见 `reports/`；划分协议见 `p0_data_audit.md`；"
                 "校准/覆盖见 `p2_calibration.md`；外部验证见 `p3_external.md`。")
    lines.append("")

    lines += ["## 0. 关键结论", "",
              "1. 原始 SI 的 “External validation” 子集并非独立外部集：606 个本地化合物中 458 个直接出现在 Karim 集内；原 Set I/II 也不是骨架不相交。本报告一律使用重建的全局骨架不相交划分。",
              "2. 在完整数据上，CheMeleon 相对 scratch（默认 300×3）的 3-seed 集成 AUC 增益均不显著（hERG +0.014, p=0.76；DILI +0.040, p=0.41；Ames +0.018, p=0.050），但 hERG 上 Brier 显著更优（ΔBrier −0.039, p=0.035），ECE 的 95% CI 也偏向更好。",
              "3. 容量归因是端点依赖的：同架构随机初始化对照（2048×6，参数量与 CheMeleon 完全相同）在 hERG 上显著低于 CheMeleon（ΔAUC +0.122 [0.017, 0.237], p=0.025），数值上甚至低于 scratch（−0.107, p=0.104）；但在 DILI/Ames 上 CheMeleon 与 matched 差距接近 0（−0.002, p=0.94；+0.010, p=0.26）。即 hERG 上预训练收益超越容量，DILI/Ames 上可由容量解释。",
              "4. 低数据（hERG）：CheMeleon 相对 scratch 的 AUC 优势为 +0.15（n=50–100）与 +0.10（n=200），n=400 时 scratch 追平（0.866 vs 0.864）。固定容量下的预训练收益在 n=200/400 仍为 +0.09/+0.09（vs matched）；最佳容量对照 matched+dropout 在 n≤100 与 CheMeleon 差距仅 0.01–0.03，n=200/400 为 +0.04/+0.10。",
              "5. 多任务不带来 AUC 收益（3-seed 集成：hERG −0.005, p=0.86；DILI −0.006, p=0.84；Ames +0.003, p=0.48），且在 Ames 上显著恶化校准（ΔECE +0.045, p<0.001；ΔBrier +0.014, p=0.001），不作为主方法。",
              "6. split conformal 在 test 内部可交换划分下达到名义覆盖（Ames 0.90）；但以 early-stopping 所用的 valid 作校准集时 Ames 仅 0.848，失效来自模型选择乐观偏差（valid AUC 0.908 vs test 0.827）而非骨架位移；366 点/153 簇下簇条件校准不可达（见 P2）。",
              "7. 外部 Karim 集上所有模型 AUC 仅 0.60–0.65，未达 0.80 门槛；迁移能力由骨架覆盖决定（共享骨架 0.80 vs 全新骨架 0.65），外部验证仅作附录（见 P3）。",
              ""]

    lines += ["## 1. 数据与划分", "",
              "| 端点 | 原始行 | 去重/冲突后 | 阳性/阴性 | 骨架数 | train/valid/test |",
              "|---|---|---|---|---|---|"]
    for e in manifest["endpoints"]:
        per = manifest["per_endpoint"][e["endpoint"]]
        sc = per["split_counts"]
        lines.append(
            f"| {e['endpoint']} | {e['raw_rows']} | {e['modeling_rows']} | "
            f"{e['class_counts']['1']}/{e['class_counts']['0']} | {e['scaffolds']} | "
            f"{sc['train']}/{sc['valid']}/{sc['test']} |"
        )
    chk = manifest["global_checks"]
    lines += ["", f"全局检查：scaffold_disjoint={chk['scaffold_disjoint']}，"
                  f"compound_disjoint={chk['compound_disjoint']}；全局行数 "
                  f"{chk['split_counts']['train']}/{chk['split_counts']['valid']}/{chk['split_counts']['test']}。", ""]

    lines += ["## 2. 主结果（test，AUC 为多种子均值 ± 标准差）", "",
              "ECE/Brier 为各种子单独评估后的均值；第 5 节与 P2 使用种子集成的概率，两者数值略有差异。", "",
              "| 端点 | 模型 | 种子数 | AUC | ECE | Brier |", "|---|---|---|---|---|---|"]
    for ep in ["herg", "dili", "ames"]:
        rows = []
        b = base[(base.endpoint == ep) & (base.split == "test")]
        for _, r in b.iterrows():
            rows.append({"model": r["model"], "seeds": 1, "auc": r["auc"], "auc_sd": 0.0,
                         "ece": r["ece"], "brier": r["brier"]})
        c = runs[(runs.endpoint == ep) & (runs.split == "test")]
        for model, g in c.groupby("model"):
            rows.append({"model": model, "seeds": len(g), "auc": g["auc"].mean(),
                         "auc_sd": g["auc"].std(ddof=0), "ece": g["ece"].mean(),
                         "brier": g["brier"].mean()})
        order = {"rf": 0, "histgb": 1, "logreg": 2, "chemprop_none": 3,
                 "chemprop_matched": 4, "chemprop_matched_dropout": 5,
                 "chemprop_chemeleon": 6, "multitask_chemeleon": 7}
        for r in sorted(rows, key=lambda x: order.get(x["model"], 9)):
            lines.append(
                f"| {ep} | {r['model']} | {r['seeds']} | {fmt(r['auc'])} ± {fmt(r['auc_sd'])} | "
                f"{fmt(r['ece'])} | {fmt(r['brier'])} |"
            )
    lines.append("")

    cls_path = R / "classical_vs_chemprop.csv"
    if cls_path.exists():
        cls = pd.read_csv(cls_path)
        lines += ["### 2b. CheMeleon 种子集成 vs 最强经典基线（配对 bootstrap，2000 次）", "",
                  "| 端点 | 对照 | n | CheMeleon AUC | 经典 AUC | ΔAUC [95% CI] | p | ΔECE [95% CI] | p |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for _, r in cls.iterrows():
            lines.append(
                f"| {r['endpoint']} | {r['comparison'].replace('chemeleon_vs_', '')} | {int(r['n'])} | "
                f"{fmt(r['auc_chemprop'])} | {fmt(r['auc_classical'])} | "
                f"{fmt(r['d_auc'])} [{fmt(r['d_auc_lo'])}, {fmt(r['d_auc_hi'])}] | {fmt(r['d_auc_p'])} | "
                f"{fmt(r['d_ece'])} [{fmt(r['d_ece_lo'])}, {fmt(r['d_ece_hi'])}] | {fmt(r['d_ece_p'])} |"
            )
        lines += ["", "hERG 上 CheMeleon 显著优于最强经典基线；DILI 与 Ames 上 ΔAUC 的 95% CI 跨 0，"
                      "即与 ECFP4+RF 无法区分；Ames 上 CheMeleon 的 ECE 反而显著更差（RF ECE 0.032）。", ""]

    ctrl_path = R / "control_contrast.csv"
    if ctrl_path.exists():
        ctrl = pd.read_csv(ctrl_path)
        lines += ["### 2c. 预训练 vs 容量：CheMeleon 与同架构随机初始化（2048×6）对照", "",
                  "对照模型与 CheMeleon 编码器结构、参数量完全相同（9,329,247），只差是否载入预训练权重；"
                  "概率为各种子集成平均，Δ 为配对 bootstrap（2000 次）。", "",
                  "| 端点 | A | B | 种子 A/B | AUC A | AUC B | ΔAUC [95% CI] | p | ΔECE | ΔBrier |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in ctrl.iterrows():
            lines.append(
                f"| {r['endpoint']} | {r['model_a']} | {r['model_b']} | {int(r['seeds_a'])}/{int(r['seeds_b'])} | "
                f"{fmt(r['auc_a'])} | {fmt(r['auc_b'])} | "
                f"{fmt(r['d_auc'])} [{fmt(r['d_auc_lo'])}, {fmt(r['d_auc_hi'])}] | {fmt(r['d_auc_p'])} | "
                f"{fmt(r['d_ece'])} | {fmt(r['d_brier'])} |"
            )
        lines.append("")

    lines += ["## 3. 配对 bootstrap 比较（单种子 seed 42，2000 次重采样）", "",
              "| 端点 | A | B | ΔAUC [95% CI] | p | ΔECE | ΔBrier |", "|---|---|---|---|---|---|---|"]
    for _, r in pairs.iterrows():
        lines.append(
            f"| {r['endpoint']} | {r['model_a']} | {r['model_b']} | "
            f"{fmt(r['d_auc'])} [{fmt(r['d_auc_ci_low'])}, {fmt(r['d_auc_ci_high'])}] | {fmt(r['d_auc_p'])} | "
            f"{fmt(r['d_ece'])} | {fmt(r['d_brier'])} |"
        )
    lines.append("")

    ens_path = R / "ensemble_comparisons.csv"
    if ens_path.exists():
        ens = pd.read_csv(ens_path)
        lines += ["### 3b. 种子集成比较（概率平均）", "",
                  "多任务模型同为 2048×6（`--from-foundation` 覆盖架构），100 epoch 上限；"
                  "其 patience 为 25，但三次运行 best epoch 分别为 3/17/15，未触及该差异。", "",
                  "| 端点 | A | B | n | AUC A | AUC B | ΔAUC [95% CI] | p | ΔECE | ΔBrier |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in ens.iterrows():
            lines.append(
                f"| {r['endpoint']} | {r['model_a']} | {r['model_b']} | {r['n']} | "
                f"{fmt(r['auc_a'])} | {fmt(r['auc_b'])} | "
                f"{fmt(r['d_auc'])} [{fmt(r['d_auc_ci_low'])}, {fmt(r['d_auc_ci_high'])}] | {fmt(r['d_auc_p'])} | "
                f"{fmt(r['d_ece'])} | {fmt(r['d_brier'])} |"
            )
        lines.append("")

    lines += ["## 4. hERG 低数据缩放（3 个抽样种子，test AUC）", "",
              "| train n | scratch (300) | matched (2048×6) | matched+dropout 0.1 | CheMeleon | Δ(CheMeleon−scratch) |",
              "|---|---|---|---|---|---|"]
    for n in sorted(low.train_n.unique()):
        a = low[(low.train_n == n) & (low.model == "scratch")]
        b = low[(low.train_n == n) & (low.model == "chemeleon")]
        m = low[(low.train_n == n) & (low.model == "matched")]
        md = low[(low.train_n == n) & (low.model == "matched_dropout")]
        d = (b.set_index("seed")["auc"] - a.set_index("seed")["auc"])
        m_txt = f"{fmt(m['auc'].mean())} ± {fmt(m['auc'].std(ddof=0))}" if len(m) else "–"
        md_txt = f"{fmt(md['auc'].mean())} ± {fmt(md['auc'].std(ddof=0))}" if len(md) else "–"
        lines.append(
            f"| {n} | {fmt(a['auc'].mean())} ± {fmt(a['auc'].std(ddof=0))} | {m_txt} | {md_txt} | "
            f"{fmt(b['auc'].mean())} ± {fmt(b['auc'].std(ddof=0))} | "
            f"{fmt(d.mean())} ± {fmt(d.std(ddof=0))} |"
        )
    lines.append("")

    conf_path = R / "conformal_scaffold.csv"
    cal_path = R / "calibration_pooled.csv"
    if conf_path.exists() and cal_path.exists():
        conf = pd.read_csv(conf_path)
        cal = pd.read_csv(cal_path)
        lines += ["## 5. 校准与 conformal 摘要（详见 `p2_calibration.md`）", "",
                  "| 模型 | 合并 raw ECE | 合并 Platt ECE | ΔECE [95% CI] |", "|---|---|---|---|"]
        for model, g in cal.groupby("model"):
            row = {r["calibrator"]: r for _, r in g.iterrows()}
            lines.append(f"| {model} | {fmt(row['raw']['ece_pooled'])} | {fmt(row['platt']['ece_pooled'])} | "
                         f"{fmt(row['platt']['d_ece_pooled'])} [{fmt(row['platt']['d_ece_lo'])}, "
                         f"{fmt(row['platt']['d_ece_hi'])}] |")
        lines += ["", "| 端点 | 模型 | 标准 conformal 覆盖 | 集合大小 |", "|---|---|---|---|"]
        s = conf[(conf.calibration == "raw") & (conf.conformal == "standard")]
        for _, r in s.iterrows():
            lines.append(f"| {r['endpoint']} | {r['model']} | {fmt(r['coverage'])} | {fmt(r['set_size'])} |")
        lines.append("")

    lines += ["## 6. 复现", "",
              "```bash",
              "python scripts/00_audit.py && python scripts/01_build_splits.py",
              "python scripts/02_baselines_classical.py",
              "python scripts/03_chemprop_run.py --endpoint herg --foundation CHEMELEON --seed 42",
              "python scripts/04_calibration.py runs/chemprop/herg_chemeleon_s42/preds.json",
              "python scripts/11_conformal_scaffold.py && python scripts/13_calibration_ci.py",
              "python scripts/rebuild_runs.py && python scripts/08_make_report.py",
              "```", ""]

    (R / "p1_results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
