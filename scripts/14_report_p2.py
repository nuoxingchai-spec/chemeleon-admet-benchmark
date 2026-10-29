"""Assemble P2 report: calibration, conformal coverage, selective prediction."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"


def f(x, n=3):
    return f"{x:.{n}f}" if pd.notna(x) else "–"


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def main():
    cal = pd.read_csv(R / "calibration_ci.csv")
    pooled = pd.read_csv(R / "calibration_pooled.csv")
    conf = pd.read_csv(R / "conformal_scaffold.csv")
    sel = pd.read_csv(R / "selective.csv") if (R / "selective.csv").exists() else None

    lines = ["# P2：骨架位移下的校准、覆盖与选择性预测", ""]
    lines += ["设置：主表沿用常见做法——valid 同时用于 early stopping 与 conformal 校准，test 作为评估集；",
              "α=0.10；概率为种子集成平均。2b 用 test 内的独立划分隔离该协议的偏差。", ""]

    lines += ["## 1. 事后校准（test）", "",
              "ΔECE 为相对 raw 的配对 bootstrap（2000 次，按化合物重采样），括号内为 95% CI。", "",
              "| 端点 | 模型 | n | raw ECE | temperature | Platt | isotonic | ΔECE (Platt) [95% CI] |",
              "|---|---|---|---|---|---|---|---|"]
    for (ep, model), g in cal.groupby(["endpoint", "model"], sort=False):
        row = {r["calibrator"]: r for _, r in g.iterrows()}
        p = row.get("platt")
        lo, hi = (p["d_ece_lo"], p["d_ece_hi"]) if p is not None else (float("nan"), float("nan"))
        lines.append(
            f"| {ep} | {model} | {int(g['n'].iloc[0])} | {f(row['raw']['ece'])} | "
            f"{f(row['temperature']['ece'])} | {f(row['platt']['ece'])} | {f(row.get('isotonic', {}).get('ece', float('nan')))} | "
            f"{f(p['d_ece_vs_raw'])} [{f(lo)}, {f(hi)}] |"
        )
    lines.append("")

    gap_path0 = R / "valid_test_gap.csv"
    if gap_path0.exists():
        g0 = pd.read_csv(gap_path0)
        if {"frac_gt90_test", "base_rate_test"}.issubset(g0.columns):
            a = g0[g0.endpoint == "ames"]
            if len(a):
                txt = "、".join(f"{r['model']} {f(r['frac_gt90_test'], 2)}" for _, r in a.iterrows())
                lines += [f"Ames 上测试预测 >0.9 的比例：{txt}（基准阳性率 {f(a['base_rate_test'].iloc[0], 2)}）；"
                          "CheMeleon 的 ECE 劣势主要来自极端分箱的过度自信，而平均预测概率与基准率接近。", ""]

    lines += ["### 合并（按端点分层 bootstrap）", "",
              "| 模型 | n | raw | temperature | Platt | isotonic | ΔECE (Platt) [95% CI] |",
              "|---|---|---|---|---|---|---|"]
    for model, g in pooled.groupby("model", sort=False):
        row = {r["calibrator"]: r for _, r in g.iterrows()}
        p = row["platt"]
        lines.append(
            f"| {model} | {int(g['n_pooled'].iloc[0])} | {f(row['raw']['ece_pooled'])} | "
            f"{f(row['temperature']['ece_pooled'])} | {f(p['ece_pooled'])} | {f(row['isotonic']['ece_pooled'])} | "
            f"{f(p['d_ece_pooled'])} [{f(p['d_ece_lo'])}, {f(p['d_ece_hi'])}] |"
        )
    lines.append("")

    lines += ["## 2. Conformal 覆盖（α=0.10，名义覆盖 0.90）", "",
              "| 端点 | 模型 | n_test | 标准 [95% CI] | 骨架簇 Mondrian | 相似度加权 | 新颖度分箱 | 集成分歧归一化 | 组合归一化 |",
              "|---|---|---|---|---|---|---|---|---|"]
    order = ["standard", "cluster", "swc", "difficulty", "norm_sigma", "norm_combo"]
    for (ep, model), g in conf[(conf.calibration == "raw")].groupby(["endpoint", "model"], sort=False):
        row = {r["conformal"]: r for _, r in g.iterrows()}
        cells = []
        for k in order:
            if k in row and pd.notna(row[k]["coverage"]):
                txt = f"{f(row[k]['coverage'])} ({f(row[k]['set_size'])})"
                if k == "standard":
                    n = int(row[k]["n_test"])
                    lo, hi = wilson(round(row[k]["coverage"] * n), n)
                    txt = f"{f(row[k]['coverage'])} [{f(lo)}, {f(hi)}] ({f(row[k]['set_size'])})"
                cells.append(txt)
            else:
                cells.append("–")
        lines.append(f"| {ep} | {model} | {int(g['n_test'].iloc[0])} | " + " | ".join(cells) + " |")
    lines.append("")
    lines += ["括号内为平均预测集大小。Ames（n=732）上标准 conformal 的 95% CI 不含 0.90，属于确定的覆盖不足；",
              "hERG（n=59）与 DILI（n=51）的 CI 很宽，无法区分。骨架分组/加权/归一化变体在 44–62 个校准点下",
              "均未稳定改善覆盖，部分变体（相似度加权、组合归一化）反而更低。失效来源见 2b。", ""]

    cl = conf[(conf.calibration == "raw") & (conf.conformal == "cluster")]
    lines += ["### 骨架簇层面的覆盖异质性", "",
              "| 端点 | 模型 | 测试簇数 | 边际覆盖 | 最差簇 | 最好簇 | 加权 MAD |",
              "|---|---|---|---|---|---|---|"]
    for _, r in cl.iterrows():
        lines.append(
            f"| {r['endpoint']} | {r['model']} | {int(r['n_clusters_test'])} | {f(r['coverage'])} | "
            f"{f(r['min_cluster_coverage'])} | {f(r['max_cluster_coverage'])} | {f(r['cluster_coverage_mad'])} |"
        )
    lines.append("")
    lines += ["仅统计 ≥10 个测试点的簇。Ames 的边际覆盖掩盖了明显的簇间差异，"
              "说明单一边际覆盖率不足以描述骨架位移下的可靠性。", ""]

    ho_path = R / "conformal_holdout.csv"
    gap_path = R / "valid_test_gap.csv"
    if ho_path.exists() and gap_path.exists():
        ho = pd.read_csv(ho_path)
        gap = pd.read_csv(gap_path)
        lines += ["### 2b. 覆盖失效的来源：校准集与评估集是否可交换", "",
                  "在 test 内部重复 200 次 50/50 划分：随机划分满足可交换性（conformal 理论上应达名义覆盖），"
                  "骨架分组划分模拟部署位移；最后一列为原协议（valid 作校准、test 作评估）。", "",
                  "| 端点 | 模型 | n_test | 随机 50/50 | 骨架分组 50/50 | valid→test |", "|---|---|---|---|---|---|"]
        for (ep, model), g in ho.groupby(["endpoint", "model"], sort=False):
            r = {x["scheme"]: x for _, x in g.iterrows()}
            def cell(k):
                if k not in r:
                    return "–"
                x = r[k]
                txt = f"{f(x['coverage'])}"
                if pd.notna(x.get("coverage_lo")):
                    txt += f" [{f(x['coverage_lo'])}, {f(x['coverage_hi'])}]"
                return f"{txt} ({f(x['set_size'])})"
            lines.append(f"| {ep} | {model} | {int(g['n_test'].iloc[0])} | {cell('random50')} | "
                         f"{cell('scaffold50')} | {cell('valid_to_test')} |")
        lines.append("")
        lines += ["随机与骨架分组划分下覆盖均回到名义水平（Ames 0.901/0.896），说明实现正确、"
                  "骨架位移本身并未破坏边际覆盖；而 valid→test 显著偏低（0.848）。原因见下表的模型选择乐观偏差：", "",
                  "| 端点 | 模型 | valid AUC | test AUC | ΔAUC | valid Brier | test Brier |",
                  "|---|---|---|---|---|---|---|"]
        for _, r in gap.iterrows():
            lines.append(f"| {r['endpoint']} | {r['model']} | {f(r['auc_valid'])} | {f(r['auc_test'])} | "
                         f"{f(r['auc_valid'] - r['auc_test'])} | {f(r['brier_valid'])} | {f(r['brier_test'])} |")
        lines += ["", "valid 同时用于 early stopping，其上的 conformity score 系统性偏小，"
                      "导致 q 偏小、test 覆盖不足。这是**校准协议问题**，不是 conformal 在位移下失效。", ""]

        mon_path = R / "conformal_mondrian_holdout.csv"
        if mon_path.exists():
            mon = pd.read_csv(mon_path)
            lines += ["### 2c. 骨架条件校准的可达性（Ames）", "",
                      "在校准/评估可交换的骨架分组划分下，比较标准 conformal 与 Butina 簇 Mondrian：", "",
                      "| 模型 | 校准簇数 | ≥25 点的簇 | 命中大簇的测试比例 | 标准覆盖 | Mondrian 覆盖 | Δ覆盖 [95% CI] | Δ最差簇覆盖 | Δ集合大小 |",
                      "|---|---|---|---|---|---|---|---|---|"]
            for _, r in mon.iterrows():
                lines.append(
                    f"| {r['model']} | {f(r['n_clusters'], 0)} | {f(r['n_large_clusters'], 1)} | "
                    f"{f(r['frac_eval_large'])} | {f(r['cov_std'])} | {f(r['cov_mon'])} | "
                    f"{f(r['d_cov_mon'])} [{f(r['d_cov_mon_lo'])}, {f(r['d_cov_mon_hi'])}] | "
                    f"{f(r['d_min_mon'])} | {f(r['d_size_mon'])} |"
                )
            lines += ["", "366 个校准点被 153 个骨架簇摊薄，仅约 2 个簇达到 25 点，且只有约 17% 的测试点能命中这些簇；"
                          "Mondrian 退化为全局 conformal，覆盖与最差簇覆盖均无改善。"
                          "这说明在当前数据规模下，簇条件覆盖在统计上不可达，而非加权方式选择不当。", ""]

    if sel is not None:
        lines += ["## 3. 选择性预测（弃权分数）", "",
                  "AURC 越低越好；Δ 为相对置信度弃权的配对 bootstrap 差值与 95% CI（负值表示更好）。", "",
                  "| 端点 | 模型 | 置信度 | 集成分歧 | 新颖度 | 组合 | Δ(集成分歧) | Δ(新颖度) |",
                  "|---|---|---|---|---|---|---|---|"]
        for (ep, model), g in sel.groupby(["endpoint", "model"], sort=False):
            row = {r["score"]: r for _, r in g.iterrows()}
            def dci(k):
                r = row.get(f"delta_{k}")
                return f"{f(r['aurc'])} [{f(r['risk_at_80'])}, {f(r['risk_at_90'])}]" if r is not None else "–"
            lines.append(
                f"| {ep} | {model} | {f(row['confidence']['aurc'])} | {f(row['neg_sigma']['aurc'])} | "
                f"{f(row['neg_novelty']['aurc'])} | {f(row['combo']['aurc'])} | "
                f"{dci('neg_sigma')} | {dci('neg_novelty')} |"
            )
        lines.append("")
        lines += ["置信度弃权在多数端点上仍是最优或接近最优；骨架新颖度与集成分歧只在个别端点（DILI/scratch）上更好，"
                  "且差值 CI 多数跨 0。因此没有证据支持用骨架新颖度替代模型置信度做弃权。", ""]

    lines += ["## 4. 结论与限制", "",
              "1. 事后校准（temperature/Platt）在样本量充足的 Ames 上显著降低 ECE，且不改变排序（AUC 不变）；在 hERG/DILI 上 95% CI 跨 0，无法区分。",
              "2. 校准集仅 44–62 个点时，isotonic/β 校准不稳定，不建议在小验证集上使用高自由度校准器。",
              "3. split conformal 在 test 内部可交换划分下达到名义覆盖（Ames 0.901/0.896），实现正确；"
              "**覆盖失效来自把 early-stopping 用的 valid 同时当作校准集**（Ames 0.848，valid AUC 0.908 vs test 0.827）。",
              "4. 骨架簇条件校准在当前数据规模下不可达：366 个校准点/153 个簇，仅 2 个簇 ≥25 点；Mondrian 退化，覆盖与最差簇覆盖无改善。",
              "5. 因此本文不宣称新的 conformal 算法；贡献在于**诊断校准协议**：报告覆盖失效来源、簇条件覆盖异质性与集合大小，"
              "并建议为 conformal 单独留出未被模型选择污染的校准集。", ""]
    (R / "p2_calibration.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
