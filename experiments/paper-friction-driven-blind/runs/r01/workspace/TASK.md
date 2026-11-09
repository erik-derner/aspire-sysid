# Task: Identification task jdhj

## 1 System and intended use

The task gives no description of the system.

The task states no intended use of the model.

## 2 Data

`data/train.csv` holds 3522 samples of training data: 13 trajectories of 450, 450, 300, 300, 442, 442, 442, 141, 141, 141, 91, 91, 91 consecutive samples; the column `trajectory` holds the trajectory number. `data/val.csv` holds 1192 samples of validation data: 3 trajectories of 450, 300, 442 consecutive samples; the column `trajectory` holds the trajectory number. Whether and how you use the validation data is your decision. Row k+1 of a trajectory is the sample that follows row k; different trajectories are separate experiments. The sampling period is T_s = 0.01 s.

| Column | Role | Unit | Training range | Description |
|---|---|---|---|---|
| `y` | state, scored output | not supplied | not declared | not supplied |
| `x1` | state | not supplied | not declared | not supplied |
| `x2` | input | not supplied | not declared | not supplied |
| `dx1` | sampled time derivative of `x1` | not supplied | not declared | not supplied |

The task does not state the units. The task does not describe the columns.

## 3 What you deliver

A candidate is a continuous-time model of 2 closed-form expressions, `dy` and `dx1`: the time derivatives of the states `y` and `x1` as functions of `y`, `x1` and `x2`. The column `dx1` is a possible fitting target for the derivative of `x1`; it is not an argument of the expressions. `FORMAT.md` states how an expression is written and what it may contain.

Write one file per candidate, `models/<label>.json`; `FORMAT.md` describes the file and gives an example. Write also `models/pool.json`, which lists the labels of your candidates in the order in which they are to be evaluated. You can recommend one candidate that you consider the best-performing. `models/pool.json` then names that candidate and gives your reason. Run `python check_submission.py` to check your files: it prints every error with its location, so that you can correct it.

At most 10 candidates are evaluated, in the order of `models/pool.json`. Consider various identification approaches, for example physically motivated structures, symbolic-regression search or sparse regression; before fitting, list the approaches and the model families you will try. Build the pool from structurally different model families, not from variations of one form. Examine the residuals of your best candidates and try structures that can represent what they show. Include only candidates you would defend as a model of the system.

## 4 Evaluation

The harness, the software that runs this task, evaluates every candidate on test data that you cannot access. For each test trajectory it starts from the first logged state and integrates the expressions with the classical fourth-order Runge–Kutta method, one step per sampling period, with the logged inputs held constant between samples; a simulated state is never replaced by a later measurement. The score is the root mean squared error (RMSE) between simulated and logged `y` over all test samples after the first of each trajectory. An evaluation fails when a value is not finite, when `y` leaves [-1000, 1000] or `x1` leaves [-1000, 1000], or when it takes longer than 60 s.

## 5 Limits and completion

One round: 60 turns, 3600 s of execution time, 10 USD; a turn is one response of yours. When the files pass the check, send the exact message DONE. If the harness's check of the files then fails, you receive its report and may correct the files once. If a limit ends the round earlier, the complete candidate files are evaluated.
