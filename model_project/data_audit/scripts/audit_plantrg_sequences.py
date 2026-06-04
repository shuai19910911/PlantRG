#!/usr/bin/env python3
import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


DNA_ALLOWED = set("ACGTUNacgtun")
AA_ALLOWED = set("ABCDEFGHIKLMNPQRSTVWXYZJUO*abcdefghiklmnpqrstvwxyzjuo*")


def parse_args():
    parser = argparse.ArgumentParser(description="Audit PlantRG CDS/protein FASTA files.")
    parser.add_argument("--manifest", default="metadata/plantrg_full_manifest.csv")
    parser.add_argument("--seq-root", default="downloads/sequences")
    parser.add_argument("--outdir", default="model_project/data_audit/results")
    parser.add_argument("--threads", type=int, default=1)
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


def n50(lengths):
    if not lengths:
        return 0
    total = sum(lengths)
    acc = 0
    for length in sorted(lengths, reverse=True):
        acc += length
        if acc >= total / 2:
            return length
    return 0


def percentile(lengths, p):
    if not lengths:
        return 0
    xs = sorted(lengths)
    idx = (len(xs) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return xs[int(idx)]
    return xs[lo] * (hi - idx) + xs[hi] * (idx - lo)


def audit_file(task):
    species, seq_type, filename, seq_root, record_dir = task
    fasta_path = Path(seq_root) / seq_type / filename
    record_dir = Path(record_dir) / seq_type
    record_dir.mkdir(parents=True, exist_ok=True)
    record_path = record_dir / f"{filename}.records.tsv"

    allowed = DNA_ALLOWED if seq_type == "CDS" else AA_ALLOWED
    lengths = []
    invalid_records = 0
    duplicate_ids = 0
    empty_records = 0
    cds_not_mod3 = 0
    cds_no_start_atg = 0
    cds_no_terminal_stop = 0
    protein_has_stop = 0
    ids_seen = set()
    id_list = []

    with record_path.open("w", newline="") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=[
                "species",
                "type",
                "filename",
                "seq_id",
                "length",
                "invalid_chars",
                "is_duplicate_id",
                "cds_mod3",
                "cds_start_atg",
                "cds_terminal_stop",
                "protein_contains_stop",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        for seq_id, desc, seq in read_fasta(fasta_path):
            length = len(seq)
            lengths.append(length)
            invalid = "".join(sorted(set(seq) - allowed))
            is_dup = seq_id in ids_seen
            if is_dup:
                duplicate_ids += 1
            ids_seen.add(seq_id)
            id_list.append(seq_id)
            if length == 0:
                empty_records += 1
            if invalid:
                invalid_records += 1

            cds_mod3 = ""
            cds_start_atg = ""
            cds_terminal_stop = ""
            protein_contains_stop = ""
            if seq_type == "CDS":
                upper = seq.upper()
                cds_mod3 = int(length % 3 == 0)
                cds_start_atg = int(upper.startswith("ATG"))
                cds_terminal_stop = int(upper[-3:] in {"TAA", "TAG", "TGA"} if length >= 3 else False)
                if not cds_mod3:
                    cds_not_mod3 += 1
                if not cds_start_atg:
                    cds_no_start_atg += 1
                if not cds_terminal_stop:
                    cds_no_terminal_stop += 1
            else:
                protein_contains_stop = int("*" in seq)
                if protein_contains_stop:
                    protein_has_stop += 1

            writer.writerow(
                {
                    "species": species,
                    "type": seq_type,
                    "filename": filename,
                    "seq_id": seq_id,
                    "length": length,
                    "invalid_chars": invalid,
                    "is_duplicate_id": int(is_dup),
                    "cds_mod3": cds_mod3,
                    "cds_start_atg": cds_start_atg,
                    "cds_terminal_stop": cds_terminal_stop,
                    "protein_contains_stop": protein_contains_stop,
                }
            )

    count = len(lengths)
    summary = {
        "species": species,
        "type": seq_type,
        "filename": filename,
        "path": str(fasta_path),
        "records": count,
        "total_length": sum(lengths),
        "min_length": min(lengths) if lengths else 0,
        "mean_length": statistics.mean(lengths) if lengths else 0,
        "median_length": statistics.median(lengths) if lengths else 0,
        "p05_length": percentile(lengths, 0.05),
        "p95_length": percentile(lengths, 0.95),
        "max_length": max(lengths) if lengths else 0,
        "n50_length": n50(lengths),
        "invalid_records": invalid_records,
        "duplicate_ids": duplicate_ids,
        "empty_records": empty_records,
        "cds_not_mod3": cds_not_mod3,
        "cds_no_start_atg": cds_no_start_atg,
        "cds_no_terminal_stop": cds_no_terminal_stop,
        "protein_has_stop": protein_has_stop,
        "record_table": str(record_path),
    }
    return summary, id_list


def write_tsv(path, rows, fieldnames):
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    tables_dir = outdir / "tables"
    record_dir = outdir / "per_file_records"
    tables_dir.mkdir(parents=True, exist_ok=True)

    with open(args.manifest, newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))

    tasks = [
        (
            row["species"],
            row["type"],
            row["filename"],
            args.seq_root,
            str(record_dir),
        )
        for row in manifest_rows
    ]

    summaries = []
    ids_by_species_type = defaultdict(set)
    workers = max(1, min(args.threads, len(tasks)))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(audit_file, task) for task in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            summary, ids = future.result()
            summaries.append(summary)
            ids_by_species_type[(summary["species"], summary["type"])].update(ids)
            if i % 100 == 0 or i == len(futures):
                print(f"audited {i}/{len(futures)} files", flush=True)

    summaries.sort(key=lambda r: (r["species"], r["type"], r["filename"]))
    summary_fields = [
        "species",
        "type",
        "filename",
        "path",
        "records",
        "total_length",
        "min_length",
        "mean_length",
        "median_length",
        "p05_length",
        "p95_length",
        "max_length",
        "n50_length",
        "invalid_records",
        "duplicate_ids",
        "empty_records",
        "cds_not_mod3",
        "cds_no_start_atg",
        "cds_no_terminal_stop",
        "protein_has_stop",
        "record_table",
    ]
    write_tsv(tables_dir / "file_summary.tsv", summaries, summary_fields)

    species_rows = []
    species_set = sorted({row["species"] for row in manifest_rows})
    by_species_type_summary = defaultdict(list)
    for row in summaries:
        by_species_type_summary[(row["species"], row["type"])].append(row)
    for species in species_set:
        cds_rows = by_species_type_summary.get((species, "CDS"), [])
        pro_rows = by_species_type_summary.get((species, "protein"), [])
        cds_ids = ids_by_species_type.get((species, "CDS"), set())
        pro_ids = ids_by_species_type.get((species, "protein"), set())
        species_rows.append(
            {
                "species": species,
                "cds_records": sum(int(r["records"]) for r in cds_rows),
                "protein_records": sum(int(r["records"]) for r in pro_rows),
                "paired_exact_ids": len(cds_ids & pro_ids),
                "cds_only_ids": len(cds_ids - pro_ids),
                "protein_only_ids": len(pro_ids - cds_ids),
                "cds_total_length": sum(int(r["total_length"]) for r in cds_rows),
                "protein_total_length": sum(int(r["total_length"]) for r in pro_rows),
            }
        )
    write_tsv(
        tables_dir / "species_pairing_summary.tsv",
        species_rows,
        [
            "species",
            "cds_records",
            "protein_records",
            "paired_exact_ids",
            "cds_only_ids",
            "protein_only_ids",
            "cds_total_length",
            "protein_total_length",
        ],
    )

    all_record_path = tables_dir / "all_records.tsv"
    with all_record_path.open("w") as out:
        wrote_header = False
        for record_path in sorted(record_dir.rglob("*.records.tsv")):
            with record_path.open() as handle:
                header = next(handle)
                if not wrote_header:
                    out.write(header)
                    wrote_header = True
                for line in handle:
                    out.write(line)

    global_summary = {
        "manifest_files": len(manifest_rows),
        "audited_files": len(summaries),
        "species": len(species_set),
        "cds_files": sum(1 for row in summaries if row["type"] == "CDS"),
        "protein_files": sum(1 for row in summaries if row["type"] == "protein"),
        "cds_records": sum(int(row["records"]) for row in summaries if row["type"] == "CDS"),
        "protein_records": sum(int(row["records"]) for row in summaries if row["type"] == "protein"),
        "invalid_record_files": sum(1 for row in summaries if int(row["invalid_records"]) > 0),
        "duplicate_id_files": sum(1 for row in summaries if int(row["duplicate_ids"]) > 0),
        "empty_record_files": sum(1 for row in summaries if int(row["empty_records"]) > 0),
        "species_with_unpaired_ids": sum(
            1
            for row in species_rows
            if int(row["cds_only_ids"]) > 0 or int(row["protein_only_ids"]) > 0
        ),
        "all_records_table": str(all_record_path),
    }
    (outdir / "global_summary.json").write_text(json.dumps(global_summary, indent=2, ensure_ascii=False))

    report = [
        "# PlantRG 数据审计报告",
        "",
        "## 全局概览",
        "",
        f"- manifest 文件数：{global_summary['manifest_files']}",
        f"- 审计文件数：{global_summary['audited_files']}",
        f"- 物种数：{global_summary['species']}",
        f"- CDS 文件数：{global_summary['cds_files']}",
        f"- protein 文件数：{global_summary['protein_files']}",
        f"- CDS 记录数：{global_summary['cds_records']}",
        f"- protein 记录数：{global_summary['protein_records']}",
        f"- 含异常字符的文件数：{global_summary['invalid_record_files']}",
        f"- 含重复 ID 的文件数：{global_summary['duplicate_id_files']}",
        f"- 含空序列的文件数：{global_summary['empty_record_files']}",
        f"- CDS/protein 存在未配对 ID 的物种数：{global_summary['species_with_unpaired_ids']}",
        "",
        "## 主要输出文件",
        "",
        f"- `tables/file_summary.tsv`：每个 FASTA 文件的统计。",
        f"- `tables/species_pairing_summary.tsv`：每个物种 CDS/protein ID 配对情况。",
        f"- `tables/all_records.tsv`：每条序列的基础审计信息。",
        f"- `global_summary.json`：全局统计的机器可读版本。",
    ]
    (outdir / "数据审计报告.md").write_text("\n".join(report) + "\n")
    print(json.dumps(global_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
