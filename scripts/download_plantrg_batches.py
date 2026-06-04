#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "http://plantrg.bio2db.com"
HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "PlantRG-local-mirror/1.0",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Download PlantRG data as official tar.gz batches.")
    parser.add_argument("--manifest", default="metadata/plantrg_full_manifest.csv")
    parser.add_argument("--outdir", default="downloads/batches")
    parser.add_argument("--type", choices=["CDS", "protein", "all"], default="all")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--retries", type=int, default=4)
    return parser.parse_args()


def load_records(path, data_type):
    with open(path, newline="") as handle:
        records = list(csv.DictReader(handle))
    if data_type != "all":
        records = [r for r in records if r["type"] == data_type]
    return records


def chunks(items, size):
    for start in range(0, len(items), size):
        yield start // size + 1, items[start : start + size]


def request_batch_tar(filenames, retries):
    body = urlencode([("get_break", name) for name in filenames]).encode()
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(BASE + "/Download-Select", data=body, headers=HEADERS, method="POST")
            with urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["download_file"]
        except Exception as exc:
            last_error = exc
            time.sleep(min(30, 2 * attempt))
    raise RuntimeError(f"Download-Select failed: {last_error!r}")


def tar_member_count(path):
    with tarfile.open(path, "r:gz") as tar:
        return len([m for m in tar.getmembers() if m.isfile()])


def prepare_batches(batches, data_type, outdir, retries):
    batch_dir = Path(outdir) / data_type
    batch_dir.mkdir(parents=True, exist_ok=True)
    prepared = []
    manifest_path = Path("metadata") / f"plantrg_batch_manifest_{data_type}.tsv"
    with manifest_path.open("w") as manifest:
        for batch_no, records in batches:
            marker = batch_dir / f"batch_{batch_no:04d}.done"
            if marker.exists():
                target_name, _size, _members = marker.read_text().strip().split("\t")
                prepared.append((batch_no, records, target_name, True))
                manifest.write(f"{batch_no}\tDONE\t{target_name}\t{len(records)}\n")
                continue
            server_name = request_batch_tar([r["filename"] for r in records], retries)
            target_name = f"batch_{batch_no:04d}_{server_name}"
            prepared.append((batch_no, records, target_name, False))
            manifest.write(f"{batch_no}\tNEW\t{target_name}\t{len(records)}\n")
            manifest.flush()
            # The server uses low-entropy timestamp-like names; spacing avoids collisions.
            time.sleep(1.2)
            if batch_no % 10 == 0:
                print(f"prepared {batch_no}/{len(batches)} {data_type} batches", flush=True)
    return prepared


def download_batch(batch_no, records, target_name, already_done, outdir, retries):
    data_type = records[0]["type"] if records else "empty"
    batch_dir = Path(outdir) / data_type
    batch_dir.mkdir(parents=True, exist_ok=True)
    marker = batch_dir / f"batch_{batch_no:04d}.done"
    if already_done and marker.exists():
        target_name, size, members = marker.read_text().strip().split("\t")
        return batch_no, "SKIP", target_name, int(size), int(members)

    target = batch_dir / target_name
    if target.exists() and target.stat().st_size <= 10000:
        target.unlink()
    server_name = target_name.split("_", 2)[2]
    url = BASE + "/" + server_name

    last_status = None
    for attempt in range(1, retries + 1):
        cmd = [
            "curl",
            "-L",
            "--retry",
            str(retries),
            "--retry-delay",
            "3",
            "-C",
            "-",
            "-o",
            str(target),
            url,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            last_status = f"curl:{result.returncode}:{result.stderr[-200:]}"
        else:
            try:
                members = tar_member_count(target)
                size = target.stat().st_size
                marker.write_text(f"{target.name}\t{size}\t{members}\n")
                return batch_no, "OK", target.name, size, members
            except Exception as exc:
                last_status = f"tar:{exc!r}"
        if target.exists() and target.stat().st_size <= 10000:
            target.unlink()
        time.sleep(min(60, 5 * attempt))

    size = target.stat().st_size if target.exists() else 0
    return batch_no, f"FAIL:{last_status}", target.name, size, 0


def main():
    args = parse_args()
    records = load_records(args.manifest, args.type)
    batches = list(chunks(records, args.batch_size))
    data_type = args.type if args.type != "all" else "all"
    prepared = prepare_batches(batches, data_type, args.outdir, args.retries)
    log_path = Path("metadata") / f"plantrg_batch_download_{args.type}.log"
    failures = []
    total_bytes = 0

    with log_path.open("a") as log, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                download_batch,
                batch_no,
                batch_records,
                target_name,
                already_done,
                args.outdir,
                args.retries,
            ): (
                batch_no,
                batch_records,
            )
            for batch_no, batch_records, target_name, already_done in prepared
        }
        done = 0
        for future in as_completed(futures):
            batch_no, status, tar_name, size, members = future.result()
            done += 1
            if status.startswith("FAIL"):
                failures.append((batch_no, status))
            else:
                total_bytes += size
            log.write(f"{batch_no}\t{status}\t{tar_name}\t{size}\t{members}\n")
            log.flush()
            if done % 10 == 0 or done == len(batches):
                print(
                    f"{args.type}: {done}/{len(batches)} batches, "
                    f"failures={len(failures)}, bytes={total_bytes}",
                    flush=True,
                )

    fail_path = Path("metadata") / f"plantrg_batch_download_{args.type}_failures.tsv"
    with fail_path.open("w") as handle:
        for batch_no, status in failures:
            handle.write(f"{batch_no}\t{status}\n")

    print(f"records={len(records)}")
    print(f"batches={len(batches)}")
    print(f"failures={len(failures)}")
    print(f"bytes={total_bytes}")


if __name__ == "__main__":
    main()
