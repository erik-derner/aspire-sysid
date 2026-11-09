"""Runs all PySR reference fits: three tasks, two settings, seeds 1 to 5 (30 calls of fit_pysr.py).

Each call is one single-core process; ``--workers`` of them run at a time. A call whose model
file exists is skipped, so that the script can be started again after an interruption. The
console output of a call is written to ``<task>/pysr-<setting>/raw/s<seed>/console.log``. After
the fits, the pool files are written.

    <pysr-python> experiments/references/run_pysr_all.py --workers 8
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
TASKS = ["turtlebot", "fermenter-pressure", "friction-driven"]
SETTINGS = ["default", "matched"]
SEEDS = [1, 2, 3, 4, 5]


def run(job: tuple[str, str, int]) -> tuple[tuple[str, str, int], int, float]:
    task, setting, seed = job
    model = HERE / task / f"pysr-{setting}" / "models" / f"ReferencePysr{setting.capitalize()}S{seed}.json"
    if model.exists():
        return job, 0, 0.0
    raw = HERE / task / f"pysr-{setting}" / "raw" / f"s{seed}"
    raw.mkdir(parents=True, exist_ok=True)
    start = time.time()
    with open(raw / "console.log", "w", encoding="utf-8") as log:
        code = subprocess.call([sys.executable, "-W", "ignore", str(HERE / "fit_pysr.py"), task, setting, str(seed)],
                               stdout=log, stderr=subprocess.STDOUT)
    return job, code, time.time() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    jobs = [(t, s, seed) for s in SETTINGS for seed in SEEDS for t in TASKS]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for job, code, seconds in pool.map(run, jobs):
            print(f"{job[0]} {job[1]} seed {job[2]}: exit {code}, {seconds:.0f} s", flush=True)
    for task in TASKS:
        for setting in SETTINGS:
            subprocess.call([sys.executable, str(HERE / "fit_pysr.py"), task, setting, "--pool"])


if __name__ == "__main__":
    main()
