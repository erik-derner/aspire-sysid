# Reference models

A **reference model** is a model of a task that is obtained without the agent and scored by the
harness on the same sealed test data and with the same evaluation settings as the candidates of
the agent. The harness is
the software of ASPIRE; the agent is the language model that identifies models. The reference
models give the test scores of the agent's models a value to compare with. They are not
presented as competing methods.

The manuscript reports only the
PySINDy and the PySR models and not the models written by hand. The evaluations of the
hand-written models stay in this folder as records; `experiments/paper/collect_results.py` does
not collect them.

## Kinds of reference models

Per described task (`turtlebot`, `friction-driven`, `fermenter-pressure`):

1. **Physical model**, written by hand. Its structure was fixed before any estimation; its
   parameters minimize the root mean squared error (RMSE) of the simulated output on the
   training data.
2. **Sparse-regression model**: sparse identification of nonlinear dynamics (SINDy) with PySINDy
   2.1.0, polynomial library of degree 2, sequentially thresholded least squares.
3. **Symbolic-regression model**: PySR 1.5.10 (search over expression trees by regularized
   evolution).

Each tool is used with two settings:

- **default**: the settings of the package (PySINDy: threshold 0.1; PySR: operators `+ - * /`,
  100 iterations, the equation selected by the package, `model_selection="best"`);
- **matched**: closer to what the agent is given. PySINDy: the threshold is selected from a grid
  (`turtlebot`: 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001; the continuous-time tasks: 1, 0.5
  and 0.2 times the powers of ten from 10 to 1e-6). PySR: the unary functions
  `sin cos tanh exp log sqrt abs sign`, which the tasks permit, are added, and the equation is
  selected from the Pareto front of the search. In both, the selection minimizes the RMSE of
  the simulated output on the training data, computed as the harness computes it.

The tools fit the targets that the task offers, on the training data only: for `turtlebot` the
next value of each state on the 442 of 447 one-step transitions in which the logged heading
does not wrap; for `fermenter-pressure` the column `dp`; for `friction-driven` the column
`domega`, with `dtheta = omega` written as the task prescribes (requirement R1). The validation
data of the two continuous-time tasks are not used. Every constant found by a tool is written
as a named parameter of type `fitted`.

The physical models and the PySINDy models are deterministic and are evaluated once. PySR is
stochastic and is run with the seeds 1 to 5 (`random_state`, `deterministic=True`,
`parallelism="serial"`, so that a seed reproduces its result); its scores are reported as mean
± sample standard deviation (divisor n − 1) over the seeds with a finite score, with n.

The blind tasks (`task-kt5o`, `task-jdhj`, `task-qtqm`) hold the same data as their described
tasks, and the tools use no description, so the scores below apply to the blind tasks unchanged.

## Files

- `common.py`: reading of the training data, simulation as in the harness, writing of model
  files, the PySINDy fit of the continuous-time tasks;
- `<task>/fit_references.py`: the physical model and the two PySINDy models, written to
  `<task>/models/`; run with the Python environment of the agent;
- `fit_pysr.py <task> <default|matched> <seed>`: one PySR model, written to
  `<task>/pysr-<setting>/models/`, with the Pareto front and a record of the search in
  `<task>/pysr-<setting>/raw/s<seed>/`; `run_pysr_all.py` runs the 30 calls. Run with a Python
  environment that holds PySR and Julia (for the reported models: PySR 1.5.10,
  Julia 1.11.9, NumPy 2.5.2, SymPy; the agent's environment has no Julia);
- `<folder>/evaluation/`: the report of
  `aspire evaluate tasks/<task> <folder>/models --out <folder>/evaluation`.

No script reads the test data. A pool holds at most 10 models (the pool limit of the tasks),
which is why the PySR models have their own pools.

## Results

Test score S: pooled RMSE of the simulated output over the scored test samples. Training error:
the same measure on the training data (`turtlebot`: in segments of
25 simulated samples, the horizon of the task; the other tasks: whole trajectories). Both are
computed by the harness (version 0.1.0.dev0). All 39 models passed
the checks; none failed numerically.

A training error and a test score do not depend on the requirements of a task.
The tools were not given the requirements. Outcomes for the 13 models of `friction-driven`
(`tasks/friction-driven/provenance.md` states the requirements):

| Models of `friction-driven` | R1 | R2 (`domega*theta <= 0` at omega = 0, u = 0) | R3 (`domega` does not decrease with `u`) |
|---|---|---|---|
| `ReferencePhysical` | proof | proof | proof |
| `ReferenceSindy`, `ReferenceSindyThreshold` | proof | counterexample (theta = 0.006 and 0.012 rad; `domega*theta` = 0.0016 and 0.0012 rad²/s²) | proof |
| `ReferencePysrDefaultS1` to `S5` | proof | counterexample (theta = -2.945 rad; `domega*theta` = 82 to 100 rad²/s²) | proof |
| `ReferencePysrMatchedS1` to `S5` | proof | counterexample (theta = 0.049 to 0.098 rad; `domega*theta` = 0.008 to 0.071 rad²/s²) | proof |

All 12 models of PySINDy and PySR have a demonstrated violation of R2 and are therefore not
eligible as a candidate would be; the scores are reported nevertheless, with this fact stated
beside them. Each of these models contains a constant term or a polynomial in the angle, so that at
rest with zero voltage its acceleration points away from the hanging equilibrium at some angles.
The counterexample is the point that the harness reports, not the largest violation.
`fermenter-pressure` has requirements in natural language only, which the harness does not verify;
its 13 models and the 13 models of `turtlebot` are eligible.

### `turtlebot` (output `x`, m; 447 scored training samples, 298 scored test samples in 12 trajectories)

| Model | Setting | Fitted parameters | Training error (m) | Test score S (m) |
|---|---|---|---|---|
| `ReferenceUnicycle` (physical) | - | 2 | 0.0396 | 0.0445 |
| `ReferenceSindy` | default, threshold 0.1 | 3 | 0.2217 | 0.2140 |
| `ReferenceSindyThreshold` | matched, threshold 0.001 | 55 | 0.0446 | 0.1530 |
| `ReferencePysrDefaultS1` to `S5` | default | 6 to 8 | 0.065 ± 0.024 (n = 5) | 0.0504 ± 0.0068 (n = 5; 0.0458 to 0.0612) |
| `ReferencePysrMatchedS1` to `S5` | matched | 8 to 14 | 0.0263 ± 0.0033 (n = 5) | 0.056 ± 0.013 (n = 5; 0.0438 to 0.0761) |

Physical model: `x_next = x + p_v*v_f*cos(phi)`, `y_next = y + p_v*v_f*sin(phi)`,
`phi_next = phi + p_w*v_a`, with `p_v` = 0.1657 s and `p_w` = 0.1584 s (Nelder–Mead method,
SciPy 1.18.1, started at the sampling period 0.2 s).

### `friction-driven` (output `theta`, rad; 3509 scored training samples in 13 trajectories, 978 scored test samples in 4 trajectories)

| Model | Setting | Fitted parameters | Training error (rad) | Test score S (rad) |
|---|---|---|---|---|
| `ReferencePhysical` | - | 4 | 0.0656 | 0.0402 |
| `ReferenceSindy` | default, threshold 0.1 | 8 | 0.1957 | 0.2668 |
| `ReferenceSindyThreshold` | matched, threshold 0.02 | 10 | 0.1934 | 0.2692 |
| `ReferencePysrDefaultS1` to `S5` | default | 4 | 0.13909 ± 0.00017 (n = 5) | 0.14404 ± 0.00098 (n = 5; 0.1424 to 0.1449) |
| `ReferencePysrMatchedS1` to `S5` | matched | 5 to 6 | 0.0666 ± 0.0070 (n = 5) | 0.0363 ± 0.0039 (n = 5; 0.0335 to 0.0431) |

Physical model: `dtheta = omega`,
`domega = -a*sin(theta) - b*omega - c*tanh(s*omega) + k*u`, with `a` = 110.39 rad/s²,
`b` = 1.759 1/s, `c` = 20.21 rad/s², `k` = 28.12 rad/(s² V) fitted (Nelder–Mead method, SciPy
1.18.1, started at the least-squares fit of the column `domega`: 105.49, 1.812, 17.01, 26.27)
and `s` = 10 s/rad fixed. Per-trajectory test RMSE: 0.0317 and 0.0586 rad (driven), 0.0157 and
0.0276 rad (free decay). The structure is that of the model recorded in
`tasks/friction-driven/provenance.md`.

### `fermenter-pressure` (output `p`, bar; 1451 scored training samples, 1209 scored test samples, one trajectory each)

| Model | Setting | Fitted parameters | Training error (bar) | Test score S (bar) |
|---|---|---|---|---|
| `ReferencePhysical` | - | 3 | 0.0272 | 0.0267 |
| `ReferenceSindy` | default, threshold 0.1 | 0 | 0.4020 | 0.2631 |
| `ReferenceSindyThreshold` | matched, threshold 2e-6 | 10 | 0.0309 | 0.0284 |
| `ReferencePysrDefaultS1` to `S5` | default | 3 to 5 | 0.0489 ± 0.0056 (n = 5) | 0.0418 ± 0.0054 (n = 5; 0.0350 to 0.0483) |
| `ReferencePysrMatchedS1` to `S5` | matched | 1 to 5 | 0.10 ± 0.11 (n = 5) | 0.075 ± 0.063 (n = 5; 0.0276 to 0.1850) |

Physical model: `dp = a*flow - b*(1 - valve/c_v)*sqrt(Max(p - p_a, 0))`, an inflow proportional
to the air flow rate and an orifice outflow with a linear valve characteristic, with
`a` = 0.001336 bar min/(l s), `b` = 0.1835 bar^0.5/s and `p_a` = 1.027 bar fitted (Nelder–Mead
method, started at `p_a` = 1 bar and the least-squares fit of the column `dp`) and `c_v` = 100
(% closed) fixed.

## Observations

1. The evaluation path is verified by `ReferenceUnicycle`, which reproduces the test score of a
   separate evaluation of the same unicycle model (S = 0.0445 m). For the nine physical and PySINDy
   models, the training error computed by the fitting script equals that of the harness.
2. PySINDy at the default threshold removes every term with an input in `turtlebot` and every
   term in `fermenter-pressure` (`dp = 0`), because the threshold 0.1 is an absolute bound on
   the coefficients and does not depend on the units. With the selected threshold it reaches
   S = 0.0284 bar on `fermenter-pressure`, close to the physical model; on `turtlebot` and
   `friction-driven` the polynomial library of degree 2 has no trigonometric function and the
   test score stays at 0.15 m and 0.27 rad.
3. PySR at its defaults (no unary function) reaches S = 0.050 ± 0.007 m on `turtlebot`, where
   polynomial and rational terms in the heading approximate the trigonometric functions over
   the range of the data. On `friction-driven` all five seeds give nearly the same polynomial
   model (S = 0.144 rad).
4. With the matched setting PySR finds `sin(theta)` and `tanh` terms on `friction-driven`, and
   its test score (0.0363 ± 0.0039 rad) is below that of the physical model (0.0402 rad) in four
   of five seeds. On `fermenter-pressure` the matched setting is worse than the default on
   average and varies strongly between the seeds (0.028 to 0.185 bar): equations with a small
   error of the derivative drift or fail in simulation, and for seed 2 the equation with the
   smallest training simulation error on the front is a constant (`dp = ca1`).
5. On `turtlebot` the matched PySR models have a lower training error than the default ones
   (0.026 against 0.065 m) and a higher test score (0.056 against 0.050 m): the selection by the
   training simulation error prefers equations that fit the three training trajectories and do
   not transfer.
6. A deterministic single-core PySR search took 4 to 16 min per target at the defaults and up to
   31 min (`friction-driven`, 3522 rows) at the matched setting.
7. In the PySINDy fits of `turtlebot`, five of the 447 training transitions are left out because
   the logged heading wraps at ±π.
