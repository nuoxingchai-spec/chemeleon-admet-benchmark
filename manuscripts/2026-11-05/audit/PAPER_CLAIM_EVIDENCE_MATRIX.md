> 公开聚合副本：本机路径已移除；未分发证据明确保留为本地可见，不冒称公开可复核或独立审核批准。原始审计记录未改写。

# 结论—证据矩阵

本轮为获用户授权的探索性实验，已跳过等待独立审核人，未取得独立批准。原始资料与 main 未改动。源标签语义和新增外部数据准入未闭环处继续 UNVERIFIED/BLOCKED；不得作为已批准正式评价。

新神经数值均来自另存的确定性FP32预测及固定权重；原BF16结果仅作数值诊断，见N01。历史数值沿用阶段1/2复算，二者不混表。主效应见 joint_group_seed_bootstrap.csv，完整指标见 all_graph_seed_metrics.csv；不将新实验用于追认旧的不可复现 p 值。

历史逐数值索引另见288项结论/数值证据登记（本地证据，未随公开包分发）、阶段1完整结论矩阵（本地证据，未随公开包分发）及表2逐单元核对（本地证据，未随公开包分发）。这些是历史证据，旧文件中的待审核状态未被改写；本轮用户已豁免等待审核人，但来源/标签缺口仍单独列出。新结果以本轮canonical版本为准。

### M01 · P0 · RECOMPUTED_EXPLORATORY

- **问题位置**：paper/sections/04_benchmark.tex:12（本地证据，未随公开包分发）
- **原始陈述**：The matched control isolates pretraining from architecture.
- **实际证据**：原审计：runs/chemprop/herg_chemeleon_s42/train.log:62（本地证据，未随公开包分发） 与 runs/chemprop/herg_matched_s42/train.log:53（本地证据，未随公开包分发） 显示实际聚合算子不同。安装的 Chemprop 2.3.1 在 from-foundation 分支强制 mean，随机初始化分支默认 norm=100；mean 为 Σh/原子数，norm 为 Σh/100，是分子大小相关变换，并非固定常数缩放。主矩阵、第二划分与 LR 对照日志均可见此差异。参数量相同不足以隔离初始化收益。 本轮：同 MeanAggregation、同头种子、同优化的 matched encoder 重评完成；旧实验混杂仍如实保留。 证据：[joint_group_seed_bootstrap.csv](../evidence/reports/joint_group_seed_bootstrap.csv)。
- **严重等级**：P0
- **建议修复**：保留历史实验为“参数量匹配但聚合方式不同”的敏感性结果；删除纯权重收益/容量已隔离的归因。
- **所需实验或资料**：原缺口：获准后固定同一计算图、mean aggregation、特征器、头部及优化预算；只切换 encoder 权重。先审结构签名，再训练。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：核心容量归因 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D01 · P0 · FILE_IDENTITY_RESOLVED_LABELS_NOT_APPROVED

- **问题位置**：paper/sections/03_data.tex:5（本地证据，未随公开包分发）
- **原始陈述**：identical to the TDC hERG collection (InChIKey coverage 1.00)
- **实际证据**：原审计：本地 SI 与本地 TDC 均 655 行/615 个键；按结构组的标签集合相同，不能解释为所有实验记录一一相同。未去重直接连接产生 735 对，其中 18 对标签不一致，来自冲突组的多对多展开，不证明 TDC 反转标签。官方 hERG 说明为 648，vendor 元数据亦为 648。SI 官方下载文件哈希、TDC 快照版本/下载响应未找到。vendor/pytdc-1.1.15/tdc/metadata.py:1248（本地证据，未随公开包分发） 本轮：官方 SI/TDC 身份已在阶段2核实；不得将文件身份等同原始实验语义批准。 证据：ORIGINAL_ARTIFACT_INTEGRITY.json（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：将“identical”改为本地快照结构覆盖与组级标签比较；给出 655→615→606 流程，单列官方 648 差异。
- **所需实验或资料**：原缺口：Wang DOI/SI 官方文件身份、TDC Dataverse file 4259588 的版本及校验和、下载日志；内部逐记录 join 与重复来源说明。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：hERG 来源身份 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D02 · P0 · INHERITED_CLASS_CONFIRMED_SOURCE_SEMANTICS_BLOCKED

- **问题位置**：README.md:62（本地证据，未随公开包分发）
- **原始陈述**：标签阈值 pIC50 ≥ 4.41（约 40 µM）
- **实际证据**：原审计：训练实际直接使用 SI Class，不按 pIC50 生成主标签。655 行有 129 行缺失 pIC50；606 个保留结构有 123 个缺失。已测行中，4.4 与 Class 一致，4.41 有 2 行不一致；Class=1 最低 4.4000077，Class=0 最高 4.3819518。原始 pIC50=5 有 14 行。区分继承 Class 与推导阈值，不能用观测边界推定来源规则。scripts/00_audit.py:64（本地证据，未随公开包分发） 本轮：主标签继承Class而非按pIC50生成：655来源行有129个缺测，606保留结构有123个缺测；观测边界4.4一致不能证明原始定义。严格边界敏感性排除218个样本而未重标，仍不能补足缺测Class与多实验聚合出处。 证据：DERIVED_DATA_LINEAGE_VALIDATION.json（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：正文/README/manifest 统一说明“继承原始 Class；阈值依据待原文核验”；不要自动重标或丢掉缺失测量者。
- **所需实验或资料**：原缺口：原始端点定义、阈值严格/非严格关系、缺测者的标签出处、测量单位/删失符号与边界例外清单，独立审核。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：hERG 标签语义 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D03 · P0 · FILE_IDENTITY_RESOLVED_LABELS_NOT_APPROVED

- **问题位置**：paper/sections/03_data.tex:5（本地证据，未随公开包分发）
- **原始陈述**：DILI is the TDC ...; Ames is the TDC ...
- **实际证据**：原审计：从现有 .tab 重新标准化，DILI 475→474；Ames 7278→7248→7246（2 冲突组/4 行），与最终标签键集完全相符。官方说明 Ames=7255，DILI=475；源表的 endpoint→原始研究→实验记录映射和快照校验和缺失。代码重建成功只闭合本地处理链。 本轮：版本与文件校验已核实，上游逐 assay 标签链仍有 UNVERIFIED。 证据：ORIGINAL_ARTIFACT_INTEGRITY.json（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：补充 TDC 文件 ID、版本、下载时间、哈希与上游 Xu 2012/Xu 2015 引用；解释 Ames 23 行差异。
- **所需实验或资料**：原缺口：Dataverse 4259564/4259585 的版本记录；四个 Ames 原始来源与 DILI FDA/NCTR 标签定义、冲突政策、许可范围。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：正式标签/版本未闭环 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D04 · P1 · LOCAL_LINEAGE_RECONSTRUCTED

- **问题位置**：scripts/01_build_splits.py:47（本地证据，未随公开包分发）
- **原始陈述**：n_source_rows; p = g["pIC50"].median()
- **实际证据**：原审计：最终数据只保留来源条数、首个结构/原 Set 信息和测量中位数；未保存每个来源行的去向及删除原因。本轮内存关联确认三端点保留键集与标签无差异；hERG 保留组有 27 组多次测量、24 组有测量跨度，中位数与现工件一致。未完成原始实验级来源验证。 本轮：8408个原始来源行逐一关联到五套新划分，共42040行内部血缘映射；8326个最终端点样本的键、标签与结构未变，冲突删除行明确无最终样本。逐成员映射不对外公开。 证据：DERIVED_DATA_LINEAGE_VALIDATION.json（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：建立受控内部 lineage 表，保留全部原始行及测量，不改历史文件；对外仅经批准的聚合表。
- **所需实验或资料**：原缺口：source_file_sha256/sheet/row/record_id→结构转换→组ID→冲突/缺失原因→最终样本ID/划分；审核者、日期、适用合同。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：原始实验映射尚缺；内部文件映射可重建 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D05 · P0 · NEW_SPLITS_REPAIRED_NOT_HISTORICAL_OVERWRITE

- **问题位置**：paper/sections/03_data.tex:8（本地证据，未随公开包分发）
- **原始陈述**：are disjoint at compound and scaffold level.
- **实际证据**：原审计：按 full InChIKey 和现有 scaffold_key 确实不相交，重放划分算法 0 个分配差异。但 Ames 有 33 个 first-block connectivity 组跨 train/valid/test，共 66 个端点样本，其中 64 个为 acyclic；全局相应 68 个端点行。当前 acyclic 使用 full InChIKey 独立成组，立体变体可能跨集。hERG/DILI 各端点未查到该类跨集组。 本轮：五次新划分在全局 connectivity 与环状 Murcko 联合分组上互斥；历史划分原封保留。 证据：[joint_group_seed_bootstrap.csv](../evidence/reports/joint_group_seed_bootstrap.csv)。
- **严重等级**：P0
- **建议修复**：将无泄漏断言限定在已检验的键定义；把 Ames connectivity 跨集列为潜在泄漏，不能声称已证明其影响大小。
- **所需实验或资料**：原缺口：内部检查 33 组结构、标签、立体信息、互变异构与原始测量；获准后用统一 connectivity/系列分组新建划分并冻结，重评受影响结果。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：Ames 潜在结构泄漏 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D06 · P1 · NEW_SPLIT_RULE_EXPLICIT

- **问题位置**：paper/sections/90_appendix.tex:4（本地证据，未随公开包分发）
- **原始陈述**：We rebuild each partition with a different scaffold order
- **实际证据**：原审计：第二划分 hERG seed2027 使用标签加权分配，DILI2030/Ames2033 改为 size-only，并挑选类别率接近的 seed。三端点合并后有 66 个 full-key 组、101 个 scaffold_key 组跨集合；这些是逐端点单任务复验，不是第二个全局划分，不代表当前逐端点模型有直接标签泄漏。 本轮：五次新划分采用同一 size-only 分配算法、预定随机种子与联合分组；不冒称历史第二划分只改变 scaffold 顺序。 证据：locked_split_counts.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：明确算法与标签平衡筛选差异，限制为 endpoint-specific split sensitivity；禁止将此划分用于声称全局不相交的多任务实验。
- **所需实验或资料**：原缺口：预先冻结的全局多划分协议、全部候选 seeds/选择规则和 split-level 独立性说明。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：若保留全局重复验证的表述 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D07 · P0 · WAIT_WAIVED_APPROVAL_NOT_GRANTED

- **问题位置**：项目数据准入与历史记录
- **原始陈述**：All data are public ... / 自查通过
- **实际证据**：原审计：检索主目录及发布副本未找到独立标签审核签署件或已批准数据合同。README、p0_audit、发布方自查均是提交者记录，不等同第三方批准。本轮审计不签发数据准入许可。 本轮：用户跳过等待独立审核人；执行继续，不能把自查或授权训练写成独立批准。来源语义与合同范围仍须如实披露。 证据：EXPERIMENT_COMPLETION.json（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：建立 provenance、标签语义、许可与独立审核四项准入证据；保留历史数据不修改。
- **所需实验或资料**：原缺口：具身份和版本范围的独立审核记录；如已有合同，提供其身份及适用范围，不重写合同。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：正式评价准入 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### D08 · P0 · STRICT_BOUNDARY_SENSITIVITY_COMPLETE

- **问题位置**：scripts/10_external_prep.py:119（本地证据，未随公开包分发）
- **原始陈述**：positives at pIC50 ≥5 and negatives at ≤4.4
- **实际证据**：原审计：官方 TDC Karim 说明正类 <10 µM、负类 ≥10 µM；脚本采用 pIC50≥5，与严格 <10 µM 的边界不同。还对多次测量取中位数，并要求原 Class 与新区间同向。399 个对齐样本的产生可从本地规则追踪，不能据此证明 assay-level 对齐。manifest 又写“4.4089”，与代码和原始边界不一致。 本轮：新敏感性保留 Class=1且pIC50>5、Class=0且pIC50<=4.4；排除等于5、灰区与缺失，不重标历史样本。该筛选不补足未证实的上游标签语义。 证据：existing_external_sensitivity_metrics.csv（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：称为粗粒度阈值敏感性分析，核对严格/非严格边界；保留现工件，修订标签合同需单独批准。
- **所需实验或资料**：原缺口：原始 Karim 研究的端点、测定方式、IC50=10 µM 规则、删失和重复测量处理；本地 pIC50=5 的最终成员内部复核。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：正式外部阈值对齐主张 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### M02 · P1 · CONTROLLED_SENSITIVITY_COMPLETE

- **问题位置**：paper/sections/04_benchmark.tex:12（本地证据，未随公开包分发）
- **原始陈述**：Neither dropout nor budget explains it
- **实际证据**：原审计：hERG 主 CheMeleon best epoch 7/9/7；Matched 的 s42 为95，dropout s42为99。增加预算与 dropout 只覆盖部分优化条件，且聚合差异仍存在。LR sweep 的 CLI 只改 max-lr，init/final 仍为1e-4；它是峰值 LR/schedule 敏感性，不是三个恒定 LR。现有冻结概率给出约 +0.120/+0.083/−0.024 的 ensemble gap。 本轮：同预算、LR 全网格、长预算和聚合交互完成；仍不声称穷尽全部优化条件或已识别历史差距的唯一原因。 证据：[graph_equal_tuning_selected_metrics.csv](../evidence/reports/graph_equal_tuning_selected_metrics.csv)。
- **严重等级**：P1
- **建议修复**：报告训练曲线/实际更新数与完整 schedule；把“不能解释”改为“在这些设定下仍观察到差异”；不从 test 选择新最优 LR。
- **所需实验或资料**：原缺口：统一结构后在 train 内模型选择、相同搜索空间/预算和冻结 selection rule；未来测试集只做一次最终评估。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：若坚持优化已排除 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### M03 · P1 · PINNED_ARCHITECTURE_AND_SAVED_WEIGHTS

- **问题位置**：paper/sections/03_data.tex:13（本地证据，未随公开包分发）
- **原始陈述**：ChemBERTa ... 44,105,705 parameters
- **实际证据**：原审计：runs/chemberta 的 metrics.json 记录 pretrained/matched 参数量为44,104,705，比正文/表格少1000；代码未保存 ChemBERTa 模型权重/optimizer/checkpoint，HF MODEL 未 pin revision，缓存有两个 snapshots。实际预算由 shell/代码可读，但不能由唯一权重与环境重放推理。 本轮：ChemBERTa以固定snapshot/tokenizer、同种子分类头及匹配配置重评，实际参数量记录在各spec；大图完整模型参数9,329,241，旧9,329,247不沿用。 证据：[chemberta_ensemble_metrics.csv](../evidence/reports/chemberta_ensemble_metrics.csv)。
- **严重等级**：P1
- **建议修复**：先改为可审查的计数定义（trainable/total/encoder/head），核对实际 config/vocab；给训练工件完整性单独标记。
- **所需实验或资料**：原缺口：确切 HF commit、tokenizer/config/初始与微调权重哈希、完整命令、软件锁定与运行状态。若旧模型未保存，复现实验需获准重训。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：ChemBERTa 独立重放与精确匹配陈述 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

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

### E01 · P1 · RELEASED_CORPUS_REBUILT_CHECKPOINT_MEMBERSHIP_UNVERIFIED

- **问题位置**：scripts/44_pretrain_inchikeys.py:24（本地证据，未随公开包分发）
- **原始陈述**：Compute InChIKeys for ... pretraining corpus
- **实际证据**：原审计：本地 cleaned_pubchem_1MM.smiles 的 MD5 与官方 Zenodo15733575 v1 一致；本地预训练权重与15460715 v2 MD5一致。键缓存944168个有效格式唯一键；重算交集得到hERG32/59、DILI47/51、Ames522/732，connectivity47/59、48/51、597/732。未从全部语料重新生成缓存；语料侧直接MolFromSmiles，端点侧去盐/中和，规范化不对称。官方文件身份通过，不等于已证明该权重逐训练成员链。 本轮：944,296 行全量重建，原始唯一键 944,168 与旧缓存一致；统一规范化后唯一键 943,229。发布文件身份不证明 checkpoint 实际训练成员完整性。 证据：corpus_reconstruction.json（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：保留已核对的官方版本/MD5及新增SHA256；将“该缓存交集”与“完整训练成员已证实”分开，明确 exact 身份口径。
- **所需实验或资料**：原缺口：全语料行→失败/重复→key缓存的可重建manifest、统一规范化敏感性、训练checkpoint与语料版本的发布说明。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：精确训练暴露归因；交集计数可保留为条件性 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### E02 · P1 · ADJUSTED_OBSERVATIONAL_DIAGNOSTICS_COMPLETE_CAUSAL_CLAIM_UNSUPPORTED

- **问题位置**：paper/sections/04_benchmark.tex:15（本地证据，未随公开包分发）
- **原始陈述**：exposure still inflates absolute scores.
- **实际证据**：原审计：只有结构包含关系及暴露/未暴露子群性能；预训练目标为结构描述符，未发现 ADMET 标签在该预训练目标中的证据。子群化学性质与难度不同，没有反事实/随机化去暴露实验。 本轮：暴露子群、描述符/近邻、共同支持与固定overlap-weight诊断完成；支持不足项不估计。没有去暴露预训练干预，不能识别暴露造成的性能膨胀。 证据：exposure_overlap_weighted_diagnostics.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：改为“Structural overlap limits interpretation as generalization to unseen molecules; these observational comparisons do not identify performance inflation caused by exposure.”
- **所需实验或资料**：原缺口：描述符、类别、scaffold与训练近邻相似度的重叠诊断；足量时做预先规定的条件比较，因果归因另需干预设计。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：因果措辞 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### E03 · P1 · SMALL_STRATA_EXPLICIT

- **问题位置**：paper/sections/04_benchmark.tex:15（本地证据，未随公开包分发）
- **原始陈述**：leaving 12, 3, and 135 unseen
- **实际证据**：原审计：DILI exact-clean 仅4个且全正，AUROC不可定义；connectivity-clean仅3个。hERG connectivity-clean仅12个。clean只是相对此文件/身份规则未匹配，不等于无相近结构、无标签暴露或完全未见；很小子集不能稳健证明无效应。 本轮：所有子群报告人数/类别；单类别 AUROC 标记不可定义，不填补数值。 证据：exposure_covariate_summary.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：报告n/正负数/簇数与不可估计项；使用“not matched under this rule”，禁止补算/插值不可定义AUROC。
- **所需实验或资料**：原缺口：完整匹配规则、失败分母、类别计数、近邻诊断，足量独立数据仅经审核后使用。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：若保留未见/无效应强结论 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

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

### X01 · P1 · EXISTING_EXTERNAL_SENSITIVITY_ONLY

- **问题位置**：paper/sections/07_external.tex:11（本地证据，未随公开包分发）
- **原始陈述**：0.80 AUC gate fixed before the study
- **实际证据**：原审计：20个可定位神经external AUC逐项从冻结预测复算，最大差0。Karim不是独立原始实验来源；剔除exact/scaffold交集仍不能证明实验来源独立。现有最早发布Git记录晚于实验，未找到0.80门槛的带可信时间戳事前方案。 本轮：既有 Karim 数据严格边界敏感性完成；来源独立性和历史 0.80 gate 事前性仍未证实。 证据：existing_external_sensitivity_metrics.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：保留“历史结果低于0.80”描述；将未证实的事前声明标UNVERIFIED，并将Karim称历史集合迁移敏感性。
- **所需实验或资料**：原缺口：原始来源/assay溯源、许可证、连接结构排除策略、事前门槛记录与全部评价工件。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：独立外部评价/预设gate主张 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### X02 · P1 · OBSERVATIONAL_ONLY

- **问题位置**：paper/sections/07_external.tex:11（本地证据，未随公开包分发）
- **原始陈述**：Transfer is governed by scaffold coverage
- **实际证据**：原审计：shared 592行AUC .803 与 novel11899行AUC .653 的历史聚合相符，但两群非随机、类别率/化学空间/测量来源有差异。“only informative set”“threshold effect”“determining transfer”均超出此观察；TxGemma训练含TDC也不量化标签泄漏对该次分数的因果贡献。 本轮：重建剩余 exact/connectivity/联合组交集；不以子群差异宣称 scaffold 决定迁移。 证据：existing_external_residual_overlap.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：改为“performance differed between scaffold-sharing strata; subgroup comparison does not isolate a causal scaffold effect”；标明TxGemma仅为暴露参照。
- **所需实验或资料**：原缺口：类别、来源、近邻和描述符的分层诊断，完整连续相似度分析；无独立来源证据不得升级正式外测。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：当前因果外推 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### F01 · P1 · FORMAL_SI_OBTAINED_MAIN_FULLTEXT_UNVERIFIED

- **问题位置**：paper/refs.bib:1（本地证据，未随公开包分发）
- **原始陈述**：arXiv preprint arXiv:2506.15792 (2025)
- **实际证据**：原审计：一手正式题录确认2026 JCIM 66(17):10692–10701，DOI10.1021/acs.jcim.6c01546，标题新增“For Low-Data Regimes”。已核实正式摘要与题录；出版社全文/SI访问403，不能把arXiv v2当正式全文或声称其没有特定对照。 本轮：正式题录和 21 页 SI 已取得；已发现大型消融与微调策略分析，收窄新增性。 证据：FORMAL_CHEMELEON_CONTRIBUTION_BOUNDARY.md（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：下一阶段改正式引用并给完整作者；建立正式版/预印本/SI差异清单，贡献比较保留待核项。
- **所需实验或资料**：原缺口：正式全文与SI、版本化官方代码/模型及benchmark设定。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：正式版贡献去重尚未完成 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### F02 · P2 · FORMAL_METADATA_AUDIT_EXTENDED

- **问题位置**：paper/refs.bib:207（本地证据，未随公开包分发）
- **原始陈述**：Adaptive Conformal Inference ... ICLR (2021)
- **实际证据**：原审计：官方论文为NeurIPS2021，非ICLR。Angelopoulos/Bates教程已有正式2023版本《Conformal Prediction: A Gentle Introduction》，FnT ML16(4):494–591，DOI10.1561/2200000101。Liang作者主页列JASA to appear，不能编造正式卷页。 本轮：已修引用沿用阶段2；Liang等已核实2026正式online DOI，不能填写未知卷页；其余候选匹配不得自动升级为正确题录。 证据：BIBLIOGRAPHY_PRIMARY_AUDIT.md（本地证据，未随公开包分发）。
- **严重等级**：P2
- **建议修复**：更新会议与正式版本，保留尚未核准的出版信息为待核。
- **所需实验或资料**：原缺口：官方题录导出及对照；无实验。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：投稿前文献修复；不阻碍内部分析 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### F03 · P1 · STAGE2_DRAFT_BUILD_VERIFIED_NEW_RESULTS_SEPARATE

- **问题位置**：paper/main.bbl:12（本地证据，未随公开包分发）
- **原始陈述**：Azizi, S., et al.: TxGemma ...
- **实际证据**：原审计：当前refs.bib以Eric Wang为首作者，PDF/.bbl仍为Azizi；源/PDF不来自同一最终参考文献状态。静态检查31引用/33条目无缺键，不能代替编译身份验证。其余未逐字段取得一手记录的条目在本报告列UNVERIFIED，不承诺全31条正确。 本轮：阶段2新目录构建已验证；本轮新结果以可追踪 CSV/图与修订计划交付，不覆盖原 PDF。 证据：EXPERIMENT_COMPLETION.json（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：从冻结源码在新构建目录重编译并检查PDF/参考文献；不在原paper目录覆盖稿件。
- **所需实验或资料**：原缺口：原编译命令、TeX版本/依赖、源码hash→PDFhash；逐条BibTeX核验。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是：投稿工件一致性 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### P01 · P2 · ACTUAL_COST_RECORDED

- **问题位置**：paper/sections/01_intro.tex:14（本地证据，未随公开包分发）
- **原始陈述**：the protocol costs one extra training run and two extra splits
- **实际证据**：原审计：实有端点×seeds×容量/预算/LR/低数据/ChemBERTa/校准训练矩阵，四路隔离也涉及重新训练；一次“run”不能代表完整审计成本。当前尚有数据审核、官方语料键重建和统计报告工作。 本轮：按实际独立配置、拟合轨迹和日志秒数报告成本，不再声称完整审计只需一次额外训练。 证据：EXPERIMENT_COMPLETION.json（本地证据，未随公开包分发）。
- **严重等级**：P2
- **建议修复**：分最小容量对照与完整审计两种范围，给实际run数、GPU时间与人工审核范围；无计时证据处不报小时。
- **所需实验或资料**：原缺口：可追踪run manifest与日志计时汇总；无须新增训练。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：否：收窄陈述即可 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### F04 · P2 · PRIMARY_PAGE_CONFIRMED_CORRECTION_REQUIRED

- **问题位置**：paper/refs.bib:245（本地证据，未随公开包分发）
- **原始陈述**：pages = {2739--2747} (Vaicenavicius et al., 2019)
- **实际证据**：原审计：PMLR官方v89/vaicenavicius19a页面和BibTeX均为3459--3467。 本轮：所有33条题录已有来源登记，内容归因审核范围另列。 证据：BIBLIOGRAPHY_PRIMARY_AUDIT.md（本地证据，未随公开包分发）。
- **严重等级**：P2
- **建议修复**：在新的修订副本中改页码3459--3467，保留原历史bib。
- **所需实验或资料**：原缺口：无需新增实验；采用官方题录并在新构建中核对。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：投稿前应修正题录；不改变实验结论 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### N01 · P0 · CANONICAL_FP32_COMPLETE_RAW_BF16_BLOCKED

- **问题位置**：本轮scripts/train_graph.py原BF16推理路径、runs/原始预测；protocol/EVALUATION_PRECISION_AMENDMENT.json；reports/pilot_weight_replay.json
- **原始陈述**：原执行计划假设冻结权重可在数值容差内重放其BF16预测；此假设未通过完整回放前不应写成已验证。
- **实际证据**：原审计：两份预先指定checkpoint重复前向：hERG最大相邻概率差0.00390625、AUROC差0.004201680672268893；Ames最大相邻概率差0.015625。BF16与FP32启用确定性算法的预检查均可稳定，不能归因于单一kernel或dtype。原BF16确定性复现链标记BLOCKED并完整保留。 本轮：643图模型、39个Transformer及60个候选状态已生成确定性FP32预测并双前向检查；另进程1841个预测角色的float32概率全部逐位一致，见canonical_inference_complete.json和weight_replay_progress.json。10个FP32训练对照完成；hERG3个配对seed，DILI/Ames各1个seed，后两者只作描述。来源工厂哈希不变。 全矩阵政策漂移：BF16到canonical最大概率差0.065715970；test AUROC差范围[-0.046918768, 0.145370370]。它与重复BF16前向差的口径不同；独立sklearn核对支持最大AUROC漂移案例。 证据：NUMERICAL_REPRODUCIBILITY_AMENDMENT.md（本地证据，未随公开包分发）。
- **严重等级**：P0
- **建议修复**：显式披露数值政策修订；新神经统计统一使用evaluation_fp32，原BF16预测仅作诊断。保留原epoch选择与训练记录，不把canonical回放写成原训练轨迹逐位重复；全部10个训练政策对照逐项报告，不按test选择政策。
- **所需实验或资料**：原缺口：修复固定权重数值链所需的全矩阵canonical双前向与另进程回放已完成。若声称完整训练逐位可复现，仍需在固定环境重跑训练轨迹；若声称dtype独立因果效应，需分离dtype与确定性reduction的干预设计。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：原BF16预测的确定性复现声明仍BLOCKED；可使用经验证的canonical版本并披露修订。数据来源/标签准入限制独立保留。 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### F05 · P1 · BROAD_NOVELTY_CLAIM_NARROWED

- **问题位置**：paper/sections/02_related.tex:4（本地证据，未随公开包分发）
- **原始陈述**：Recent benchmarks probe foundation models under data scarcity, out-of-distribution shift, and activity cliffs ... but do not separate capacity from pretraining or audit the calibration split.
- **实际证据**：原审计：Zhao 2026正式主文已核读：广泛ADMET挑战与5×5重复已有。主文关键词搜索不足以证明其SI/代码不存在相关控制；本轮未独立复现该研究。 本轮：相关正式研究和本项目贡献边界已分开登记。 证据：RELATED_ADMET_BENCHMARK_BOUNDARY.md（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：改为本项目正面的具体问题与证据定位，删除未覆盖SI/代码的全面缺失断言；参见贡献边界建议句。
- **所需实验或资料**：原缺口：若坚持负面全面比较，需逐项读取正式SI及相关代码/配置；无需为改写另做大规模训练。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是，若保留未经证实的已有工作缺失论断 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C05 · P1 · GUARANTEE_SCOPE_NARROWED

- **问题位置**：paper/sections/02_related.tex:6（本地证据，未随公开包分发）
- **原始陈述**：calibrating on the model-selection split ... breaks exchangeability regardless of distribution shift.
- **实际证据**：原审计：标准split-conformal固定score的独立校准条件通常不满足，但不能从复用本身推导每个具体模型必然欠覆盖；存在选择感知的有效性研究。Liang/Zhu/Barber 2026正式论文讨论特定选择规则，不能直接当作本项目AUROC早停机制的验证。 本轮：随机pool诊断与域差异解释分开；不把三条训练轨迹的重复拆分当独立证明。 证据：[calibration_factorial_summary.csv](../evidence/reports/calibration_factorial_summary.csv)。
- **严重等级**：P1
- **建议修复**：改为：Standard split-conformal guarantees do not directly apply when calibration observations influenced model selection, unless selection-aware validity conditions are established.
- **所需实验或资料**：原缺口：本轮同轨迹随机pool复用诊断已安排；若要求普遍保证，需针对具体选择算法的理论条件，观察性coverage不能替代理论。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是，若保留普遍必然破坏/欠覆盖论断 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### M04 · P1 · HISTORICAL_TEST_SELECTION_DETECTED_NEW_FIXED_COMPARISONS

- **问题位置**：scripts/16_vs_classical.py:71（本地证据，未随公开包分发）; paper/sections/04_benchmark.tex:9（本地证据，未随公开包分发）
- **原始陈述**：best_name = max(klass, key=lambda k: roc_auc_score(ys, klass[k])) / strongest classical baseline
- **实际证据**：原审计：历史脚本在test选择RF/HistGB/LogReg中的最高AUC，再对被选基线作配对统计。新做9个明确历史配置的数值重建，使用冻结旧报告中的比较身份，不重新按test选胜者。数字接近或复现不使选择后推断自动有效。 本轮：历史配置重建与新五套修复划分的固定基线比较分开。 证据：historical_classical_numeric_replay.csv（本地证据，未随公开包分发）。
- **严重等级**：P1
- **建议修复**：将旧strongest比较限定为探索性、说明test选择；新实验逐个报告全部固定基线，不用test决定报告哪个算法。如需选择器，必须在selection冻结。
- **所需实验或资料**：原缺口：本轮105传统模型和全比较已安排；历史原始classical权重/概率未保存，精确旧预测仍有UNVERIFIED。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：是，若保留旧比较作为未经选择的确认性推断 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。

### C06 · P2 · LEGACY_VALUES_RECOMPUTED_DEFINITION_LIMITED

- **问题位置**：scripts/11_conformal_scaffold.py:279（本地证据，未随公开包分发）; paper/sections/06_calibration.tex:14（本地证据，未随公开包分发）
- **原始陈述**：Ames AURC 0.142 versus 0.171/0.246; hERG 0.082 versus 0.230/0.176
- **实际证据**：原审计：24个历史AURC点值和18个原500-draw区间均从冻结概率/源码复算，最大误差0。定义实际只平均k=20..n的累计风险；hERG起始20/59、DILI20/51、Ames20/732，非统一完整coverage范围。ties用原始顺序stable打破。 本轮：旧24点/18区间精确复现；新定义结果单独保存，避免混表。 证据：historical_selective_recomputed.csv（本地证据，未随公开包分发）。
- **严重等级**：P2
- **建议修复**：保留可复算数字但说明截断区间、离散求均值、ties及原500次compound条件区间；新实验另报k=1..n完整离散AURC，ties按均匀排序期望处理。
- **所需实验或资料**：原缺口：本轮全量risk-coverage/各固定scorer对照、compound和联合分组5000次条件区间；不能用test挑最优scorer后作确认性结论。 本轮技术实验按新状态完成；无法核实的来源/因果/历史证据不以新分数替代。
- **是否阻碍正式投稿**：原门槛：投稿前必须澄清指标定义；不因此否定同端点相同范围内的描述排序 本轮仅解除了相应技术执行缺口；正式数据准入及过强主张仍按证据收窄。
