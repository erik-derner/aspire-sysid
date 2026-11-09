# Provenance: turtlebot

Record of the data and the fields of the task `turtlebot` (schema version 1, `tasks/README.md`).
Nothing in this file is shown to the agent. Terms: the **harness** is the software of ASPIRE and
the **agent** the language model; **sealed** means inaccessible through the agent's files, tools
and conversation.

## System and origin

The data are recordings of a TurtleBot 2 differential-drive mobile robot, made by Erik
Derner. The following facts were stated by that author:

- The pose (position x, y and heading phi) is the robot's on-board odometry; the logged data are
  known to carry a considerable measurement error. Its size was not quantified.
- The commands are the forward velocity v_f and the angular velocity v_a. Each pair of commands
  is held for 5 consecutive samples (about 1 s) and is then replaced by a new random pair.
- The sampling period is approximately T_s = 0.2 s (5 Hz).
- After an abrupt change of the commands, transition effects affect about the first three of the
  five samples.

The units are m, rad, m/s and rad/s.

## Data files

The recording consists of 5 trajectories of 150 consecutive samples each: inside a trajectory,
the state logged as the next state of sample k equals the state of sample k + 1 exactly, for x, y
and phi.

| File | Samples | Content | Visibility |
|---|---|---|---|
| `data/train.csv` | 450 (3 trajectories of 150, column `trajectory` 1 to 3) | trajectories 1 to 3 | agent-visible |
| `test/test_trajectory_<j>.csv`, j = 1 to 6 | 26, 26, 26, 26, 26, 25 | trajectory 4, segments 1 to 6 | sealed |
| `test/test_trajectory_<j>.csv`, j = 7 to 12 | 26, 26, 26, 26, 26, 25 | trajectory 5, segments 1 to 6 | sealed |

The values are written in the shortest decimal spelling that reproduces the double-precision
number, with the header `x,y,phi,v_f,v_a`.

A **test segment** holds 25 transitions (5 s): 26 consecutive rows, of which the first
initializes the simulation and the other 25 are scored. Consecutive segments share their boundary
row, which is the last scored row of one segment and the initialization row of the next. The last
segment of a trajectory has 24 transitions. The scored test samples number 2 × (5 × 25 + 24) =
298. The training data give 3 × 149 = 447 transitions. There are no validation data.

## Split

The split is by whole trajectories: trajectories 1 to 3 are training data, trajectories 4 and 5
are test data, and the test horizon is 25 samples. Reasons:

- The gains of the commands rise along a trajectory (property 4 below). A split inside the
  trajectories, with the first part of each trajectory as training data and the last part as test
  data, therefore tests a model on data whose gains differ systematically from those of its
  training data; with such a split, the training and the test simulation errors of x ranked
  parameter sets of the unicycle model in opposite order.
- The horizon of 25 samples makes the heading equation matter: a unicycle model with
  `phi_next = phi` has about twice the test error of the fitted unicycle model, whereas at a
  horizon of 5 samples the two errors differ by about 10 %.

Limitation: 12 test segments from 2 trajectories are few. The test-based ranking of a pool is an
oracle measure on a small sample.

## Properties of the data

Computed on the whole recording (5 trajectories of 150 samples, 745 transitions), which includes
the test trajectories; the agent does not receive this section. `p_v` (s) denotes the gain of the
forward command and `p_w` (s) the gain of the angular command in the unicycle model
`x_next = x + p_v*v_f*cos(phi)`, `y_next = y + p_v*v_f*sin(phi)`, `phi_next = phi + p_w*v_a`.

1. **Each trajectory starts at the pose (0, 0, 0).** The heading is wrapped to (−π, π].
2. **The gains are below T_s.** One-step least squares over all transitions (x and y jointly for
   `p_v`; the wrapped heading difference for `p_w`) gives `p_v` = 0.1667 s and `p_w` = 0.1170 s,
   against the nominal 0.2 s.
3. **The heading responds with a delay of about one sample.** In the first sample after a change
   of the commands, the heading gain is 0.047 s; in the four later samples it is 0.131 to
   0.139 s. The forward gain is 0.166 to 0.168 s in all five positions. The task supplies only
   the commands of the current sample, so a candidate cannot represent this delay.
4. **The gains rise along a trajectory.** Mean gains over the five trajectories per block of 25
   samples (`p_v` / `p_w`, the latter without the first sample after a command change): 0.148 /
   0.130 (samples 0–24), 0.164 / 0.120, 0.165 / 0.137, 0.167 / 0.138, 0.174 / 0.143 and 0.171 /
   0.138 (samples 125–149). The cause is not known.
5. **Totals per trajectory.** The ratio of the logged heading change to T_s times the sum of v_a
   is 0.84, 0.76, 0.93, 0.98 and 1.40 for trajectories 1 to 5; the ratio of the logged path
   length to T_s times the sum of v_f is 0.80, 0.85, 0.87, 0.87 and 0.84.

## Task fields and their sources

| Field | Source |
|---|---|
| `description`, `intended_use`, units | stated by the author who made the recordings |
| `data.noise`, `data.preprocessing` | not set: the description states that the logged pose carries a considerable measurement error; no preprocessing was applied |
| `formulation: discrete`, states x, y, phi, inputs v_f, v_a, output x | the task author: evaluation by simulation, one scalar output x, all three state equations delivered |
| `dynamics.sampling_period` 0.2 s | the nominal sampling period ("approximately 0.2 s") |
| `evaluation.mode: simulation`, `initialization: 1`, `horizon: 25` | the task author (section "Split") |
| column `range` | intervals that contain the training data: x and y rounded outward from the observed −1.171 to 2.552 m and −1.105 to 1.624 m; the commands' intervals [0, 0.3] m/s and [−1, 1] rad/s are rounded outward from the observed 3.4e-5 to 0.2982 and −0.9481 to 0.9412; whether the commands were drawn from exactly these intervals is an assumption |
| `failure_limits` | numerical divergence bounds (justifications in `task.yaml`) |
| requirements, reference expression | none |
| `pool_cap` 10, budget | as in the other tasks of the paper |
