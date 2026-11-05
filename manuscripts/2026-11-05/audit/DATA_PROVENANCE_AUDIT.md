> 公开聚合副本：本机路径已移除；未分发证据明确保留为本地可见，不冒称公开可复核或独立审核批准。原始审计记录未改写。

# 数据血缘审计更新

本轮为获用户授权的探索性实验，已跳过等待独立审核人，未取得独立批准。原始资料与 main 未改动。源标签语义和新增外部数据准入未闭环处继续 UNVERIFIED/BLOCKED；不得作为已批准正式评价。

官方SI/TDC文件身份和8408行内部映射见阶段2；本轮已关联五次划分形成42040行内部血缘映射，并验证8326个最终端点样本的键、标签、结构未变。派生划分继承原标签，不把阈值筛选敏感性写成标签重建。944,296行发布语料全量身份已重建。新外部候选只做来源调查，未准入、未计算模型分数。逐成员文件仅在本地data、runs、_internal及source_quarantine处理，不视为批准公开。

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
