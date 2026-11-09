# Provenance: fermenter-pressure

Record of the data and the fields of the task `fermenter-pressure` (schema version 1,
`tasks/README.md`). Nothing in this file is shown to the agent. Terms: the **harness** is the
software of ASPIRE and the **agent** the language model; **sealed** means inaccessible through the
agent's files, tools and conversation.

## System and origin

The data are recordings, made by Robert Babuška, of a small-scale 40-liter fermentation tank
filled with about 25 liters of water. At the bottom of the tank, air is fed into the water at a
flow rate controlled by a local mass-flow controller. The air collects in the headspace above the
water level and leaves through an outlet valve at the top of the tank; the air pressure above the
water level depends on the valve position. The valve position is the first input, the air flow
rate is the second input, and the air pressure is the output and the state of the system. The
description of the task (`task.yaml`) is the description by the author who made the recordings.

Source of the data, to be cited wherever the data are used: H. J. L. van Can, H. A. B. te Braake,
C. Hellinga, A. J. Krijgsman, H. B. Verbruggen, K. Ch. A. M. Luyben and J. J. Heijnen, "Design and
real time testing of a neural model predictive controller for a nonlinear system", Chemical
Engineering Science 50(15), 2419–2430, 1995, doi:10.1016/0009-2509(95)00083-H.

## Signals

Sampling period T_s = 5 s. `p`: headspace air pressure in bar (values about 1.0 to 2.2),
quantized on a grid of 1.221e-4 bar (2^-13). `valve`: outlet valve position in % closed
(100 % = fully closed). `flow`: air flow rate in l/min, quantized on a grid of 2.193e-4 l/min.
`dp`: the time derivative of `p` supplied with the data, in bar/s; it is an estimated signal (a
filtered numerical difference), not an exact difference: its correlation with the centered
difference of `p` is 0.95, 0.90 and 0.93 on the training, validation and test files.

## Data files

The values are written in the shortest decimal spelling that reproduces the double-precision
number, with the header `p,valve,flow,dp`. The files have no trajectory column: each file is
declared as one trajectory. The division into training, validation and test data is that of the
author who made the recordings (three files).

| File | Samples | Visibility |
|---|---|---|
| `data/train.csv` | 1452 | agent-visible |
| `data/val.csv` | 1454 | agent-visible, offered |
| `test/test_trajectory_1.csv` | 1210 (trajectory test-1) | sealed |

**A property of the files.** Each file has a row in its middle (training: row 726; validation:
row 728; test: row 605) at which the pressure returns to its lowest value with an air flow rate
near 0.1 l/min, as in the first row. This suggests that each file consists of two recordings
joined into one declared trajectory. The task and the evaluation treat each file as one
trajectory; the manuscript states this property.

## Requirements

The task has five requirements in natural language, R1 to R5 (`requirements_nl` in `task.yaml`):
monotonicity with respect to the inlet flow, monotonicity with respect to the valve closure,
zero-flow equilibrium, pressure relaxation, and the fully closed valve. Robert Babuška stated
them; they are entered verbatim. The harness passes them to the agent and reports them as
unresolved, and a human assesses them. The task has no formal requirement.

## Task fields and their sources

- `description`, `intended_use`: the author who made the recordings (units: pressure in bar,
  valve position in % closed, air flow rate in l/min).
- `columns[].range`: the declared range of `valve` is [0, 100] % closed. Observed training
  ranges: p ∈ [0.9923, 2.1867] bar, valve ∈ [10.31, 92.41] % closed, flow ∈ [0.0973, 30.80] l/min,
  dp ∈ [−0.02090, 0.02395] bar/s.
- `evaluation`: simulation from one initial sample (sample 0), scoring samples 1 to 1209 of the
  test trajectory, zero-order hold, one fourth-order Runge–Kutta step per T_s.
- `failure_limits`: a numerical divergence bound (justification in `task.yaml`).
