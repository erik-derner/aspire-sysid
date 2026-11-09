# Aggregation of experiment paper-fermenter-pressure

## 1 Scope

Task: `fermenter-pressure`. Model identifier: `gpt-6.1-sol`. Harness version 0.1.0.dev0; harness identity: git tree `aspire` c721b3f729f9, `tasks` d11b128ccaa8.

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
| 5 | 5 | 5 | 5 | 0 | 0 | completed 5 | 0 |

Leak scan: no sealed information was found in any transcript or agent-written file.

## 4 Errors of the output

| Unit | Training error of the recommended candidate | S of the recommended candidate (practical selection) | Best eligible S (oracle-based selection on test data) | Candidates considered per run | Pool sizes | Pool limit |
|---|---|---|---|---|---|---|
| bar (output p) | 0.0253 ± 0.0007793 (5 of 5) | 0.02324 ± 0.0005911 (5 of 5) | 0.02306 ± 0.0004579 (5 of 5) | 4, 3, 4, 5, 3 | 3, 4, 5 | 10 |

## 5 Consumption and pool properties

| Quantity | Unit | Value |
|---|---|---|
| turns | - | 33.2 ± 3.962 (5 of 5) |
| input tokens | tokens | 882876 ± 210458 (5 of 5) |
| output tokens | tokens | 23066 ± 5308 (5 of 5) |
| cost | USD | 2.014 ± 0.4543 (5 of 5) |
| elapsed execution time | s | 794.7 ± 126.4 (5 of 5) |
| pool size | - | 3.8 ± 0.8367 (5 of 5) |
| evaluated candidates | - | 3.8 ± 0.8367 (5 of 5) |
| distinct structures | - | 3.8 ± 0.8367 (5 of 5) |
| candidates with a sensitivity rank deficiency | - | 0 ± 0 (5 of 5) |
| fitted parameters of the recommended candidate | - | 5.6 ± 1.14 (5 of 5) |
| expression-tree nodes of the recommended candidate | - | 100.2 ± 55.77 (5 of 5) |

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
| test-1 | 0.02324 ± 0.0005911 (5 of 5) | 0.02306 ± 0.0004579 (5 of 5) |

## 8 Requirement outcomes

Outcomes of the assessment of each requirement: proof, counterexample, inconclusive or unavailable for formal requirements; natural-language requirements are assessed by the human. Counts over the recommended candidates of the runs and over all evaluated candidates.

| Requirement | Recommended candidates | All evaluated candidates |
|---|---|---|
| R1 | assessed by the human 5 | assessed by the human 19 |
| R2 | assessed by the human 5 | assessed by the human 19 |
| R3 | assessed by the human 5 | assessed by the human 19 |
| R4 | assessed by the human 5 | assessed by the human 19 |
| R5 | assessed by the human 5 | assessed by the human 19 |

## 9 Runs

| Run | Outcome | Delivered | Eligible | Recommended | Training error (recommended) | S (recommended) | Best eligible | S (best eligible; oracle-based selection on test data) | Candidates considered | Pool size | Turns | Cost (USD) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r01 | completed | yes | yes | SeriesPipe | 0.02612 | 0.02391 | ValvePower | 0.02301 | 4 | 4 | 39 | 2.58 |
| r02 | completed | yes | yes | mixed | 0.02617 | 0.02386 | mixed | 0.02386 | 3 | 3 | 34 | 2.34 |
| r03 | completed | yes | yes | PowerOutlet | 0.02479 | 0.02285 | PowerOutlet | 0.02285 | 4 | 4 | 28 | 1.53 |
| r04 | completed | yes | yes | GeneralizedDischarge | 0.02458 | 0.02271 | GeneralizedDischarge | 0.02271 | 5 | 5 | 32 | 1.61 |
| r05 | completed | yes | yes | power_balance | 0.02482 | 0.02287 | power_balance | 0.02287 | 3 | 3 | 33 | 2.01 |
