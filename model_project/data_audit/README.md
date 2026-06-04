# PlantRG 数据审计

本目录保存 PlantRG 模型项目第一阶段“数据审计”的脚本、Slurm 提交脚本和结果。

当前阶段已完成。Slurm 成功任务号为 `8438806`，运行节点为 `cu27`。

## 目标

数据审计阶段用于确认当前下载到本地的 PlantRG FASTA 是否适合进入后续 benchmark 和建模流程。

主要检查内容：

- 每个 FASTA 文件的序列数量；
- CDS 和 protein 的长度分布；
- 异常字符；
- 空序列；
- 重复 ID；
- CDS 长度是否为 3 的倍数；
- CDS 是否以 ATG 开头；
- CDS 是否有终止密码子；
- protein 是否包含 `*`；
- 同一物种 CDS/protein ID 是否一一对应。

## 运行方式

CPU 任务通过 Slurm 提交到 `q07` 分区：

```bash
sbatch -p q07 -c 30 model_project/data_audit/run_data_audit.sh
```

脚本内部使用：

```bash
mamba run -n bio3 python model_project/data_audit/scripts/audit_plantrg_sequences.py
```

## 输出

已输出到 `model_project/data_audit/results/`：

- `数据审计报告.md`
- `global_summary.json`
- `tables/file_summary.tsv`
- `tables/species_pairing_summary.tsv`
- `tables/invalid_records_summary.tsv`
- `tables/all_records.tsv`
- `per_file_records/`

其中 `all_records.tsv` 和 `per_file_records/` 较大，仅保留在本地，不提交 GitHub。GitHub 只同步报告、脚本和轻量 summary。

## 当前结论

- FASTA 文件总数：1,574
- 物种数：787
- CDS 记录数：1,605,489
- protein 记录数：1,605,489
- CDS/protein ID 配对完整。
- 未发现重复 ID 或空序列。
- 32 个文件含非标准字符，需要在建模前清洗。
