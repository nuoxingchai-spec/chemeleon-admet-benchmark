"""Assemble P3 report: Karim external validation and transfer diagnostics."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"


def f(x, n=3):
    return f"{x:.{n}f}" if pd.notna(x) else "–"


def main():
    man = json.loads((R / "p3_external_manifest.json").read_text(encoding="utf-8"))
    ext = pd.read_csv(R / "external_runs.csv")
    tr = pd.read_csv(R / "external_transfer.csv")

    k = man["karim"]
    ov = man["overlap"]
    ta = man["threshold_alignment"]
    lines = ["# P3：hERG 外部验证（Karim 集）与迁移诊断", ""]

    lines += ["## 0. 结论", "",
              "1. 原始 SI 的 606 个化合物中有 458 个（75.6%）直接出现在 Karim 集中，原论文所称的外部验证并不独立。",
              "2. 本地标签阈值约 40 µM（pIC50 ≥ 4.41），Karim 为 10 µM（pIC50 ≥ 5）；83 个本地阳性落在 4.4–5.0 灰区。",
              "3. 在去除化合物与骨架重叠的 Karim 子集（11,899 条）上，所有模型的外部 AUC 仅 0.60–0.65，低于 0.80 的预设门槛；按 Go/No-Go，外部验证只作为附录敏感性分析。",
              "4. 迁移失败主要由骨架覆盖决定：与本地共享骨架的 Karim 化合物 AUC 0.803，全新骨架 0.653；新颖度分箱内部没有单调下降。",
              "5. 阈值不一致主要损害校准而非排序：同一批本地测试化合物，10 µM 标签下 AUC 略升（0.85→0.90），但 ECE 从 0.09 升到 0.18。",
              ""]

    lines += ["## 1. 数据与重叠", "",
              f"- Karim 原始 {k['raw_rows']} 行，标准化成功 {k['standardized']}，去重后 {k['unique_after_dedup']} 个化合物，"
              f"阳性/阴性 {k['positives']}/{k['negatives']}。",
              f"- 与本地 hERG 完全重叠 {ov['full_inchikey_with_local_herg']} 个化合物；共享 Murcko 骨架 {ov['karim_rows_sharing_local_scaffold']} 条；"
              f"去除化合物重叠后 {ov['external_all_rows']} 条，再去骨架重叠后 {ov['external_clean_rows']} 条。",
              f"- 阈值对齐后的本地训练集：train/valid/test = {ta['per_split']['train']}/{ta['per_split']['valid']}/{ta['per_split']['test']}；"
              f"丢弃灰区 {ta['dropped_gray']} 条、缺失 pIC50 {ta['dropped_missing_pIC50']} 条。", ""]

    lines += ["## 2. 外部评估（external_clean，无化合物/骨架重叠）", "",
              "| 模型 | 训练标签 | AUC | 95% CI | Brier | ECE |", "|---|---|---|---|---|---|"]
    e = ext[ext.eval_set == "external_clean"].copy()
    e["source"] = e["source"].fillna("original")
    e = e.sort_values(["source", "model", "seed"])
    for _, r in e.iterrows():
        seed = r["seed"]
        seed_txt = f" s{seed}" if str(seed).isdigit() else ""
        lines.append(
            f"| {r['model']}{seed_txt} | {r['source']} | {f(r['auc'])} | "
            f"[{f(r['auc_ci_low'])}, {f(r['auc_ci_high'])}] | {f(r['brier'])} | {f(r['ece'])} |"
        )
    lines.append("")

    lines += ["## 3. 迁移分解（CheMeleon，原始 40 µM 标签）", "",
              "| 子集 | n | AUC | 平均预测概率 | ECE |", "|---|---|---|---|---|"]
    t = tr[tr.model == "chemeleon_original"]
    for _, r in t.iterrows():
        lines.append(f"| {r['subset']} | {r['n']} | {f(r['auc'])} | {f(r['mean_p'])} | {f(r['ece'])} |")
    lines.append("")

    lines += ["## 4. 阈值敏感性（本地 test，同一批化合物）", "",
              "| 模型 | 40 µM AUC | 10 µM AUC | 40 µM ECE | 10 µM ECE |", "|---|---|---|---|---|"]
    for model, g in tr[tr.subset.str.startswith("local_test")].groupby("model"):
        a = g[g.subset == "local_test_40uM"].iloc[0]
        b = g[g.subset == "local_test_10uM"].iloc[0]
        lines.append(f"| {model} | {f(a['auc'])} | {f(b['auc'])} | {f(a['ece'])} | {f(b['ece'])} |")
    lines.append("")

    lines += ["## 5. 反向迁移（Karim 训练 → 本地 test）", "",
              "| 模型 | 标签 | n | AUC |", "|---|---|---|---|"]
    for _, r in tr[tr.model == "rf_karim_trained"].iterrows():
        lines.append(f"| {r['model']} | {r['subset']} | {r['n']} | {f(r['auc'])} |")
    lines.append("")
    lines += ["反向迁移同样有限，说明本地序列与 Karim 的化学空间差异是双向的；"
              "12k 规模的外部数据可以学到可迁移的 hERG 规律（Karim 内部骨架划分 AUC 0.854），"
              "但 400–600 条的本地数据不足以覆盖该空间。", ""]

    lines += ["## 6. 对论文的影响", "",
              "- 外部 AUC 未达 0.80，按预设 Go/No-Go 不作为主结果，仅作附录。",
              "- 反而支持主论点：**骨架覆盖度而非预训练**是跨数据集性能的主要决定因素；"
              "同时说明文献中常见的“外部验证”需要先做化合物与骨架去重、并统一活性阈值。", ""]
    (R / "p3_external.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
