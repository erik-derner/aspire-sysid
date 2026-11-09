# Provenance: friction-driven

Record of the data and the fields of the task `friction-driven` (schema version 1,
`tasks/README.md`). Nothing in this file is shown to the agent. Terms: the **harness** is the
software of ASPIRE and the **agent** the language model; **sealed** means inaccessible through the
agent's files, tools and conversation.

## System and origin

The system is a rotational motion system with adjustable dry friction, driven by a
voltage-controlled DC motor, recorded by Robert Babuška on a real rig. A felt pad pressed
against the rotating disc by a leaf spring sets the dry-friction level; it is constant across all
recordings used here. The driven recordings and the free-response recordings come from the same
rig, the same friction configuration and the same session. The author who made the recordings
stated that a constant acceleration offset of +1.9 to +3.2 rad/s² is physical but small, that
u = 0 in the free-response recordings, and that u is the voltage of a voltage-controlled DC motor
with a torque approximately linear in u over the used range, without dead zone or saturation.

## Signals

Sampling period T_s = 0.01 s. The angle θ (column `theta`, rad) is an encoder reading quantized
on a grid of π/1000 rad; the angular velocity ω (`omega`, rad/s) and the angular acceleration
dω/dt (`domega`, rad/s²) are numerical derivatives of the angle and lie on grids of π/20 rad/s and
2.5π rad/s²: within every driven trajectory, `omega` equals the centered difference of `theta`
divided by 2 T_s, and `domega` the centered difference of `omega`, to within 3e-12. The input u
(`u`, V) is the motor voltage.

## Data files

The driven recordings consist of trajectories that start at θ = 0 at rest. The free-response
recordings hold θ, ω and dω/dt; the column u = 0 was added. The values are written in the shortest
decimal spelling that reproduces the double-precision number. The training and validation files
have the column `trajectory` (integers from 1, driven trajectories first); each test file is one
trajectory without it.

| File | Content | Samples | Trajectories (samples) | Visibility |
|---|---|---|---|---|
| `data/train.csv` | 4 driven + 9 free responses | 3522 | 1–4 driven (450, 450, 300, 300); 5–7 free (442 each); 8–10 free (141 each); 11–13 free (91 each) | agent-visible |
| `data/val.csv` | 2 driven + 1 free response | 1192 | 1–2 driven (450, 300); 3 free (442) | agent-visible, offered |
| `test/test_trajectory_1.csv` | driven | 450 | test-1 | sealed |
| `test/test_trajectory_2.csv` | driven | 300 | test-2 | sealed |
| `test/test_trajectory_3.csv` | free response, low amplitude | 141 | test-3 | sealed |
| `test/test_trajectory_4.csv` | free response | 91 | test-4 | sealed |

**Overlap of trajectories.** The free-response trajectories of 141 and 91 samples are the final
samples of driven recordings. This holds within the training data, between the training and the
validation data (232 of the 1192 validation samples are also training samples) and within the
test data (test trajectories 3 and 4 are the final samples of test trajectories 1 and 2). No test
trajectory overlaps the training or the validation data. The manuscript states this property.

## Requirements

A formal requirement of the harness is a condition on a submitted expression over a box of its
arguments. R1 is the state equation dθ/dt = ω (`dtheta` equals `omega`, verified symbolically).
R2 and R3 are conditions on the expression `domega` as a function of `theta` (rad), `omega`
(rad/s) and `u` (V). They were derived from requirements that Robert Babuška stated in words
for the terms of a model of the form

    J dω/dt = τ_g(θ) + τ_m(u) − b ω − τ_f,

where J is the moment of inertia, τ_g the gravitational torque, τ_m the motor torque, b the
viscous-friction coefficient and τ_f the dry-friction torque. A candidate does not declare its
terms separately, so each condition is a special case in which the other terms drop out. A
requirement contains no number other than 0 and the bounds of the domain.

| Id | Requirement in words | Condition on `domega` | Domain |
|---|---|---|---|
| R2 | Gravitational restoring tendency: gravity acts toward the hanging equilibrium; static friction can prevent motion | `domega*theta <= 0` | omega = 0, u = 0, theta in [-π, π] |
| R3 | Motor input: motor torque approximately proportional to the voltage, with fixed polarity | `domega` increasing in `u`, not strictly | theta in [-3.1416, 3.1416], omega in [-23, 23], u in [-10, 10] |

- R2: at rest with zero voltage the acceleration is zero (sticking) or has the sign of τ_g(θ),
  which points toward theta = 0. The angle bound is π, written `pi`, because sin(3.1416) < 0 and
  the bound 3.1416 would give a model with the gravity term −k_g sin θ a counterexample at the
  edge of the box.
- R3: τ_m increases with u and no other term depends on u; during sticking `domega` stays zero.
  The harness checks ∂`domega`/∂`u` ≥ 0, so that `increasing` means non-decreasing. The positive
  polarity is taken from the training and validation data: all 7 samples with |theta| < 0.01 rad,
  omega = 0 and u ≠ 0 have `domega*u >= 0`.

The entries of `task.yaml` hold only the fields that the task loader requires; they have no
`statement`, so that the brief shows the agent each condition with its domain and tolerance and
not a sentence of the requirement. Every tolerance is 0, and a demonstrated violation excludes a
candidate. Verification: the symbolic stage, then 10000 sampled points with the seed 20261009.

Comparison of R2 with the training and validation data (4714 samples, no test data): 2139 of the
2170 samples with omega = 0 and u = 0 satisfy the relation; the largest value of `domega*theta` is
1.28 rad²/s², at samples where `domega` is one quantization step (7.85 rad/s²).

Check of the two conditions on example models (no language model; coefficients: least squares on
the samples with |omega| > 0.5 rad/s): a stick–slip model in closed form with a constant offset
has no counterexample (R2 proved, R3 without violation at the sampled points); a model with
gravity, drive, viscous term and smoothed Coulomb term `c*tanh(10*omega)` without offset satisfies
both (proved); the same model with a constant offset violates R2, because at rest near theta = 0
its acceleration equals the offset. The two conditions therefore do not distinguish a model with
sticking from a model with smooth friction and no offset.

## Task fields and their sources

- `description`, `intended_use`: written by the task authors from the statements of the author
  who made the recordings.
- `columns[].range`: the declared range of `theta` is [−3.1416, 3.1416] rad and that of `u` is
  [−10, 10] V. Observed training ranges: θ ∈ [−2.513, 2.535] rad, ω ∈ [−20.11, 14.45] rad/s,
  u ∈ [−4.945, 3.953] V, dω/dt ∈ [−196.3, 180.6] rad/s².
- `evaluation`: simulation from one initial sample per trajectory (sample 0), scoring samples
  1 to N − 1 of each trajectory, zero-order hold, one fourth-order Runge–Kutta step per T_s.
- `failure_limits`: numerical divergence bounds (justifications in `task.yaml`).
