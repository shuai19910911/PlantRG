#!/usr/bin/env python3
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


MODEL_ALLOWED = set("ACDEFGHIKLMNPQRSTVWYXBZJUO")


def parse_args():
    parser = argparse.ArgumentParser(description="Build strict PlantRG protein positive set.")
    parser.add_argument("--manifest", default="metadata/plantrg_full_manifest.csv")
    parser.add_argument("--protein-dir", default="downloads/sequences/protein")
    parser.add_argument("--outdir", default="model_project/data_cleaning/results")
    return parser.parse_args()


def read_fasta(path):
    seq_id = None
    desc = ""
    chunks = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if seq_id is not None:
                    yield seq_id, desc, "".join(chunks)
                desc = line[1:]
                seq_id = desc.split()[0]
                chunks = []
            else:
                chunks.append(line)
        if seq_id is not None:
            yield seq_id, desc, "".join(chunks)


def write_fasta_record(handle, header, seq, width=80):
    handle.write(f">{header}\n")
    for start in range(0, len(seq), width):
        handle.write(seq[start : start + width] + "\n")


def load_protein_manifest(path):
    rows = []
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            if row["type"] == "protein":
                rows.append(row)
    return sorted(rows, key=lambda r: (r["species"], r["filename"]))


def classify_sequence(seq):
    upper = seq.upper()
    terminal_stop_stripped = 0
    while upper.endswith("*"):
        upper = upper[:-1]
        terminal_stop_stripped += 1
    chars = set(upper)
    invalid = "".join(sorted(chars - MODEL_ALLOWED))
    reasons = []
    if not upper:
        reasons.append("empty")
    if "." in upper:
        reasons.append("dot")
    if "*" in upper:
        reasons.append("internal_stop")
    if invalid:
        reasons.append("invalid_chars")
    return upper, invalid, reasons, terminal_stop_stripped


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    table_dir = outdir / "tables"
    outdir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    protein_rows = load_protein_manifest(args.manifest)
    fasta_out = outdir / "positive_protein_strict.fa"
    index_out = outdir / "positive_protein_strict_index.tsv"
    species_out = table_dir / "protein_cleaning_by_species.tsv"
    summary_out = outdir / "protein_cleaning_summary.json"
    report_out = outdir / "蛋白正样本清洗报告.md"

    global_counts = Counter()
    species_counts = defaultdict(Counter)
    invalid_patterns = Counter()
    length_sum = 0
    kept_length_sum = 0

    with fasta_out.open("w") as fasta_handle, index_out.open("w", newline="") as index_handle:
        index_fields = [
            "species",
            "filename",
            "seq_id",
            "original_length",
            "cleaned_length",
            "status",
            "exclude_reason",
            "invalid_chars",
            "terminal_stop_stripped",
        ]
        index_writer = csv.DictWriter(index_handle, fieldnames=index_fields, delimiter="\t")
        index_writer.writeheader()

        for row in protein_rows:
            species = row["species"]
            filename = row["filename"]
            fasta_path = Path(args.protein_dir) / filename
            for seq_id, desc, seq in read_fasta(fasta_path):
                original_length = len(seq)
                upper, invalid, reasons, terminal_stop_stripped = classify_sequence(seq)
                length = len(upper)
                status = "keep" if not reasons else "exclude"
                reason_text = ",".join(reasons)

                global_counts["total_records"] += 1
                species_counts[species]["total_records"] += 1
                length_sum += original_length
                if terminal_stop_stripped:
                    global_counts["terminal_stop_stripped_records"] += 1
                    global_counts["terminal_stop_stripped_chars"] += terminal_stop_stripped
                    species_counts[species]["terminal_stop_stripped_records"] += 1
                    species_counts[species]["terminal_stop_stripped_chars"] += terminal_stop_stripped
                if status == "keep":
                    global_counts["kept_records"] += 1
                    species_counts[species]["kept_records"] += 1
                    kept_length_sum += length
                    clean_header = f"{species}|{seq_id}"
                    write_fasta_record(fasta_handle, clean_header, upper)
                else:
                    global_counts["excluded_records"] += 1
                    species_counts[species]["excluded_records"] += 1
                    for reason in reasons:
                        global_counts[f"excluded_{reason}"] += 1
                        species_counts[species][f"excluded_{reason}"] += 1
                    if invalid:
                        invalid_patterns[invalid] += 1

                index_writer.writerow(
                    {
                        "species": species,
                        "filename": filename,
                        "seq_id": seq_id,
                        "original_length": original_length,
                        "cleaned_length": length,
                        "status": status,
                        "exclude_reason": reason_text,
                        "invalid_chars": invalid,
                        "terminal_stop_stripped": terminal_stop_stripped,
                    }
                )

    species_fields = [
        "species",
        "total_records",
        "kept_records",
        "excluded_records",
        "excluded_dot",
        "excluded_internal_stop",
        "excluded_invalid_chars",
        "excluded_empty",
        "terminal_stop_stripped_records",
        "terminal_stop_stripped_chars",
        "retention_rate",
    ]
    with species_out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=species_fields, delimiter="\t")
        writer.writeheader()
        for species in sorted(species_counts):
            counts = species_counts[species]
            total = counts["total_records"]
            kept = counts["kept_records"]
            row = {field: counts[field] for field in species_fields if field not in {"species", "retention_rate"}}
            row["species"] = species
            row["retention_rate"] = f"{kept / total:.6f}" if total else "0.000000"
            writer.writerow(row)

    total = global_counts["total_records"]
    kept = global_counts["kept_records"]
    summary = {
        "protein_files": len(protein_rows),
        "species": len(species_counts),
        "total_records": total,
        "kept_records": kept,
        "excluded_records": global_counts["excluded_records"],
        "excluded_dot": global_counts["excluded_dot"],
        "excluded_internal_stop": global_counts["excluded_internal_stop"],
        "excluded_invalid_chars": global_counts["excluded_invalid_chars"],
        "excluded_empty": global_counts["excluded_empty"],
        "terminal_stop_stripped_records": global_counts["terminal_stop_stripped_records"],
        "terminal_stop_stripped_chars": global_counts["terminal_stop_stripped_chars"],
        "retention_rate": kept / total if total else 0,
        "mean_length_all": length_sum / total if total else 0,
        "mean_length_kept": kept_length_sum / kept if kept else 0,
        "top_invalid_patterns": invalid_patterns.most_common(20),
        "strict_fasta": str(fasta_out),
        "strict_index": str(index_out),
        "species_table": str(species_out),
    }
    with summary_out.open("w") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    with report_out.open("w") as handle:
        handle.write("# PlantRG 蛋白正样本清洗报告\n\n")
        handle.write("更新时间：2026-06-04\n\n")
        handle.write("## 清洗规则\n\n")
        handle.write("- 输入：PlantRG protein FASTA，共 787 个文件。\n")
        handle.write("- 保留：仅包含蛋白语言模型兼容字符 `ACDEFGHIKLMNPQRSTVWYXBZJUO` 的序列。\n")
        handle.write("- 处理：剥离序列末端 `*` 终止符。\n")
        handle.write("- 排除：含 `.`、内部 `*`、空序列或其他非兼容字符的序列。\n\n")
        handle.write("## 全局结果\n\n")
        handle.write(f"- protein 文件数：{summary['protein_files']}\n")
        handle.write(f"- 物种数：{summary['species']}\n")
        handle.write(f"- 原始 protein 记录数：{summary['total_records']}\n")
        handle.write(f"- 严格保留记录数：{summary['kept_records']}\n")
        handle.write(f"- 排除记录数：{summary['excluded_records']}\n")
        handle.write(f"- 保留率：{summary['retention_rate']:.6f}\n")
        handle.write(f"- 含 `.` 排除数：{summary['excluded_dot']}\n")
        handle.write(f"- 含内部 `*` 排除数：{summary['excluded_internal_stop']}\n")
        handle.write(f"- 非兼容字符排除数：{summary['excluded_invalid_chars']}\n")
        handle.write(f"- 空序列排除数：{summary['excluded_empty']}\n\n")
        handle.write("## 末端终止符处理\n\n")
        handle.write(f"- 剥离末端 `*` 的记录数：{summary['terminal_stop_stripped_records']}\n")
        handle.write(f"- 剥离末端 `*` 字符数：{summary['terminal_stop_stripped_chars']}\n\n")
        handle.write("## 输出文件\n\n")
        handle.write("- `positive_protein_strict.fa`：严格清洗后的正样本 FASTA，仅本地保留。\n")
        handle.write("- `positive_protein_strict_index.tsv`：逐记录清洗索引，仅本地保留。\n")
        handle.write("- `tables/protein_cleaning_by_species.tsv`：每个物种清洗统计。\n")
        handle.write("- `protein_cleaning_summary.json`：全局清洗统计。\n\n")
        handle.write("## 后续用途\n\n")
        handle.write("该严格 protein 正样本集合将作为第一版 R gene vs non-R gene benchmark 的正样本来源。后续需要构建负样本并做同源去冗余后，才能进入正式训练和评估。\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
