"""Generate the synthetic data of the example task ``example-dynamic`` (tasks/GUIDE.md).

The data are not measurements. They are simulated from h[k+1] = h[k] + T_s*(0.02*u[k] - 0.015*sqrt(h[k]))
with T_s = 1 s, a pump command u that is held for 10 samples and then redrawn uniformly from
[0, 1], and Gaussian noise of standard deviation 0.002 m added to the logged level
(numpy.random.default_rng, seed 2). A task of your own needs no such script: place your data
files in data/ and test/ directly. Run: python tasks/example-dynamic/build.py
"""
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TS = 1.0


def trajectory(n: int, h0: float, rng: np.random.Generator) -> list[tuple[float, float]]:
    h, rows = h0, []
    for k in range(n):
        if k % 10 == 0:
            u = float(rng.uniform(0.0, 1.0))
        rows.append((h + float(rng.normal(0.0, 0.002)), u))
        h = max(h + TS * (0.02 * u - 0.015 * np.sqrt(h)), 0.0)
    return rows


def main() -> None:
    rng = np.random.default_rng(2)
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "test").mkdir(exist_ok=True)
    lines = ["h,u,trajectory\n"]
    for number, h0 in ((1, 0.2), (2, 0.6)):
        lines += [f"{h:.4f},{u:.3f},{number}\n" for h, u in trajectory(80, h0, rng)]
    (HERE / "data" / "train.csv").write_text("".join(lines), encoding="ascii", newline="\n")
    rows = trajectory(60, 0.4, rng)
    (HERE / "test" / "test_1.csv").write_text("h,u\n" + "".join(f"{h:.4f},{u:.3f}\n" for h, u in rows), encoding="ascii", newline="\n")


if __name__ == "__main__":
    main()
