# PlantRG 模型项目

本仓库用于记录基于 PlantRG 数据库构建植物抗性基因模型、benchmark 和论文工作的进展。当前项目运行在 Slurm 集群登录节点，原始数据下载只在登录节点完成；CPU 计算任务后续通过 `q07` 分区提交，GPU 任务由用户单独执行。

## 当前数据状态

PlantRG FASTA 数据已下载并完成校验：

- 物种数：787
- FASTA 文件：1,574
- CDS 文件：787
- protein 文件：787
- 缺失文件：0
- 空文件：0
- 实际落盘大小：4,137,691,785 bytes，约 3.854 GiB

原始数据位于本地工作目录：

- `downloads/sequences/CDS/`
- `downloads/sequences/protein/`

注意：FASTA 数据体量较大，不提交到 GitHub。

## 仓库内容

- `PlantRG_data_introduction.md`：PlantRG 数据介绍、下载记录和最终校验结果。
- `model_project/PlantRG模型项目长期记忆.md`：模型项目长期记忆，记录论文可行性判断、推荐路线和风险。
- `model_project/模型结构解析.md`：拟建模型框架、数据流、训练任务和评估设计。
- `model_project/项目进展计划.md`：模型项目阶段进展、当前结论和后续计划。
- `model_project/data_audit/`：第一阶段数据审计脚本、Slurm 任务和轻量结果。
- `scripts/`：下载和补跑脚本。
- `metadata/plantrg_full_manifest.csv`：完整 FASTA 下载清单。

## 计算环境约束

集群使用规则：

- CPU 任务通过 Slurm 提交到 `q07` 分区。
- 每个计算节点最多申请 30 核、150G 内存。
- 每次最多提交 6 个命令。
- 程序运行环境优先使用 `mamba` 的 `bio3` 环境。
- 示例命令：

```bash
sbatch -p q07 -c 30 run.sh
```

数据下载规则：

- 下载数据只在登录节点执行。
- 后续 CPU 密集型分析、HMMER、MMseqs2、特征提取、模型训练等应提交 Slurm。
- GPU 任务由用户自行执行。

## 推荐研究主线

不建议只做普通“抗性基因分类器”。当前更稳妥的论文主线是：

> PlantRG-Bench：面向植物抗性基因预测的跨物种基准数据集与蛋白语言模型框架。

核心任务：

1. 构建严格去冗余的 PlantRG 抗性基因 benchmark。
2. 补充同物种或近缘物种非抗性基因负样本。
3. 设计 random split、species split、genus/family split 等多级泛化评估。
4. 比较 HMM/domain baseline、k-mer 模型、ESM/ProtT5 embedding 模型。
5. 结合 domain、motif 和谱系分析做模型解释。

## 当前进展

- 已完成 PlantRG FASTA 数据下载。
- 已完成 manifest 对照校验。
- 已形成模型项目长期记忆。
- 已完成第一阶段数据审计，并通过 Slurm 任务 `8438806` 在 `q07` 分区完成计算。
- 已完成第二阶段 protein 正样本严格清洗，并通过 Slurm 任务 `8438823` 在 `q07` 分区完成计算。
- 已将项目说明、模型结构解析和阶段审计结果同步到 GitHub。

第一阶段数据审计结论：

- CDS 记录数：1,605,489
- protein 记录数：1,605,489
- CDS/protein ID 配对完整，未发现未配对物种。
- 未发现空序列或重复 ID。
- 32 个文件包含非标准字符，需要在建模前制定清洗策略。
- protein 建模路线当前更稳；CDS 建模建议作为补充任务或敏感性分析。

第二阶段 protein 清洗结论：

- 原始 protein 记录数：1,605,489
- 严格清洗保留记录数：1,583,910
- 排除记录数：21,579
- 保留率：98.6559%
- 已剥离末端 `*` 终止符记录数：203,635
- 含 `.` 排除数：20,057
- 含内部 `*` 排除数：1,522
- 清洗后的本地正样本 FASTA：`model_project/data_cleaning/results/positive_protein_strict.fa`

## 下一阶段计划

### 阶段 1：数据审计

- 已解析 787 个 protein FASTA 和 787 个 CDS FASTA。
- 已统计每个物种的抗性基因数量。
- 已统计 CDS/protein 长度分布。
- 已检查异常序列、空序列、非标准字符。
- 已确认 CDS 和 protein ID 可一一对应。

### 阶段 2：标签和负样本

- 已完成 protein 正样本严格清洗。
- 下一步确认 PlantRG FASTA header 是否含有 family/domain 信息。
- 如果无精细标签，则使用 HMMER/Pfam 自行重注释。
- 从外部 proteome 构建非抗性基因负样本。
- 使用 MMseqs2/CD-HIT 做同源去冗余。

### 阶段 3：benchmark 和 baseline

- 构建二分类任务：R gene vs non-R gene。
- 构建可选多分类任务：CNL/TNL/RLK/RLP/NBS 等。
- 实现 k-mer、domain rule、ESM/ProtT5 embedding baseline。
- 做跨物种和跨谱系泛化评估。

### 阶段 4：论文分析

- 系统比较不同划分下的模型性能。
- 分析随机划分与跨物种划分的性能差异。
- 做模型解释和候选基因发现。
- 整理图表、方法和可复现实验流程。
