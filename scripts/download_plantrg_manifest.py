#!/usr/bin/env python3
import argparse
import csv
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen


def parse_args():
    parser = argparse.ArgumentParser(description="Download PlantRG files from manifest.")
    parser.add_argument("--manifest", default="metadata/plantrg_full_manifest.csv")
    parser.add_argument("--outdir", default="downloads/sequences")
    parser.add_argument("--type", choices=["CDS", "protein", "all"], default="all")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--progress-md", default="")
    parser.add_argument("--md-every", type=int, default=100)
    return parser.parse_args()


def load_records(path, data_type):
    with open(path, newline="") as handle:
        records = list(csv.DictReader(handle))
    if data_type != "all":
        records = [r for r in records if r["type"] == data_type]
    return records


def download_one(record, outdir, retries):
    target_dir = Path(outdir) / record["type"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / record["filename"]
    part = target.with_suffix(target.suffix + ".part")

    if target.exists() and target.stat().st_size > 0:
        return record["filename"], "SKIP", target.stat().st_size

    req = Request(record["url"], headers={"User-Agent": "PlantRG-local-mirror/1.0"})
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with urlopen(req, timeout=180) as response, part.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            if part.stat().st_size == 0:
                raise RuntimeError("empty download")
            part.replace(target)
            return record["filename"], "OK", target.stat().st_size
        except Exception as exc:
            last_error = exc
            if part.exists():
                part.unlink()
            time.sleep(min(30, 2 * attempt))
    return record["filename"], f"FAIL:{last_error!r}", 0


def main():
    args = parse_args()
    records = load_records(args.manifest, args.type)
    log_path = Path("metadata") / f"plantrg_download_{args.type}.log"
    failures = []
    total_bytes = 0

    with log_path.open("a") as log, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(download_one, record, args.outdir, args.retries): record
            for record in records
        }
        done = 0
        for future in as_completed(futures):
            filename, status, size = future.result()
            done += 1
            if status.startswith("FAIL"):
                failures.append((filename, status))
            else:
                total_bytes += size
            log.write(f"{filename}\t{status}\t{size}\n")
            log.flush()
            if done % 50 == 0 or done == len(records):
                print(
                    f"{args.type}: {done}/{len(records)} files, "
                    f"failures={len(failures)}, bytes={total_bytes}",
                    flush=True,
                )
            if args.progress_md and (done % args.md_every == 0 or done == len(records)):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with Path(args.progress_md).open("a") as md:
                    md.write(
                        f"- {ts} CST：逐文件下载 `{args.type}` 进度 "
                        f"{done}/{len(records)}，失败 {len(failures)}，"
                        f"当前累计成功/跳过文件大小 {total_bytes} bytes。\n"
                    )

    fail_path = Path("metadata") / f"plantrg_download_{args.type}_failures.tsv"
    with fail_path.open("w") as handle:
        for filename, status in failures:
            handle.write(f"{filename}\t{status}\n")

    print(f"records={len(records)}")
    print(f"failures={len(failures)}")
    print(f"bytes={total_bytes}")


if __name__ == "__main__":
    main()
