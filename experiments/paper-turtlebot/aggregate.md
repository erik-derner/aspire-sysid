# Aggregation of experiment paper-turtlebot

## 1 Scope

Task: `turtlebot`. Model identifier: `gpt-6.1-sol`. Harness version 0.1.0.dev0; harness identity: git tree `aspire` 5b0a61ed9713, `tasks` 4d94d2dee0f4.

An **experiment** is one task, run one or more times with identical settings; a **run** is one session of the agent for the task. The runs differ only in the responses of the language model; the requests set no seed. Every run of an aggregation used the same task, model identifier and harness identity; the harness refuses to aggregate runs that differ in any of them.

Runs planned: 5. Round budget: the round budget of the task. Pool limit of the task: 10.

## 2 Definitions

Counts: *attempted*: runs with a run record (finished, whatever the outcome); *delivered*: runs whose final check report passed: a valid pool file with at least one candidate within the pool limit that passed the file and expression checks; *eligible*: runs with at least one candidate eligible for ranking; *evaluated without a valid pool file*: runs that ended without a valid pool file whose checked candidates were evaluated in file-name order (harness order); they can be eligible without being delivered; *interrupted attempts*: attempts ended by an interruption of the harness and repeated from the beginning; not attempted runs. The counts overlap and need not sum to the number of runs.

Per-run quantities: *test score S of the recommended candidate (practical selection)*: pooled test RMSE S of the candidate the agent recommended from training and validation evidence; *training error of the recommended candidate*: pooled RMSE of the recommended candidate on the training data, computed by the harness in the evaluation mode of the task; *best eligible test score S in the pool (oracle-based selection on test data)*: smallest S among the eligible candidates of the run; selects on the test data and measures whether the pool contains an accurate model; *turns*: language-model responses of the round; *input tokens*: input tokens of all requests of the run; *output tokens*: output tokens (including reasoning tokens) of all responses; *cost*: cost from the dated price schedule (aspire/configs/prices.yaml); *elapsed execution time*: elapsed execution time of the round, without the final checks and the evaluation; *pool size*: candidates proposed in the final pool; *evaluated candidates*: candidates within the pool limit that passed the checks and were evaluated; *distinct structures*: distinct expression structures among the evaluated candidates; *candidates with a sensitivity rank deficiency*: evaluated candidates whose sensitivity rank test found dependent fitted parameters; *fitted parameters of the recommended candidate*: count of fitted parameters; *expression-tree nodes of the recommended candidate*: node count under the convention of aspire_sysid/evaluate/complexity.py.

The test score S is the pooled root mean squared error (RMSE) over all test trajectories, in the unit of the output. Every best-of-pool value is labeled "oracle-based selection on test data": it selects on the test data and states whether the pool contains an accurate model, not whether the agent recognized it; it is reported with the pool size and the number of candidates considered (the eligible candidates of the run). The agent's recommendation is reported separately.

Statistics: a table entry `m ± s (k of N)` gives the mean m and the sample standard deviation s over the k runs with a finite result among the N attempted runs (divisor k − 1); s = sqrt( sum_i (x_i - xbar)^2 / (k - 1) ), xbar = (1/k) sum_i x_i, over the k runs with a finite result (divisor k - 1); undefined for k < 2. The sample standard deviation divides by k - 1; the output errors use the population convention. An entry of an experiment with one run is labeled "single run" and has no s; an entry with one finite result among several runs states that s is undefined. Runs without a finite result are listed in Section 6 with their reasons, for every quantity; they are never assigned zero.

## 3 Runs

| Planned | Attempted | Delivered | Eligible | Evaluated without valid pool file | Interrupted attempts | Outcomes | Leak-scan findings |
|---|---|---|---|---|---|---|---|
| 5 | 5 | 5 | 5 | 0 | 0 | completed 5 | 4 |

**Leak scan: sealed information was found in 4 place(s); see the run records (extra.leak_scan).**

## 4 Errors of the output

| Unit | Training error of the recommended candidate | S of the recommended candidate (practical selection) | Best eligible S (oracle-based selection on test data) | Candidates considered per run | Pool sizes | Pool limit |
|---|---|---|---|---|---|---|
| m (output x) | 0.03974 ± 0.0006638 (5 of 5) | 0.04297 ± 0.001039 (5 of 5) | 0.03815 ± 0.001606 (5 of 5) | 6, 4, 6, 5, 4 | 4, 5, 6 | 10 |

## 5 Consumption and pool properties

| Quantity | Unit | Value |
|---|---|---|
| turns | - | 28.8 ± 3.768 (5 of 5) |
| input tokens | tokens | 561195 ± 118107 (5 of 5) |
| output tokens | tokens | 17770 ± 2469 (5 of 5) |
| cost | USD | 1.31 ± 0.2535 (5 of 5) |
| elapsed execution time | s | 531.4 ± 158.5 (5 of 5) |
| pool size | - | 5 ± 1 (5 of 5) |
| evaluated candidates | - | 5 ± 1 (5 of 5) |
| distinct structures | - | 5 ± 1 (5 of 5) |
| candidates with a sensitivity rank deficiency | - | 0 ± 0 (5 of 5) |
| fitted parameters of the recommended candidate | - | 2.4 ± 0.8944 (5 of 5) |
| expression-tree nodes of the recommended candidate | - | 31.6 ± 9.343 (5 of 5) |

## 6 Runs without a finite result

Every quantity of Sections 4 and 5 for which an attempted run has no finite value, with the reason.

Every attempted run has a finite value of every quantity.

Planned runs without a run record (not attempted runs; not in the counts of Section 3):

- none.

Spend of interrupted attempts and unfinished run folders (from their transcripts; not in the statistics): 0 attempt(s), 0 input tokens, 0 output tokens, 0.0000 USD.

## 7 Root mean squared error per test trajectory

RMSE of the recommended candidate and of the best eligible candidate (oracle-based selection on test data), per test trajectory.

| Trajectory | Recommended candidate | Best eligible candidate |
|---|---|---|
| test-1 | 0.04819 ± 0.006844 (5 of 5) | 0.05441 ± 0.01213 (5 of 5) |
| test-10 | 0.01152 ± 0.002163 (5 of 5) | 0.01073 ± 0.001238 (5 of 5) |
| test-11 | 0.06831 ± 0.008406 (5 of 5) | 0.05335 ± 0.004459 (5 of 5) |
| test-12 | 0.005823 ± 0.000739 (5 of 5) | 0.007728 ± 0.001293 (5 of 5) |
| test-2 | 0.01022 ± 0.002532 (5 of 5) | 0.009621 ± 0.001867 (5 of 5) |
| test-3 | 0.053 ± 0.005552 (5 of 5) | 0.05133 ± 0.00389 (5 of 5) |
| test-4 | 0.02613 ± 0.00435 (5 of 5) | 0.02472 ± 0.003881 (5 of 5) |
| test-5 | 0.03932 ± 0.004112 (5 of 5) | 0.03575 ± 0.005739 (5 of 5) |
| test-6 | 0.07205 ± 0.007352 (5 of 5) | 0.05103 ± 0.005688 (5 of 5) |
| test-7 | 0.0538 ± 0.01166 (5 of 5) | 0.05379 ± 0.007294 (5 of 5) |
| test-8 | 0.008164 ± 0.003077 (5 of 5) | 0.007783 ± 0.003168 (5 of 5) |
| test-9 | 0.03806 ± 0.004223 (5 of 5) | 0.03247 ± 0.003014 (5 of 5) |

## 8 Requirement outcomes

Outcomes of the assessment of each requirement: proof, counterexample, inconclusive or unavailable for formal requirements; natural-language requirements are assessed by the human. Counts over the recommended candidates of the runs and over all evaluated candidates.

The task states no requirement.

## 9 Runs

| Run | Outcome | Delivered | Eligible | Recommended | Training error (recommended) | S (recommended) | Best eligible | S (best eligible; oracle-based selection on test data) | Candidates considered | Pool size | Turns | Cost (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r01 | completed | yes | yes | CalibratedMidpoint | 0.04022 | 0.04172 | AngularDeadzone | 0.03642 | 6 | 6 | 33 | 1.65 |
| r02 | completed | yes | yes | Euler | 0.03965 | 0.04369 | AngularDeadZone | 0.03746 | 4 | 4 | 29 | 1.33 |
| r03 | completed | yes | yes | CalibratedEuler | 0.04059 | 0.04275 | TurnDeadband | 0.03791 | 6 | 6 | 28 | 1.23 |
| r04 | completed | yes | yes | RectifiedEuler | 0.03917 | 0.04431 | TurnDeadzone | 0.04076 | 5 | 5 | 23 | 0.956 |
| r05 | completed | yes | yes | calibrated_unicycle | 0.03905 | 0.04236 | angular_deadzone | 0.03821 | 4 | 4 | 31 | 1.38 |
