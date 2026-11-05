> 公开聚合副本：本机路径已移除；未分发证据明确保留为本地可见，不冒称公开可复核或独立审核批准。原始审计记录未改写。

# 统计与校准审计更新

本轮为获用户授权的探索性实验，已跳过等待独立审核人，未取得独立批准。原始资料与 main 未改动。源标签语义和新增外部数据准入未闭环处继续 UNVERIFIED/BLOCKED；不得作为已批准正式评价。

分析定义见 protocol/STATISTICAL_ANALYSIS_PLAN.md。新神经统计只消费evaluation_fp32；643个图模型、39个Transformer及60个候选状态已另进程逐位回放。原BF16数值链仍BLOCKED，epoch原选择过程保留且不声称完整训练逐位重复。主要比较族为三端点×三对照；低数据为四样本量×三对照。区间条件于冻结模型与固定来源池，不等于总体部署保证。ensemble AUROC、seed-mean AUROC、AP、梯形PR-AUC、MCC、Brier、ECE分列。

### S01 · P1 · RECOMPUTED_NEW_RESULTS

- **问题位置**：paper/sections/00_abstract.tex:2（本地证据，未随公开包分发）
- **原始陈述**：hERG gap ... +0.120 ... but +0.104 under scaffold resampling
- **实际证据**：原审计：同一冻结 ensemble 的原始 ΔAUC=0.1204481793；scaffold bootstrap Δ 的均值=0.1036888891。32_robustness.contrast 的 delta 字段返回 d.mean()。抽样层级应改变区间/尾部统计，不能把该均值写成原始点估计变化。ChemBERTa Ames 的 +0.042 亦混入重采样均值；原始 ensemble Δ应按冻结概率直接计算。 本轮：新结果从保存概率计算；point estimate 与 bootstrap mean 分列。 证据：paired_graph_contrasts.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：统一使用 observed delta；另列 bootstrap mean/bias。保留现有历史结果文件，不覆盖。
- **所需实验或资料**：原缺口：更新分析输出 schema 和所有摘要、Table1/容量表/正文；无须新训练。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：核心结果表达 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S02 · P1 · ESTIMANDS_SEPARATED

- **问题位置**：paper/tables/t2_compact.tex:5（本地证据，未随公开包分发）
- **原始陈述**：Rows are seed means ... paired contrasts use seed-ensemble probabilities.
- **实际证据**：原审计：该表注在AUC与paired contrast之间明确区分estimand；但ChemBERTa的AP例外见S09。hERG CheMeleon/Matched seed mean 为0.881419/0.752101，而 ensemble 为0.890756/0.770308。第二 DILI seed mean 的差为正，但 ensemble 差约−0.010870；Ames 第二划分 seed-mean 差约0.028717，而 ensemble约0.014690。正文交替使用仍易误读。 本轮：seed-mean和ensemble分开保存；单划分配对bootstrap以固定ensemble为对象，主跨划分效应以per-seed差为对象，不能互换。 证据：[joint_group_seed_bootstrap.csv](../evidence/reports/joint_group_seed_bootstrap.csv)。
- **严重等级**：P1
- **建议修复**：每个差值显式标记 seed-mean delta、ensemble observed delta；训练随机性与测试抽样误差分开报告。
- **所需实验或资料**：原缺口：分层 estimand 说明、逐 seed 指标与 ensemble 对照表。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：否：可由现工件澄清 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S03 · P1 · GROUP_RESAMPLING_SCOPE_LIMITED

- **问题位置**：paper/sections/03_data.tex:16（本地证据，未随公开包分发）
- **原始陈述**：Murcko scaffold groups, the exchangeable unit when deploying to novel scaffolds
- **实际证据**：原审计：32_robustness 按唯一 scaffold_key 有放回抽 G 个组，保留组内全部成员，指标为 compound-weighted AUROC；两模型共享同一抽样。18 个 capacity bootstrap 结果与冻结文件完全相同。该实现不能证明真实新 scaffold 分布下簇可交换，亦不包含训练/校准/划分随机性。 本轮：compound 与联合分组 bootstrap 分开；重采分组本身不创造部署exchangeability，也未纳入重新抽训练数据的全部变异。 证据：paired_graph_contrasts.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：称为“假设簇可交换时的 cluster bootstrap 敏感性推断”；报告有效抽样数、单类丢弃数及簇大小，不把区间当部署保证。
- **所需实验或资料**：原缺口：统计目标与采样假设、层级不确定性方案。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：若保留部署可交换性断言 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S04 · P1 · NEW_MULTIPLICITY_REPORTED

- **问题位置**：paper/sections/03_data.tex:16（本地证据，未随公开包分发）
- **原始陈述**：BH q-values and Bonferroni-adjusted p-values within each family
- **实际证据**：原审计：capacity 每层9检验、classical 每层3检验的 BH/Bonferroni 实现正确。dropout、LR、长预算、暴露子集、ChemBERTa、低数据及校准比较未统一纳入同一确认性族；若挑显著子集作主结论会形成选择性推断。普通 bootstrap尾部比例不是严格零假设随机化检验；5000次尾部为0不代表p=0。 本轮：近似中心化 bootstrap p 有限 Monte Carlo 校正；BH/Bonferroni 比较族显式记录，重叠划分不作为独立研究。 证据：[joint_group_seed_bootstrap.csv](../evidence/reports/joint_group_seed_bootstrap.csv)。
- **严重等级**：P1
- **建议修复**：区分预先定义的确认性族与探索性结果；披露未校正值，给尾部有限分辨率；必要时使用经验证的检验设计。
- **所需实验或资料**：原缺口：预先锁定族、主指标/端点、层级 gatekeeping 与统计分析计划。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：确认性显著性主张 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S05 · P1 · EQUIVALENCE_CLAIM_WITHDRAWN

- **问题位置**：paper/sections/03_data.tex:16（本地证据，未随公开包分发）
- **原始陈述**：±0.06 AUC margin—half the hERG point estimate
- **实际证据**：原审计：TOST 实现为同一 bootstrap 的90% percentile interval 是否落在(−.06,.06)，并输出尾部 max；DILI仅 compound 通过，Ames两层通过，已复核。边界由观察到的 hERG 差值反推，未有领域依据；不能据此证明实用等效或“容量解释了一切”。 本轮：四个边界只作探索性敏感性，不将不显著写成实际等效。 证据：equivalence_margin_sensitivity.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：将现结果改为事后、条件性的 equivalence sensitivity；预先论证端点相关最小实用差异，明确多重等效检验处理。
- **所需实验或资料**：原缺口：领域可接受误差/决策损失依据、事前边界与功效方案；不能事后更换边界直到显著。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：正式等效结论 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S06 · P1 · NEW_LOW_DATA_HIERARCHY_COMPLETE_OLD_P_UNVERIFIED

- **问题位置**：paper/sections/05_lowdata.tex:13（本地证据，未随公开包分发）
- **原始陈述**：fixed-capacity advantage is significant only at n=400 (p=0.04)
- **实际证据**：原审计：48 条低数据冻结预测已逐一复算。未发现对应低数据 p 值的冻结检验脚本/结果表。诊断性 paired t-test 可产生 n200≈.33、n400≈.037/.041，但 n50对matched≈.042、对dropout≈.0075，说明“only”取决于未说明方法/比较。只有3个采样与训练共用 seed，正态近似无法可靠检验；未校正多 n/模型比较。 本轮：5 抽样 × 3 训练种子，与测试分组共同重采样；历史缺脚本 p 值不因此获验证。 证据：[lowdata_joint_sampling_training_test_bootstrap.csv](../evidence/reports/lowdata_joint_sampling_training_test_bootstrap.csv)。
- **严重等级**：P1
- **建议修复**：删除“only significant”和未经定义的p；先保留均值/SD曲线；若追溯原检验，写出配对单位、统计量、假设和完整检验族。
- **所需实验或资料**：原缺口：原始检验命令/脚本/统计方案；未来将 subsample seed 与 training seed 解耦。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：低数据显著性 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S07 · P1 · PRECISION_DIAGNOSTICS_NOT_ADEQUATE_POWER_PROOF

- **问题位置**：paper/sections/90_appendix.tex:5（本地证据，未随公开包分发）
- **原始陈述**：the second null is not a power artefact
- **实际证据**：原审计：第二 hERG gap确实很小，但不显著不能排除低功效；两次不同测试人群的模型变化不能识别差异原因。MDE≈.21由 bootstrap SD×(z.975+z.80) 得到，是当前数据下正态近似诊断，不是对既定真实效应的事前功效证明。 本轮：保留全部区间及条件性正态位置近似MDE诊断；不能据此断言第二划分null不是功效问题。 证据：power_resolution_diagnostic.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：改为“点估计对划分敏感；当前证据不能区分效果异质性与采样/优化不确定性”；upper bound 改 observed contrast，不称严格上界。
- **所需实验或资料**：原缺口：独立多划分、多训练种子、预先给定真实效应/簇数的模拟功效设计。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：若保留排除功效/严格上界措辞 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S08 · P1 · NEW_TABLES_TRACEABLE_OLD_UNSUPPORTED_P_NOT_REUSED

- **问题位置**：scripts/21_make_tables.py:87（本地证据，未随公开包分发）
- **原始陈述**：Generate paper tables / Test-set AUC (ECE)
- **实际证据**：原审计：当前 Table2为9模型的AUC(PR-AUC)；脚本只生成4模型AUC(ECE)，容量表也仍用旧2000次compound bootstrap。运行将覆盖正式tex。现有6个table文件仅t1/t2在main路径被引用，三个figure文件仅fig3在正文出现（PDF中编号Fig1）。22_check_paper只做静态引用检查，不能验证数值或输出身份。 本轮：本轮完整脚本/概率/比较族保存；新表从指定CSV生成，历史无法定位的次级结果继续 UNVERIFIED。 证据：global_seed_mean_table.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：另建版本化、纯输出到新目录的表图生成流程，明确included/orphan工件；锁定artifact→cell/curve→latex→PDF清单。
- **所需实验或资料**：原缺口：当前稿件的真实生成命令与构建记录；全部主文/附录数字清单，生成后比较，不覆盖历史稿件。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：一键论文复现 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### S09 · P1 · ESTIMANDS_SEPARATED

- **问题位置**：paper/tables/t2_compact.tex:18（本地证据，未随公开包分发）
- **原始陈述**：Rows are seed means / ChemBERTa 0.773 (0.893)
- **实际证据**：原审计：主表54个AUC/AP单元中45个符合逐seed均值；9个不符全部为ChemBERTa三臂×三端点AP。它们逐项等于ensemble AP，而同一单元外侧AUC用seed-mean。例：hERG小scratch写0.760(0.924)，实际mean AUC=.760037、mean AP=.879983、ensemble AP=.923679。数值本身可从预测复算，但表内估计量混用，与caption冲突。 本轮：seed-mean 与 ensemble 指标分列；AP 不混称梯形 PR-AUC。 证据：[chemberta_ensemble_metrics.csv](../evidence/reports/chemberta_ensemble_metrics.csv)。
- **严重等级**：P1
- **建议修复**：统一整行AUC/AP估计量；可同时给seed mean与ensemble，但必须分列并更新caption，保留旧表为历史版本。
- **所需实验或资料**：原缺口：用冻结概率生成逐seed/ensemble双口径表与自动单元核对，无须训练。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：主表指标口径 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C01 · P1 · FACTORIAL_DIAGNOSTIC_COMPLETE_CAUSAL_SCOPE_LIMITED

- **问题位置**：paper/sections/08_discussion.tex:6（本地证据，未随公开包分发）
- **原始陈述**：The calibration failure is distributional, not merely procedural ... because ... easier than test
- **实际证据**：原审计：主valid→test .848、独立calib→test .843（α.2为.702）、第二split .931均可从预测复算。已有干净fit/es/calib/test部署模型，不应当作尚不存在。原模型与干净模型的训练样本、早停集、权重不同；同模型es与calib样本/难度亦不同。AUC差和覆盖差不能分离早停复用、分布偏移、校准样本量与训练变化的因果作用。 本轮：固定轨迹、等规模随机 pool 分配比较复用；域差异仍为观察，不证明全部失配原因。 证据：[calibration_factorial_summary.csv](../evidence/reports/calibration_factorial_summary.csv)。
- **严重等级**：P1
- **建议修复**：保留观测事实，改为“clean holdout did not restore nominal coverage in this partition; compatible with score distribution differences, without identifying their cause.”
- **所需实验或资料**：原缺口：固定训练池与模型、控制校准规模/抽样难度的复用×shift设计；同时报告分布诊断和不确定性。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：机制归因；数值不必删除 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C02 · P2 · NEW_QUANTILE_BOUNDARY_FIXED

- **问题位置**：scripts/11_conformal_scaffold.py:111（本地证据，未随公开包分发）
- **原始陈述**：k = min(ceil((n+1)(1−alpha)), n)
- **实际证据**：原审计：score=1−p(true class)，集合使用≤q+1e−12，当前样本规模α=.1/.2的分位数可复算。若k>n，代码截到最大分数，理论安全定义应取+∞；对现主结果未观察到此分支影响。正文“below”应写inclusive；least-probable-label名称应明确为候选真实标签的概率型score（LAC）。 本轮：第 ceil((n+1)(1-alpha)) 顺序统计；超出 n 取 +infinity，使用 inclusive <=。 证据：postcalibration_cp_metrics.csv（本地证据，未随公开包分发）。
- **严重等级**：P2
- **建议修复**：下一阶段修正边界分支、空calibration与α合法性，记录≤和ties；不要声称所有规模皆有保证。
- **所需实验或资料**：原缺口：最小n/极端α/ties边界验证；无需训练。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：否：当前数值；是：通用有效性保证 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C03 · P1 · CALIBRATION_AND_TEST_UNCERTAINTY_RECOMPUTED

- **问题位置**：scripts/42_conformal_cluster_ci.py:53（本地证据，未随公开包分发）
- **原始陈述**：coverage ... scaffold-cluster bootstrap
- **实际证据**：原审计：性能bootstrap用scaffold_key，主校准CI/50-50使用raw murcko，把所有无环分子合成一个ACYCLIC簇；第二split和clean deployment用scaffold_key。Ames测试的两种簇数见补充证据。50/50的95%区间是同一test反复拆分的覆盖分布，不是200次独立外部实验均值的CI。Wilson把命中近似当独立Bernoulli；cluster CI固定模型和校准阈值，未纳入校准采样不确定性。 本轮：同时重采 calibration/test 联合分组；条件于已拟合模型与概率变换，不含重训练或变换拟合全部不确定性。 证据：[coverage_calibration_and_test_uncertainty.csv](../evidence/reports/coverage_calibration_and_test_uncertainty.csv)。
- **严重等级**：P1
- **建议修复**：统一簇定义或明确并列敏感性；区分 Wilson、conditional cluster CI、重复拆分分布；不可将200次重复当独立样本。
- **所需实验或资料**：原缺口：校准集与测试簇共同重采样/分层方案；披露簇大小及有效独立单位。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：如果现区间被当无条件部署保证 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C04 · P1 · FIXED_CLASS_AND_CHEMICAL_PARTITION_DIAGNOSTICS_COMPLETE

- **问题位置**：paper/sections/06_calibration.tex:17（本地证据，未随公开包分发）
- **原始陈述**：cluster-conditional coverage is out of reach at current data sizes
- **实际证据**：原审计：19_mondrian_holdout 在校准集建立Butina簇，测试点分到最近校准成员的簇，少于25点退回全局。实现把1−Tanimoto传入Butina，cutoff=.4是距离（相似度≥.6），正文“Tanimoto0.4”有歧义/不符。特定实现和阈值不足以证明所有cluster-conditional方法不可达，也未建立固定分区的Mondrian理论条件。现输出未系统给出空集率与类条件coverage。 本轮：训练集独自冻结10个化学簇，并列global/class-Mondrian；稀疏单元严格+infinity，报告支持量、类覆盖、空集和全集率，不宣称所有条件方法不可达。 证据：mondrian_fixed_partition_metrics.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：改为“under the chosen clustering/minimum-size rule few clusters support separate calibration”；汇报退回率和子群计数。
- **所需实验或资料**：原缺口：用训练/独立数据冻结分区，明确class/cluster coverage estimand；空集、singleton、全集率与区间。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：普遍不可达结论；否：受限描述 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C05 · P1 · GUARANTEE_SCOPE_NARROWED

- **问题位置**：paper/sections/02_related.tex:6（本地证据，未随公开包分发）
- **原始陈述**：calibrating on the model-selection split ... breaks exchangeability regardless of distribution shift.
- **实际证据**：原审计：标准split-conformal固定score的独立校准条件通常不满足，但不能从复用本身推导每个具体模型必然欠覆盖；存在选择感知的有效性研究。Liang/Zhu/Barber 2026正式论文讨论特定选择规则，不能直接当作本项目AUROC早停机制的验证。 本轮：随机pool诊断与域差异解释分开；不把三条训练轨迹的重复拆分当独立证明。 证据：[calibration_factorial_summary.csv](../evidence/reports/calibration_factorial_summary.csv)。
- **严重等级**：P1
- **建议修复**：改为：Standard split-conformal guarantees do not directly apply when calibration observations influenced model selection, unless selection-aware validity conditions are established.
- **所需实验或资料**：原缺口：本轮同轨迹随机pool复用诊断已安排；若要求普遍保证，需针对具体选择算法的理论条件，观察性coverage不能替代理论。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是，若保留普遍必然破坏/欠覆盖论断 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C06 · P2 · LEGACY_VALUES_RECOMPUTED_DEFINITION_LIMITED

- **问题位置**：scripts/11_conformal_scaffold.py:279（本地证据，未随公开包分发）; paper/sections/06_calibration.tex:14（本地证据，未随公开包分发）
- **原始陈述**：Ames AURC 0.142 versus 0.171/0.246; hERG 0.082 versus 0.230/0.176
- **实际证据**：原审计：24个历史AURC点值和18个原500-draw区间均从冻结概率/源码复算，最大误差0。定义实际只平均k=20..n的累计风险；hERG起始20/59、DILI20/51、Ames20/732，非统一完整coverage范围。ties用原始顺序stable打破。 本轮：旧24点/18区间精确复现；新定义结果单独保存，避免混表。 证据：historical_selective_recomputed.csv（本地证据，未随公开包分发）。
- **严重等级**：P2
- **建议修复**：保留可复算数字但说明截断区间、离散求均值、ties及原500次compound条件区间；新实验另报k=1..n完整离散AURC，ties按均匀排序期望处理。
- **所需实验或资料**：原缺口：本轮全量risk-coverage/各固定scorer对照、compound和联合分组5000次条件区间；不能用test挑最优scorer后作确认性结论。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：投稿前必须澄清指标定义；不因此否定同端点相同范围内的描述排序 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### N01 · P0 · CANONICAL_FP32_COMPLETE_RAW_BF16_BLOCKED

- **问题位置**：本轮scripts/train_graph.py原BF16推理路径、runs/原始预测；protocol/EVALUATION_PRECISION_AMENDMENT.json；reports/pilot_weight_replay.json
- **原始陈述**：原执行计划假设冻结权重可在数值容差内重放其BF16预测；此假设未通过完整回放前不应写成已验证。
- **实际证据**：原审计：两份预先指定checkpoint重复前向：hERG最大相邻概率差0.00390625、AUROC差0.004201680672268893；Ames最大相邻概率差0.015625。BF16与FP32启用确定性算法的预检查均可稳定，不能归因于单一kernel或dtype。原BF16确定性复现链标记BLOCKED并完整保留。 本轮：643图模型、39个Transformer及60个候选状态已生成确定性FP32预测并双前向检查；另进程1841个预测角色的float32概率全部逐位一致，见canonical_inference_complete.json和weight_replay_progress.json。10个FP32训练对照完成；hERG3个配对seed，DILI/Ames各1个seed，后两者只作描述。来源工厂哈希不变。 全矩阵政策漂移：BF16到canonical最大概率差0.065715970；test AUROC差范围[-0.046918768, 0.145370370]。它与重复BF16前向差的口径不同；独立sklearn核对支持最大AUROC漂移案例。 证据：NUMERICAL_REPRODUCIBILITY_AMENDMENT.md（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：显式披露数值政策修订；新神经统计统一使用evaluation_fp32，原BF16预测仅作诊断。保留原epoch选择与训练记录，不把canonical回放写成原训练轨迹逐位重复；全部10个训练政策对照逐项报告，不按test选择政策。
- **所需实验或资料**：原缺口：修复固定权重数值链所需的全矩阵canonical双前向与另进程回放已完成。若声称完整训练逐位可复现，仍需在固定环境重跑训练轨迹；若声称dtype独立因果效应，需分离dtype与确定性reduction的干预设计。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：原BF16预测的确定性复现声明仍BLOCKED；可使用经验证的canonical版本并披露修订。数据来源/标签准入限制独立保留。 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### M04 · P1 · HISTORICAL_TEST_SELECTION_DETECTED_NEW_FIXED_COMPARISONS

- **问题位置**：scripts/16_vs_classical.py:71（本地证据，未随公开包分发）; paper/sections/04_benchmark.tex:9（本地证据，未随公开包分发）
- **原始陈述**：best_name = max(klass, key=lambda k: roc_auc_score(ys, klass[k])) / strongest classical baseline
- **实际证据**：原审计：历史脚本在test选择RF/HistGB/LogReg中的最高AUC，再对被选基线作配对统计。新做9个明确历史配置的数值重建，使用冻结旧报告中的比较身份，不重新按test选胜者。数字接近或复现不使选择后推断自动有效。 本轮：历史配置重建与新五套修复划分的固定基线比较分开。 证据：historical_classical_numeric_replay.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：将旧strongest比较限定为探索性、说明test选择；新实验逐个报告全部固定基线，不用test决定报告哪个算法。如需选择器，必须在selection冻结。
- **所需实验或资料**：原缺口：本轮105传统模型和全比较已安排；历史原始classical权重/概率未保存，精确旧预测仍有UNVERIFIED。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是，若保留旧比较作为未经选择的确认性推断 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。
