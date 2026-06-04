# PlantRG 训练数据清洗

本目录保存 PlantRG 模型项目第二阶段“训练数据清洗”的脚本、Slurm 提交脚本和结果。

当前 protein 正样本严格清洗已完成。Slurm 成功任务号为 `8438823`，运行节点为 `cu27`。

## 当前目标

第一版 benchmark 优先使用 protein 序列作为正样本输入。本阶段先构建 protein 严格清洗集合：

- 排除含 `.` 的 protein 记录；
- 剥离末端 `*` 终止符；
- 排除含内部 `*` 的 protein 记录；
- 排除含不兼容蛋白语言模型字符的记录；
- 输出本地 FASTA 和逐记录索引；
- 输出可提交 GitHub 的轻量统计表和中文报告。

## 运行方式

CPU 任务通过 Slurm 提交到 `q07` 分区：

```bash
sbatch -p q07 -c 30 model_project/data_cleaning/run_protein_cleaning.sh
```

脚本内部使用：

```bash
mamba run -n bio3 python model_project/data_cleaning/scripts/build_protein_positive_set.py
```

## 输出

输出目录：`model_project/data_cleaning/results/`

- `protein_cleaning_summary.json`：全局清洗统计。
- `tables/protein_cleaning_by_species.tsv`：每个物种清洗前后记录数。
- `蛋白正样本清洗报告.md`：中文阶段报告。
- `positive_protein_strict.fa`：严格清洗后的正样本 FASTA，仅本地保留。
- `positive_protein_strict_index.tsv`：逐记录清洗索引，仅本地保留。

大型 FASTA 和逐记录索引不提交 GitHub。

## 当前结论

- 原始 protein 记录数：1,605,489
- 严格保留记录数：1,583,910
- 排除记录数：21,579
- 保留率：98.6559%
- 剥离末端 `*` 终止符记录数：203,635
- 含 `.` 排除数：20,057
- 含内部 `*` 排除数：1,522
