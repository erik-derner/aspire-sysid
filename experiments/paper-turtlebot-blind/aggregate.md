# Aggregation of experiment paper-turtlebot-blind

## 1 Scope

Task: `task-kt5o`. Model identifier: `gpt-6.1-sol`. Harness version 0.1.0.dev0; harness identity: git tree `aspire` 5b0a61ed9713, `tasks` 4d94d2dee0f4.

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
| not supplied (output y) | 0.03941 ± 0.001433 (5 of 5) | 0.04006 ± 0.001524 (5 of 5) | 0.03651 ± 0.001926 (5 of 5) | 3, 3, 4, 4, 6 | 3, 4, 6 | 10 |

## 5 Consumption and pool properties

| Quantity | Unit | Value |
|---|---|---|
| turns | - | 37 ± 4.637 (5 of 5) |
| input tokens | tokens | 854380 ± 231041 (5 of 5) |
| output tokens | tokens | 18598 ± 1877 (5 of 5) |
| cost | USD | 1.911 ± 0.4719 (5 of 5) |
| elapsed execution time | s | 684.9 ± 320.3 (5 of 5) |
| pool size | - | 4 ± 1.225 (5 of 5) |
| evaluated candidates | - | 4 ± 1.225 (5 of 5) |
| distinct structures | - | 4 ± 1.225 (5 of 5) |
| candidates with a sensitivity rank deficiency | - | 0.2 ± 0.4472 (5 of 5) |
| fitted parameters of the recommended candidate | - | 9.6 ± 5.899 (5 of 5) |
| expression-tree nodes of the recommended candidate | - | 134.2 ± 91.13 (5 of 5) |

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
| test-1 | 0.05073 ± 0.02141 (5 of 5) | 0.04111 ± 0.0101 (5 of 5) |
| test-10 | 0.01205 ± 0.001656 (5 of 5) | 0.01269 ± 0.005273 (5 of 5) |
| test-11 | 0.04242 ± 0.02015 (5 of 5) | 0.03647 ± 0.02029 (5 of 5) |
| test-12 | 0.01238 ± 0.003285 (5 of 5) | 0.01471 ± 0.01083 (5 of 5) |
| test-2 | 0.01279 ± 0.001968 (5 of 5) | 0.01081 ± 0.004132 (5 of 5) |
| test-3 | 0.04049 ± 0.01551 (5 of 5) | 0.03465 ± 0.01503 (5 of 5) |
| test-4 | 0.03548 ± 0.008629 (5 of 5) | 0.03493 ± 0.01037 (5 of 5) |
| test-5 | 0.04489 ± 0.01345 (5 of 5) | 0.04498 ± 0.009305 (5 of 5) |
| test-6 | 0.05211 ± 0.008111 (5 of 5) | 0.04214 ± 0.00887 (5 of 5) |
| test-7 | 0.05921 ± 0.02044 (5 of 5) | 0.06135 ± 0.01909 (5 of 5) |
| test-8 | 0.01215 ± 0.00836 (5 of 5) | 0.01006 ± 0.00676 (5 of 5) |
| test-9 | 0.03987 ± 0.004936 (5 of 5) | 0.03361 ± 0.004172 (5 of 5) |

## 8 Requirement outcomes

Outcomes of the assessment of each requirement: proof, counterexample, inconclusive or unavailable for formal requirements; natural-language requirements are assessed by the human. Counts over the recommended candidates of the runs and over all evaluated candidates.

The task states no requirement.

## 9 Runs

| Run | Outcome | Delivered | Eligible | Recommended | Training error (recommended) | S (recommended) | Best eligible | S (best eligible; oracle-based selection on test data) | Candidates considered | Pool size | Turns | Cost (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r01 | completed | yes | yes | FourierMap | 0.0379 | 0.03794 | RigidPower | 0.03664 | 3 | 3 | 36 | 1.97 |
| r02 | completed | yes | yes | K_deadzone | 0.03849 | 0.0394 | K_smooth | 0.03394 | 3 | 3 | 31 | 1.16 |
| r03 | completed | yes | yes | FourierRidge | 0.04067 | 0.04154 | Rational | 0.03765 | 4 | 4 | 40 | 2.36 |
| r04 | completed | yes | yes | CoupledDeadzone | 0.04118 | 0.04153 | SmoothAngular | 0.03542 | 4 | 4 | 35 | 1.83 |
| r05 | completed | yes | yes | Deadzone | 0.03882 | 0.0399 | Rational | 0.03891 | 6 | 6 | 43 | 2.24 |
