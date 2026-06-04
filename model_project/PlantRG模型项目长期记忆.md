# PlantRG 模型项目长期记忆

更新时间：2026-06-04

## 项目边界

本文件夹 `model_project/` 用于保存基于当前 PlantRG 数据库构建模型、设计实验和撰写论文相关的长期材料。后续模型项目相关文件尽量都放在此文件夹内，避免和原始下载数据、下载脚本混在一起。

当前本地 PlantRG 数据已下载完成，核心数据位于：

- `../downloads/sequences/CDS/`
- `../downloads/sequences/protein/`
- `../metadata/plantrg_full_manifest.csv`
- `../PlantRG_data_introduction.md`

最终下载校验结果：

- FASTA 文件总数：1,574
- CDS 文件：787
- protein 文件：787
- 覆盖物种：787
- 缺失文件：0
- 空文件：0
- 实际落盘大小：4,137,691,785 bytes，约 3.854 GiB

## 对“能否构建模型发文章”的总体判断

可以做，有发文章潜力，但不能定位成简单的“用 PlantRG 训练一个抗性基因分类器”。这个方向已有较多已有工作，例如 PRGdb/DRAGO、RGAugury、prPred-DRLF、PRGminer、CLAP-HMM 等。如果只是做普通二分类或普通深度学习模型，创新性不足，容易被质疑标签循环、负样本构造不清、同源序列泄漏和泛化能力不足。

更稳妥的论文定位应是：

- 构建跨物种标准 benchmark；
- 研究植物抗性基因的跨物种泛化；
- 使用蛋白语言模型或序列表征模型做抗性基因预测；
- 结合严格去冗余和外部验证集；
- 加入可解释分析，例如 domain、motif、谱系和物种层面的规律。

## 当前数据能直接支持的任务

当前下载到本地的数据主要是抗性基因的 CDS 和 protein FASTA，因此适合做以下方向：

- 蛋白序列模型；
- CDS/k-mer/密码子使用特征模型；
- 抗性基因序列表征学习；
- 跨物种、跨属、跨科泛化评估；
- 抗性基因家族或结构域相关分析；
- 新抗性基因候选筛选。

当前数据不直接包含：

- 非抗性基因负样本；
- 真实抗病或抗虫表型；
- 病原或害虫对应关系；
- 每条基因的精细类别标签，如 CNL、TNL、RLK、RLP、NBS 等。

因此，如果目标是预测“某植物是否抗某病虫害”，仅靠当前 FASTA 不够，需要额外补充表型、病原、QTL/GWAS、文献或实验标签。

## 推荐论文方向

### 方向一：PlantRG-Bench 跨物种抗性基因预测基准

这是当前最推荐的主线。

核心想法：基于 PlantRG 的 787 个物种抗性基因序列，构建一个严格去冗余、跨物种划分的植物抗性基因预测 benchmark，并系统评估传统特征、HMM/domain 规则、蛋白语言模型 embedding 和轻量分类器。

可设计任务：

- R gene vs non-R gene 二分类；
- 如果能补到家族标签，再做 CNL/TNL/RLK/RLP/NBS 等多分类；
- leave-one-species-out；
- leave-one-genus-out；
- leave-one-family-out；
- 同源去冗余随机划分 vs 物种隔离划分对比。

文章贡献：

- 构建标准化数据集；
- 系统比较已有方法和新模型；
- 证明随机划分下的高性能可能被同源泄漏夸大；
- 给出更真实的跨物种泛化评估；
- 发布可复用 pipeline 和数据划分。

主要风险：

- 需要补负样本；
- 需要严格去冗余；
- 需要外部验证集支撑。

### 方向二：抗性基因专用序列表征模型

核心想法：用 PlantRG 的大规模 pan-plant R gene protein/CDS 序列，构建抗性基因专用 embedding 或轻量微调模型，重点评估跨谱系泛化和序列空间结构。

可用模型：

- ESM embedding + LightGBM/MLP；
- ProtT5 embedding + LightGBM/MLP；
- CDS k-mer + 传统机器学习；
- HMMER/domain baseline；
- 必要时做轻量 LoRA 或 adapter 微调。

文章卖点：

- 不只是分类，而是“植物抗性基因专用表征学习”；
- 能研究抗性基因在不同物种和谱系中的序列空间；
- 可输出每个物种的 resistance gene repertoire embedding。

主要风险：

- 如果没有高质量负样本和外部验证，只做 embedding 聚类会偏描述性；
- 需要证明模型优于已有工具或已有蛋白语言模型直接使用。

### 方向三：模型解释结合抗性基因进化规律

核心想法：将模型预测和 embedding 解释与 domain、motif、物种谱系、重复扩张等生物学信息结合，寻找植物抗性基因的保守与分化规律。

可能分析：

- NBS、LRR、TIR、CC、Kinase、TM 等结构域组合；
- 不同物种或类群的抗性基因空间分布；
- 快速扩张类群；
- 模型关注的 motif 与已知 immune receptor motif 是否一致；
- 候选新型抗性基因筛选。

主要风险：

- 需要额外抓取或重注释 domain 信息；
- 如果只做可视化，论文力度不足；
- 最好与 benchmark 或模型预测主线结合。

## 不推荐作为主论文的方向

不建议只做以下内容：

- 直接用 PlantRG 正样本训练一个普通二分类模型；
- 只用 PlantRG 序列做 embedding 聚类；
- 只用 CDS 训练 CNN/RNN 判断是不是抗性基因；
- 只复现已有 R gene predictor；
- 不做同源去冗余和跨物种验证的高分模型。

这些方向容易被审稿人认为创新不足、评价不严格或存在数据泄漏。

## 必须补充的数据

为了把模型项目做成可投稿论文，建议补充以下数据：

### 负样本

优先从同物种或近缘物种 proteome 中抽取非抗性蛋白。负样本需要过滤掉明显含有抗性相关 domain 的蛋白，避免标签污染。

可能来源：

- Ensembl Plants；
- NCBI RefSeq/GenBank proteome；
- UniProt；
- Phytozome，如果有权限。

### 结构域标签

可以使用 Pfam/HMMER 或 InterProScan 对 protein 序列重注释，得到 domain 组合。

重点 domain：

- NBS/NB-ARC；
- LRR；
- TIR；
- CC；
- RPW8；
- Kinase；
- TM；
- LysM；
- RLP/RLK 相关结构域。

### 外部验证集

建议整理独立外部测试集，避免只在 PlantRG 内部循环验证。

可能来源：

- PRGdb；
- PlantNLRatlas；
- 已克隆抗性基因文献集合；
- RGAugury 或其他工具附带测试集；
- PRGminer 论文或工具数据，如可获得。

## 建议的技术路线

### 第一阶段：数据审计

目标：

- 解析所有 protein/CDS FASTA；
- 统计每个物种的基因数、长度分布、异常序列；
- 检查 ID 格式；
- 检查 CDS 和 protein 是否一一对应；
- 去除过短、过长、含异常字符的序列。

产出：

- `model_project/data_audit/`；
- 物种统计表；
- 序列质量报告；
- 可用于建模的 clean manifest。

### 第二阶段：标签和负样本构建

目标：

- 从外部 proteome 构建负样本；
- 用 HMMER/Pfam 重注释 domain；
- 建立 binary label 和可选 family label；
- 做同源去冗余。

关键点：

- 不允许训练集和测试集有高度相似同源序列泄漏；
- 负样本最好和正样本按物种/长度/蛋白类型做一定匹配；
- 保留多个划分版本：random、species split、genus/family split。

### 第三阶段：baseline 和模型

建议 baseline：

- k-mer + Logistic Regression / Random Forest / LightGBM；
- amino acid composition；
- HMMER/domain rule；
- ESM/ProtT5 embedding + LightGBM；
- ESM/ProtT5 embedding + MLP。

如果资源允许，再尝试：

- protein language model adapter/LoRA；
- CDS DNABERT 类模型；
- 多模态融合：protein embedding + domain + CDS codon feature。

### 第四阶段：跨物种泛化评估

核心评估：

- 随机划分；
- 按物种留出；
- 按属留出；
- 按科或更高分类群留出；
- 与传统 HMM/domain 方法比较。

指标：

- AUROC；
- AUPRC；
- F1；
- recall；
- precision；
- calibration；
- per-family/per-lineage performance。

### 第五阶段：解释和生物学发现

可能输出：

- 模型错误案例；
- 难预测类群；
- motif/attention/domain 解释；
- 物种层面的抗性基因 repertoire embedding；
- 候选新型抗性基因。

## 论文定位建议

推荐题目方向：

> PlantRG-Bench: a cross-species benchmark and protein language model framework for plant resistance gene prediction

中文理解：

> PlantRG-Bench：面向植物抗性基因预测的跨物种基准数据集与蛋白语言模型框架

推荐主张：

1. 当前抗性基因预测工具在随机划分下容易高估性能；
2. 跨物种和跨谱系泛化才是更真实的评价；
3. PlantRG 大规模序列资源可以构建更严格的 benchmark；
4. 蛋白语言模型 embedding 在跨物种泛化中有优势；
5. domain/motif 解释可以揭示抗性基因家族的保守与分化规律。

## 可能投稿层级

如果只完成 benchmark + 常规模型：

- BMC Genomics；
- BMC Plant Biology；
- Frontiers in Plant Science；
- Plant Methods。

如果完成严格数据集、外部验证、强模型、解释分析和开源工具：

- Briefings in Bioinformatics；
- Horticulture Research；
- Plant Biotechnology Journal；
- Molecular Plant Pathology。

更高层级需要更强的实验验证或非常突出的生物学发现。

## 当前最重要的下一步

建议下一步不是直接训练模型，而是先做数据审计和可行性验证：

1. 解析 787 个 protein FASTA；
2. 统计每个物种 R gene 数量和长度分布；
3. 检查 CDS/protein 是否一一对应；
4. 随机抽样检查 FASTA header 是否含有类别或 domain 信息；
5. 确定是否能从 PlantRG 网站继续抓取每条基因的 family/domain/annotation 表；
6. 如果网站抓不到，则用 HMMER/Pfam 自行重注释；
7. 决定负样本来源。

## 重要注意事项

- 不能把 PlantRG 自己的预测结果当成完全真实标签，需要在论文中明确其来源和局限；
- 必须避免同源序列泄漏；
- 必须构建外部测试集；
- 模型性能不要只报随机划分；
- 负样本构造会决定论文可信度；
- 如果没有表型标签，不能宣称模型能预测具体病虫害抗性；
- 最稳妥的论文主线是“抗性基因识别/分类/跨物种泛化”，不是“抗病性预测”。

