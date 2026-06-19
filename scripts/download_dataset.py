#!/usr/bin/env python3
"""
Download MRTA-Benchmark (APEX-MR) dataset.

This script clones the APEX-MR repository and copies the LEGO assembly
task files to data/datasets/MRTA-Benchmark/.

Usage:
    python scripts/download_dataset.py

The dataset is NOT committed to git (too large / external dependency).
After downloading, the task files are available at:
    data/datasets/MRTA-Benchmark/*.json
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "data" / "datasets" / "MRTA-Benchmark"
TEMP_DIR = Path("/tmp") / "APEX-MR"
REPO_URL = "https://github.com/intelligent-control-lab/APEX-MR.git"
TASK_SUBDIR = Path("config") / "lego_tasks" / "assembly_tasks"


def main():
    print("=" * 60)
    print("MRTA-Benchmark (APEX-MR) Dataset Downloader")
    print("=" * 60)
    print()
    print("Source: https://github.com/intelligent-control-lab/APEX-MR")
    print("Paper:  https://arxiv.org/abs/2503.15836")
    print("License: See APEX-MR/LICENSE")
    print()

    # Step 1: Clone repo (shallow)
    if TEMP_DIR.exists():
        print(f"[1/3] Repo already exists at {TEMP_DIR}, pulling latest...")
        subprocess.run(["git", "-C", str(TEMP_DIR), "pull", "--ff-only"],
                       capture_output=True)
    else:
        print(f"[1/3] Cloning APEX-MR repo (shallow)...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(TEMP_DIR)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: Failed to clone repo: {result.stderr}")
            sys.exit(1)

    # Step 2: Copy task files
    src_dir = TEMP_DIR / TASK_SUBDIR
    if not src_dir.exists():
        print(f"ERROR: Task directory not found: {src_dir}")
        sys.exit(1)

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    json_files = list(src_dir.glob("*.json"))
    print(f"[2/3] Copying {len(json_files)} task files to {DATASET_DIR}/")

    for f in json_files:
        dst = DATASET_DIR / f.name
        shutil.copy2(f, dst)
        print(f"  ✓ {f.name}")

    # Step 3: Verify
    print(f"\n[3/3] Verification")
    loaded_files = list(DATASET_DIR.glob("*.json"))
    print(f"  {len(loaded_files)} task files in {DATASET_DIR}/")
    print()

    # List tasks
    print("Available tasks:")
    for f in sorted(loaded_files):
        size = f.stat().st_size
        print(f"  {f.stem:<20s} ({size:,} bytes)")

    print()
    print("=" * 60)
    print("Download complete!")
    print()
    print("Usage in code:")
    print("  from evaluation.mrta_loader import MRTABenchmarkLoader")
    print(f'  loader = MRTABenchmarkLoader("{DATASET_DIR}")')
    print("  tasks = loader.load_all()")
    print()
    print("Usage in CLI:")
    print(f"  python scripts/evaluate.py --dataset {DATASET_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
