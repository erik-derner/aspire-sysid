# Evaluation report: task turtlebot

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This report contains results on sealed data and is not shown to the agent.

Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])).
Error measures: for one trajectory with scoring interval I of N samples, measured output y[k] (x, m) and model output ŷ[k], SSE = Σ_(k∈I) (ŷ[k] − y[k])²; RMSE = sqrt(SSE/N), in m; NRMSE = RMSE/σ, with μ and σ the mean and the population standard deviation of y on I; R² = 1 − SSE / Σ_(k∈I) (y[k] − μ)²; NRMSE and R² are not applicable when σ = 0. The pooled RMSE over several trajectories is S = sqrt(ΣSSE / ΣN); on the test data it is the ranking score.
Numerical failure limits: x in [-100, 100] m; y in [-100, 100] m; phi in [-1000, 1000] rad; evaluation time limit 60 s per candidate and data group; symbolic time limit 10 s per verification.
Discontinuous expressions: expressions with jumps (Piecewise, sign) are evaluated pointwise at the sample instants and Runge-Kutta stages; no event detection or step refinement is applied at a jump.
Harness version 0.1.0.dev0; NumPy 2.5.1; SymPy 1.14.0.

## Pool

| category | count |
|---|---|
| candidates proposed | 6 |
| accepted by the file and expression checks | 6 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 6 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 6 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 6 among 6 evaluated candidates; groups: CalibratedEuler; SaturatedTurn; CircularArc; RectifiedCalibration; TurnDeadband; SpeedTurnCoupling. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: CalibratedEuler. The agent's reason: Recommend `CalibratedEuler`: its two-parameter model has the lowest pooled trajectory-held-out 25-step `x` RMSE among the submitted candidates, approximately `0.02970` m on `data/train.csv`, and little coefficient instability. The bounded saturation alternative is close, but its extra curvature is weakly identified. More complicated command maps improve some full-training-rollout errors, not the intended held-out 5 s prediction. No test score was accessed.
- Test score S of the recommended candidate (practical selection): 0.0427526 m; eligible: True; rank in the oracle-based selection: 4.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 6 eligible of 6 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | TurnDeadband | 0.0379078 | none | none |
| 2 | CircularArc | 0.0407373 | none | none |
| 3 | SpeedTurnCoupling | 0.0420933 | none | none |
| 4 | CalibratedEuler | 0.0427526 | none | none |
| 5 | SaturatedTurn | 0.0432785 | none | none |

## Candidates

### Candidate CalibratedEuler

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = x+(Ts*gf*v_f)*cos(phi)`
- `y_next = y+(Ts*gf*v_f)*sin(phi)`
- `phi_next = phi+Ts*(ga*v_a)`
Complexity: 2 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 22 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = 0.20000000000000001*P1*v_f*cos(phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(phi) + y`; `phi_next = 0.20000000000000001*P2*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0427526 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0540685 | 0.193126 | 0.962703 | none |
| test-2 | 25 | 25 | 0.00901186 | 0.117674 | 0.986153 | none |
| test-3 | 25 | 25 | 0.0579654 | 0.396275 | 0.842966 | none |
| test-4 | 25 | 25 | 0.0217816 | 0.144921 | 0.978998 | none |
| test-5 | 25 | 25 | 0.0347141 | 0.155732 | 0.975748 | none |
| test-6 | 24 | 24 | 0.0681157 | 0.541621 | 0.706646 | none |
| test-7 | 25 | 25 | 0.0530608 | 0.572408 | 0.672349 | none |
| test-8 | 25 | 25 | 0.00639203 | 0.0354884 | 0.998741 | none |
| test-9 | 25 | 25 | 0.0339373 | 0.256449 | 0.934234 | none |
| test-10 | 25 | 25 | 0.0106719 | 0.157132 | 0.975309 | none |
| test-11 | 25 | 25 | 0.0716188 | 0.915768 | 0.161369 | none |
| test-12 | 24 | 24 | 0.00627366 | 0.0471389 | 0.997778 | none |

Output errors on the training data (pooled RMSE: 0.0405896 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0330984 | 0.649473 | 0.578185 | none |
| 1-2 | 25 | 25 | 0.00598439 | 0.0777204 | 0.99396 | none |
| 1-3 | 25 | 25 | 0.0256547 | 0.283103 | 0.919853 | none |
| 1-4 | 25 | 25 | 0.0734653 | 1.47589 | -1.17824 | none |
| 1-5 | 25 | 25 | 0.0360594 | 0.241693 | 0.941584 | none |
| 1-6 | 24 | 24 | 0.0506526 | 1.39606 | -0.948995 | none |
| 2-1 | 25 | 25 | 0.0275834 | 0.291944 | 0.914769 | none |
| 2-2 | 25 | 25 | 0.0309208 | 0.301586 | 0.909046 | none |
| 2-3 | 25 | 25 | 0.0108159 | 0.157532 | 0.975184 | none |
| 2-4 | 25 | 25 | 0.0581011 | 0.450322 | 0.79721 | none |
| 2-5 | 25 | 25 | 0.0707688 | 0.396784 | 0.842562 | none |
| 2-6 | 24 | 24 | 0.0420874 | 0.290994 | 0.915322 | none |
| 3-1 | 25 | 25 | 0.044641 | 0.343983 | 0.881675 | none |
| 3-2 | 25 | 25 | 0.0190672 | 0.13899 | 0.980682 | none |
| 3-3 | 25 | 25 | 0.0180564 | 0.125229 | 0.984318 | none |
| 3-4 | 25 | 25 | 0.0393509 | 0.393509 | 0.84515 | none |
| 3-5 | 25 | 25 | 0.0377665 | 0.304474 | 0.907295 | none |
| 3-6 | 24 | 24 | 0.0311583 | 0.200521 | 0.959791 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1, 1; rank 2 of 2.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![CalibratedEuler test](plots/CalibratedEuler_test.png)

*Candidate CalibratedEuler, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of CalibratedEuler; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![CalibratedEuler train](plots/CalibratedEuler_train.png)

*Candidate CalibratedEuler, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of CalibratedEuler; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate SaturatedTurn

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = x+(Ts*gf*v_f)*cos(phi)`
- `y_next = y+(Ts*gf*v_f)*sin(phi)`
- `phi_next = phi+Ts*(amp*tanh(slope*v_a))`
Complexity: 3 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 25 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = 0.20000000000000001*P1*v_f*cos(phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(phi) + y`; `phi_next = 0.20000000000000001*P2*tanh(P3*v_a) + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0432785 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0540997 | 0.193237 | 0.96266 | none |
| test-2 | 25 | 25 | 0.0100086 | 0.130689 | 0.98292 | none |
| test-3 | 25 | 25 | 0.0588447 | 0.402287 | 0.838165 | none |
| test-4 | 25 | 25 | 0.0214132 | 0.14247 | 0.979702 | none |
| test-5 | 25 | 25 | 0.0348689 | 0.156426 | 0.975531 | none |
| test-6 | 24 | 24 | 0.0704865 | 0.560473 | 0.68587 | none |
| test-7 | 25 | 25 | 0.0524712 | 0.566048 | 0.679589 | none |
| test-8 | 25 | 25 | 0.00669002 | 0.0371429 | 0.99862 | none |
| test-9 | 25 | 25 | 0.034939 | 0.264019 | 0.930294 | none |
| test-10 | 25 | 25 | 0.0107693 | 0.158566 | 0.974857 | none |
| test-11 | 25 | 25 | 0.0722574 | 0.923934 | 0.146347 | none |
| test-12 | 24 | 24 | 0.00620923 | 0.0466547 | 0.997823 | none |

Output errors on the training data (pooled RMSE: 0.0405476 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.033093 | 0.649365 | 0.578325 | none |
| 1-2 | 25 | 25 | 0.00619202 | 0.0804168 | 0.993533 | none |
| 1-3 | 25 | 25 | 0.0241584 | 0.266592 | 0.928929 | none |
| 1-4 | 25 | 25 | 0.074546 | 1.4976 | -1.2428 | none |
| 1-5 | 25 | 25 | 0.0353039 | 0.23663 | 0.944006 | none |
| 1-6 | 24 | 24 | 0.051583 | 1.42171 | -1.02125 | none |
| 2-1 | 25 | 25 | 0.0288683 | 0.305543 | 0.906643 | none |
| 2-2 | 25 | 25 | 0.0315762 | 0.307979 | 0.905149 | none |
| 2-3 | 25 | 25 | 0.0118881 | 0.173149 | 0.970019 | none |
| 2-4 | 25 | 25 | 0.0571315 | 0.442807 | 0.803922 | none |
| 2-5 | 25 | 25 | 0.0717525 | 0.4023 | 0.838155 | none |
| 2-6 | 24 | 24 | 0.0408621 | 0.282522 | 0.920181 | none |
| 3-1 | 25 | 25 | 0.0442598 | 0.341046 | 0.883687 | none |
| 3-2 | 25 | 25 | 0.0193079 | 0.140745 | 0.980191 | none |
| 3-3 | 25 | 25 | 0.0178265 | 0.123634 | 0.984715 | none |
| 3-4 | 25 | 25 | 0.0372796 | 0.372797 | 0.861023 | none |
| 3-5 | 25 | 25 | 0.0369487 | 0.297881 | 0.911267 | none |
| 3-6 | 24 | 24 | 0.0311267 | 0.200318 | 0.959873 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.41, 1, 0.0141; rank 3 of 3.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![SaturatedTurn test](plots/SaturatedTurn_test.png)

*Candidate SaturatedTurn, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of SaturatedTurn; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![SaturatedTurn train](plots/SaturatedTurn_train.png)

*Candidate SaturatedTurn, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of SaturatedTurn; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate CircularArc

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = x+(Piecewise((Ts*gf*v_f*sin(Ts*ga*v_a/2)/(Ts*ga*v_a/2), (Abs(v_a)>wa_eps)), (Ts*gf*v_f, True)))*cos(phi+Ts*ga*v_a/2+offset)`
- `y_next = y+(Piecewise((Ts*gf*v_f*sin(Ts*ga*v_a/2)/(Ts*ga*v_a/2), (Abs(v_a)>wa_eps)), (Ts*gf*v_f, True)))*sin(phi+Ts*ga*v_a/2+offset)`
- `phi_next = phi+Ts*(ga*v_a)`
Complexity: 3 fitted, 2 fixed and 0 tied parameters; 0 non-integer numeric literals; 82 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = x + Piecewise((2*P1*v_f*sin(0.10000000000000001*P2*v_a)/(P2*v_a), Abs(v_a) > 1.0e-8), (0.20000000000000001*P1*v_f, True))*cos(0.10000000000000001*P2*v_a + P3 + phi)`; `y_next = y + Piecewise((2*P1*v_f*sin(0.10000000000000001*P2*v_a)/(P2*v_a), Abs(v_a) > 1.0e-8), (0.20000000000000001*P1*v_f, True))*sin(0.10000000000000001*P2*v_a + P3 + phi)`; `phi_next = 0.20000000000000001*P2*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0407373 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0506638 | 0.180965 | 0.967252 | none |
| test-2 | 25 | 25 | 0.010226 | 0.133528 | 0.98217 | none |
| test-3 | 25 | 25 | 0.0538715 | 0.368288 | 0.864364 | none |
| test-4 | 25 | 25 | 0.0238448 | 0.158649 | 0.974831 | none |
| test-5 | 25 | 25 | 0.0348377 | 0.156287 | 0.975575 | none |
| test-6 | 24 | 24 | 0.0642515 | 0.510896 | 0.738985 | none |
| test-7 | 25 | 25 | 0.0532203 | 0.574129 | 0.670376 | none |
| test-8 | 25 | 25 | 0.00561067 | 0.0311503 | 0.99903 | none |
| test-9 | 25 | 25 | 0.0332276 | 0.251086 | 0.936956 | none |
| test-10 | 25 | 25 | 0.0110353 | 0.162483 | 0.973599 | none |
| test-11 | 25 | 25 | 0.0657816 | 0.841128 | 0.292503 | none |
| test-12 | 24 | 24 | 0.00690209 | 0.0518607 | 0.99731 | none |

Output errors on the training data (pooled RMSE: 0.0387676 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0326227 | 0.640137 | 0.590225 | none |
| 1-2 | 25 | 25 | 0.00591872 | 0.0768674 | 0.994091 | none |
| 1-3 | 25 | 25 | 0.0375354 | 0.41421 | 0.82843 | none |
| 1-4 | 25 | 25 | 0.0621593 | 1.24875 | -0.559388 | none |
| 1-5 | 25 | 25 | 0.0299192 | 0.200538 | 0.959785 | none |
| 1-6 | 24 | 24 | 0.0490383 | 1.35157 | -0.82674 | none |
| 2-1 | 25 | 25 | 0.0301652 | 0.319269 | 0.898067 | none |
| 2-2 | 25 | 25 | 0.0341145 | 0.332735 | 0.889287 | none |
| 2-3 | 25 | 25 | 0.00833327 | 0.121373 | 0.985269 | none |
| 2-4 | 25 | 25 | 0.0639008 | 0.495274 | 0.754704 | none |
| 2-5 | 25 | 25 | 0.0624273 | 0.350015 | 0.877489 | none |
| 2-6 | 24 | 24 | 0.0384761 | 0.266025 | 0.929231 | none |
| 3-1 | 25 | 25 | 0.0388248 | 0.299166 | 0.9105 | none |
| 3-2 | 25 | 25 | 0.0177796 | 0.129604 | 0.983203 | none |
| 3-3 | 25 | 25 | 0.0165963 | 0.115102 | 0.986752 | none |
| 3-4 | 25 | 25 | 0.0256218 | 0.256218 | 0.934352 | none |
| 3-5 | 25 | 25 | 0.0426117 | 0.343537 | 0.881982 | none |
| 3-6 | 24 | 24 | 0.0350693 | 0.225691 | 0.949064 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1, 1, 0.998; rank 3 of 3.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![CircularArc test](plots/CircularArc_test.png)

*Candidate CircularArc, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of CircularArc; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![CircularArc train](plots/CircularArc_train.png)

*Candidate CircularArc, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of CircularArc; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate RectifiedCalibration

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `x_next = x+(Ts*Max(gf*v_f+vbias,0))*cos(phi+offset+phase*v_a)`
- `y_next = y+(Ts*Max(gf*v_f+vbias,0))*sin(phi+offset+phase*v_a)`
- `phi_next = phi+Ts*(ga*v_a+wbias)`
Complexity: 6 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 45 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `x_next = x + 0.20000000000000001*cos(P3 + P4*v_a + phi)*Max(0, P1 + P2*v_f)`; `y_next = y + 0.20000000000000001*sin(P3 + P4*v_a + phi)*Max(0, P1 + P2*v_f)`; `phi_next = 0.20000000000000001*P5 + 0.20000000000000001*P6*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0434437 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.069674 | 0.248866 | 0.938065 | none |
| test-2 | 25 | 25 | 0.0105119 | 0.137262 | 0.981159 | none |
| test-3 | 25 | 25 | 0.0572111 | 0.391119 | 0.847026 | none |
| test-4 | 25 | 25 | 0.0261191 | 0.17378 | 0.9698 | none |
| test-5 | 25 | 25 | 0.0317384 | 0.142383 | 0.979727 | none |
| test-6 | 24 | 24 | 0.0523647 | 0.416377 | 0.82663 | none |
| test-7 | 25 | 25 | 0.0628529 | 0.678044 | 0.540257 | none |
| test-8 | 25 | 25 | 0.0103142 | 0.0572642 | 0.996721 | none |
| test-9 | 25 | 25 | 0.0336698 | 0.254428 | 0.935267 | none |
| test-10 | 25 | 25 | 0.0128953 | 0.18987 | 0.963949 | none |
| test-11 | 25 | 25 | 0.0671791 | 0.858999 | 0.262122 | none |
| test-12 | 24 | 24 | 0.00838284 | 0.0629868 | 0.996033 | none |

Output errors on the training data (pooled RMSE: 0.0395953 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0286855 | 0.56288 | 0.683167 | none |
| 1-2 | 25 | 25 | 0.0144661 | 0.187874 | 0.964703 | none |
| 1-3 | 25 | 25 | 0.0293844 | 0.324261 | 0.894855 | none |
| 1-4 | 25 | 25 | 0.0662464 | 1.33086 | -0.771196 | none |
| 1-5 | 25 | 25 | 0.0303668 | 0.203538 | 0.958572 | none |
| 1-6 | 24 | 24 | 0.0506765 | 1.39672 | -0.950834 | none |
| 2-1 | 25 | 25 | 0.0301973 | 0.319609 | 0.89785 | none |
| 2-2 | 25 | 25 | 0.0373486 | 0.364279 | 0.867301 | none |
| 2-3 | 25 | 25 | 0.0200892 | 0.292597 | 0.914387 | none |
| 2-4 | 25 | 25 | 0.0663491 | 0.514249 | 0.735548 | none |
| 2-5 | 25 | 25 | 0.0546652 | 0.306495 | 0.906061 | none |
| 2-6 | 24 | 24 | 0.0414258 | 0.28642 | 0.917964 | none |
| 3-1 | 25 | 25 | 0.0419156 | 0.322983 | 0.895682 | none |
| 3-2 | 25 | 25 | 0.013223 | 0.0963889 | 0.990709 | none |
| 3-3 | 25 | 25 | 0.0131798 | 0.0914072 | 0.991645 | none |
| 3-4 | 25 | 25 | 0.0366965 | 0.366965 | 0.865336 | none |
| 3-5 | 25 | 25 | 0.0455004 | 0.366825 | 0.865439 | none |
| 3-6 | 24 | 24 | 0.0336916 | 0.216825 | 0.952987 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.37, 1.08, 1.05, 0.952, 0.913, 0.363; rank 6 of 6.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![RectifiedCalibration test](plots/RectifiedCalibration_test.png)

*Candidate RectifiedCalibration, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of RectifiedCalibration; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![RectifiedCalibration train](plots/RectifiedCalibration_train.png)

*Candidate RectifiedCalibration, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of RectifiedCalibration; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate TurnDeadband

Position in the agent's order: 5. Status: evaluated.
File and expression checks: passed.
- `x_next = x+(Ts*gf*v_f)*cos(phi+offset+phase*v_a)`
- `y_next = y+(Ts*gf*v_f)*sin(phi+offset+phase*v_a)`
- `phi_next = phi+Ts*(ga*sign(v_a)*Max(Abs(v_a)-dead,0))`
Complexity: 5 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 41 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 5: `x_next = 0.20000000000000001*P1*v_f*cos(P2 + P3*v_a + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(P2 + P3*v_a + phi) + y`; `phi_next = 0.20000000000000001*P4*sign(v_a)*Max(0, -P5 + Abs(v_a)) + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0379078 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0547949 | 0.19572 | 0.961694 | none |
| test-2 | 25 | 25 | 0.00827196 | 0.108013 | 0.988333 | none |
| test-3 | 25 | 25 | 0.0523158 | 0.357653 | 0.872085 | none |
| test-4 | 25 | 25 | 0.0237516 | 0.158028 | 0.975027 | none |
| test-5 | 25 | 25 | 0.0349235 | 0.156671 | 0.975454 | none |
| test-6 | 24 | 24 | 0.0490941 | 0.390371 | 0.84761 | none |
| test-7 | 25 | 25 | 0.0579629 | 0.625291 | 0.609012 | none |
| test-8 | 25 | 25 | 0.00755781 | 0.0419609 | 0.998239 | none |
| test-9 | 25 | 25 | 0.0302373 | 0.22849 | 0.947792 | none |
| test-10 | 25 | 25 | 0.00973416 | 0.143325 | 0.979458 | none |
| test-11 | 25 | 25 | 0.0523215 | 0.669019 | 0.552414 | none |
| test-12 | 24 | 24 | 0.00791803 | 0.0594943 | 0.99646 | none |

Output errors on the training data (pooled RMSE: 0.0398744 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0334692 | 0.656748 | 0.568682 | none |
| 1-2 | 25 | 25 | 0.00530628 | 0.0689136 | 0.995251 | none |
| 1-3 | 25 | 25 | 0.0339269 | 0.374389 | 0.859833 | none |
| 1-4 | 25 | 25 | 0.0609651 | 1.22476 | -0.500048 | none |
| 1-5 | 25 | 25 | 0.028343 | 0.189973 | 0.96391 | none |
| 1-6 | 24 | 24 | 0.0497965 | 1.37247 | -0.88367 | none |
| 2-1 | 25 | 25 | 0.0308603 | 0.326627 | 0.893315 | none |
| 2-2 | 25 | 25 | 0.024755 | 0.241448 | 0.941703 | none |
| 2-3 | 25 | 25 | 0.0106477 | 0.155082 | 0.975949 | none |
| 2-4 | 25 | 25 | 0.0688125 | 0.533343 | 0.715546 | none |
| 2-5 | 25 | 25 | 0.0534552 | 0.299711 | 0.910173 | none |
| 2-6 | 24 | 24 | 0.0441557 | 0.305294 | 0.906796 | none |
| 3-1 | 25 | 25 | 0.0451979 | 0.348274 | 0.878705 | none |
| 3-2 | 25 | 25 | 0.0138232 | 0.100764 | 0.989847 | none |
| 3-3 | 25 | 25 | 0.0180424 | 0.125132 | 0.984342 | none |
| 3-4 | 25 | 25 | 0.0405829 | 0.405829 | 0.835303 | none |
| 3-5 | 25 | 25 | 0.0537148 | 0.43305 | 0.812468 | none |
| 3-6 | 24 | 24 | 0.0321795 | 0.207093 | 0.957112 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.07, 1, 0.92, 0.384; rank 5 of 5.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![TurnDeadband test](plots/TurnDeadband_test.png)

*Candidate TurnDeadband, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of TurnDeadband; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![TurnDeadband train](plots/TurnDeadband_train.png)

*Candidate TurnDeadband, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of TurnDeadband; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate SpeedTurnCoupling

Position in the agent's order: 6. Status: evaluated.
File and expression checks: passed.
- `x_next = x+(Ts*gf*v_f)*cos(phi)`
- `y_next = y+(Ts*gf*v_f)*sin(phi)`
- `phi_next = phi+Ts*((ga+coupling*v_f)*v_a)`
Complexity: 3 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 26 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 6: `x_next = 0.20000000000000001*P1*v_f*cos(phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(phi) + y`; `phi_next = phi + 0.20000000000000001*v_a*(P2 + P3*v_f)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0420933 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0527141 | 0.188288 | 0.964548 | none |
| test-2 | 25 | 25 | 0.00972173 | 0.126944 | 0.983885 | none |
| test-3 | 25 | 25 | 0.0570228 | 0.389831 | 0.848032 | none |
| test-4 | 25 | 25 | 0.0217118 | 0.144457 | 0.979132 | none |
| test-5 | 25 | 25 | 0.0353687 | 0.158668 | 0.974824 | none |
| test-6 | 24 | 24 | 0.0745688 | 0.592933 | 0.64843 | none |
| test-7 | 25 | 25 | 0.0428242 | 0.461978 | 0.786576 | none |
| test-8 | 25 | 25 | 0.00495843 | 0.0275291 | 0.999242 | none |
| test-9 | 25 | 25 | 0.0337276 | 0.254865 | 0.935044 | none |
| test-10 | 25 | 25 | 0.0101109 | 0.148872 | 0.977837 | none |
| test-11 | 25 | 25 | 0.0693717 | 0.887034 | 0.21317 | none |
| test-12 | 24 | 24 | 0.00503479 | 0.0378303 | 0.998569 | none |

Output errors on the training data (pooled RMSE: 0.0401286 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0345168 | 0.677305 | 0.541258 | none |
| 1-2 | 25 | 25 | 0.00488601 | 0.0634554 | 0.995973 | none |
| 1-3 | 25 | 25 | 0.0339381 | 0.374512 | 0.859741 | none |
| 1-4 | 25 | 25 | 0.0706441 | 1.41921 | -1.01416 | none |
| 1-5 | 25 | 25 | 0.0328452 | 0.22015 | 0.951534 | none |
| 1-6 | 24 | 24 | 0.04956 | 1.36595 | -0.86582 | none |
| 2-1 | 25 | 25 | 0.0286369 | 0.303094 | 0.908134 | none |
| 2-2 | 25 | 25 | 0.0284513 | 0.2775 | 0.922994 | none |
| 2-3 | 25 | 25 | 0.010991 | 0.160083 | 0.974373 | none |
| 2-4 | 25 | 25 | 0.0587537 | 0.45538 | 0.792629 | none |
| 2-5 | 25 | 25 | 0.0736245 | 0.412795 | 0.8296 | none |
| 2-6 | 24 | 24 | 0.0410676 | 0.283943 | 0.919377 | none |
| 3-1 | 25 | 25 | 0.0432151 | 0.332996 | 0.889114 | none |
| 3-2 | 25 | 25 | 0.0191267 | 0.139423 | 0.980561 | none |
| 3-3 | 25 | 25 | 0.0184759 | 0.128138 | 0.983581 | none |
| 3-4 | 25 | 25 | 0.0258687 | 0.258687 | 0.933081 | none |
| 3-5 | 25 | 25 | 0.0386708 | 0.311764 | 0.902803 | none |
| 3-6 | 24 | 24 | 0.0325397 | 0.209412 | 0.956147 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.37, 1, 0.353; rank 3 of 3.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![SpeedTurnCoupling test](plots/SpeedTurnCoupling_test.png)

*Candidate SpeedTurnCoupling, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of SpeedTurnCoupling; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![SpeedTurnCoupling train](plots/SpeedTurnCoupling_train.png)

*Candidate SpeedTurnCoupling, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of SpeedTurnCoupling; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
