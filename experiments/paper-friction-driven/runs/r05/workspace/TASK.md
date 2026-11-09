# Task: Rotational motion under dry friction, driven by a DC motor (lab rig)

## 1 System and intended use

Data from a real lab rig: a rotational motion system with adjustable dry friction, driven by a voltage-controlled DC motor. A leaf spring presses a felt pad against a rotating disc. The dry-friction level is approximately constant across all recordings; bearing friction (viscous and dry) is present too. Zero angle is the hanging equilibrium. Each row is one sample of the angle theta (rad), the angular velocity omega (rad/s), the motor voltage u (V, an exogenous input) and the angular acceleration domega (rad/s^2), sampled with period T_s = 0.01 s (100 Hz). The state-space model consists of an unknown (sought) closed-form nonlinear expression: domega, the time derivative of omega, as functions of theta, omega and u; and the kinematic identity dtheta = omega as a formal requirement (R1). The training and validation files each contain several separate trajectories of two kinds, marked by the column `trajectory`; a file is not one contiguous trajectory. Driven trajectories start at rest at theta = 0 with a random binary voltage signal applied throughout. Free-response trajectories start from an initial angle with u = 0 throughout; most of their samples are at rest inside the stick band. One model must cover both regimes. The signals come from a digital encoder and numerical differentiation.

Simulation of the angle. The model is integrated from the first (theta, omega) sample of a held-out trajectory, with the recorded voltage u applied and no further corrections, and the simulated angle is compared with the measured one. The held-out trajectories are of both kinds, driven and free response. The model should give stable, accurate long-horizon simulation, including realistic sticking at rest.

## 2 Data

`data/train.csv` holds 3522 samples of training data: 13 trajectories of 450, 450, 300, 300, 442, 442, 442, 141, 141, 141, 91, 91, 91 consecutive samples; the column `trajectory` holds the trajectory number. `data/val.csv` holds 1192 samples of validation data: 3 trajectories of 450, 300, 442 consecutive samples; the column `trajectory` holds the trajectory number. Whether and how you use the validation data is your decision. Row k+1 of a trajectory is the sample that follows row k; different trajectories are separate experiments. The sampling period is T_s = 0.01 s.

| Column | Role | Unit | Training range | Description |
|---|---|---|---|---|
| `theta` | state, scored output | rad | -3.1416 to 3.1416 | angle, state and measured output |
| `omega` | state | rad/s | not declared | angular velocity |
| `u` | input | V | -10 to 10 | motor voltage, exogenous input |
| `domega` | sampled time derivative of `omega` | rad/s^2 | not declared | angular acceleration, the time derivative of omega; a possible fitting target |

## 3 What you deliver

A candidate is a continuous-time model of 2 closed-form expressions, `dtheta` and `domega`: the time derivatives of the states `theta` and `omega` as functions of `theta`, `omega` and `u`. The column `domega` is a possible fitting target for the derivative of `omega`; it is not an argument of the expressions. `FORMAT.md` states how an expression is written and what it may contain.

Write one file per candidate, `models/<label>.json`; `FORMAT.md` describes the file and gives an example. Write also `models/pool.json`, which lists the labels of your candidates in the order in which they are to be evaluated. You can recommend one candidate that you consider the best-performing. `models/pool.json` then names that candidate and gives your reason. Run `python check_submission.py` to check your files: it prints every error with its location, so that you can correct it.

At most 10 candidates are evaluated, in the order of `models/pool.json`. Consider various identification approaches, for example physically motivated structures, symbolic-regression search or sparse regression; before fitting, list the approaches and the model families you will try. Build the pool from structurally different model families, not from variations of one form. Examine the residuals of your best candidates and try structures that can represent what they show. Include only candidates you would defend as a model of the system.

## 4 Evaluation

The harness, the software that runs this task, evaluates every candidate on test data that you cannot access. For each test trajectory it starts from the first logged state and integrates the expressions with the classical fourth-order Runge–Kutta method, one step per sampling period, with the logged inputs held constant between samples; a simulated state is never replaced by a later measurement. The score is the root mean squared error (RMSE) between simulated and logged `theta`, in rad, over all test samples after the first of each trajectory. An evaluation fails when a value is not finite, when `theta` leaves [-1000, 1000] rad or `omega` leaves [-1000, 1000] rad/s, or when it takes longer than 60 s.

## 5 Physical requirements

A formal requirement is a condition on one expression over a domain of its arguments. The tolerance is the admissible violation margin. The harness checks each requirement symbolically or at sampled points; a check at sampled points that finds no violation is not a proof. A demonstrated violation excludes the candidate from the ranking, unless stated otherwise below.

- **R1**: `dtheta` = `omega`; domain: theta ∈ [-3.1416, 3.1416] rad, omega ∈ [-23, 23] rad/s, u ∈ [-10, 10] V; tolerance 0 rad/s.
- **R2**: `domega*theta <= 0`; domain: theta ∈ [-π, π] rad, omega = 0 rad/s, u = 0 V; tolerance 0 rad^2/s^2.
- **R3**: `domega` is increasing in `u`; domain: theta ∈ [-3.1416, 3.1416] rad, omega ∈ [-23, 23] rad/s, u ∈ [-10, 10] V; tolerance 0 rad/(s^2 V).

## 6 Limits and completion

One round: 60 turns, 3600 s of execution time, 10 USD; a turn is one response of yours. When the files pass the check, send the exact message DONE. If the harness's check of the files then fails, you receive its report and may correct the files once. If a limit ends the round earlier, the complete candidate files are evaluated.
