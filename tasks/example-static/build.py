"""Generate the synthetic data of the example task ``example-static`` (tasks/GUIDE.md).

The data are not measurements. They are computed from F = 120*d + 800*d**3 with added Gaussian
noise of standard deviation 0.2 N (numpy.random.default_rng, seed 1), so that the example task
can be run and its result judged. A task of your own needs no such script: place your data files
in data/ and test/ directly. Run: python tasks/example-static/build.py
"""
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def table(d: np.ndarray, rng: np.random.Generator) -> str:
    force = 120.0 * d + 800.0 * d**3 + rng.normal(0.0, 0.2, d.size)
    return "d,F\n" + "".join(f"{a:.4f},{b:.3f}\n" for a, b in zip(d, force))


def main() -> None:
    rng = np.random.default_rng(1)
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "test").mkdir(exist_ok=True)
    train = np.sort(rng.uniform(-0.1, 0.1, 40))
    test = np.sort(rng.uniform(-0.1, 0.1, 20))
    (HERE / "data" / "train.csv").write_text(table(train, rng), encoding="ascii", newline="\n")
    (HERE / "test" / "test_1.csv").write_text(table(test, rng), encoding="ascii", newline="\n")


if __name__ == "__main__":
    main()
