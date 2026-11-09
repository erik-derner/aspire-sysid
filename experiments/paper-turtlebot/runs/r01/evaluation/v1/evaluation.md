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

Distinct structures: 6 among 6 evaluated candidates; groups: CalibratedMidpoint; WheelDeadzone; ForwardDeadzone; AngularDeadzone; PhaseAdjusted; SparseCommandMap. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: CalibratedMidpoint. The agent's reason: Recommend the two-gain physical midpoint model: its leave-one-trajectory-out 25-transition (5 s) `x` RMSE is 0.029936 m. The wheel-dead-zone model achieves 0.029800 m, only about 0.000136 m lower, while adding two weakly identifiable parameters; this is not convincing evidence of improvement with three validation trajectories. Other structural candidates give about 0.0306 to 0.0315 m. The recommended model preserves zero-command stationarity and coordinate invariance, has no polynomial extrapolation, and provides the clearest defensible memoryless approximation. Selection uses training-only validation, not inaccessible test results.
- Test score S of the recommended candidate (practical selection): 0.0417201 m; eligible: True; rank in the oracle-based selection: 3.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 6 eligible of 6 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | AngularDeadzone | 0.0364221 | none | none |
| 2 | PhaseAdjusted | 0.0401728 | none | none |
| 3 | CalibratedMidpoint | 0.0417201 | none | none |
| 4 | ForwardDeadzone | 0.0421611 | none | none |
| 5 | SparseCommandMap | 0.042856 | none | none |

## Candidates

### Candidate CalibratedMidpoint

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = x + Ts*(gf*v_f)*cos(phi + 0.5*Ts*(ga*v_a))`
- `y_next = y + Ts*(gf*v_f)*sin(phi + 0.5*Ts*(ga*v_a))`
- `phi_next = atan2(sin(phi + Ts*(ga*v_a)), cos(phi + Ts*(ga*v_a)))`
Complexity: 2 fitted, 1 fixed and 0 tied parameters; 2 non-integer numeric literals; 43 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = 0.20000000000000001*P1*v_f*cos(0.10000000000000001*P2*v_a + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(0.10000000000000001*P2*v_a + phi) + y`; `phi_next = atan2(sin(0.20000000000000001*P2*v_a + phi), cos(0.20000000000000001*P2*v_a + phi))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0417201 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0502405 | 0.179452 | 0.967797 | none |
| test-2 | 25 | 25 | 0.00782807 | 0.102217 | 0.989552 | none |
| test-3 | 25 | 25 | 0.0599461 | 0.409817 | 0.83205 | none |
| test-4 | 25 | 25 | 0.0212969 | 0.141696 | 0.979922 | none |
| test-5 | 25 | 25 | 0.0354482 | 0.159025 | 0.974711 | none |
| test-6 | 24 | 24 | 0.0622185 | 0.49473 | 0.755242 | none |
| test-7 | 25 | 25 | 0.0370126 | 0.399284 | 0.840572 | none |
| test-8 | 25 | 25 | 0.00477245 | 0.0264966 | 0.999298 | none |
| test-9 | 25 | 25 | 0.0330339 | 0.249623 | 0.937689 | none |
| test-10 | 25 | 25 | 0.0101863 | 0.149983 | 0.977505 | none |
| test-11 | 25 | 25 | 0.0807998 | 1.03316 | -0.0674245 | none |
| test-12 | 24 | 24 | 0.00519434 | 0.0390292 | 0.998477 | none |

Output errors on the training data (pooled RMSE: 0.0402186 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0326637 | 0.640942 | 0.589194 | none |
| 1-2 | 25 | 25 | 0.00465514 | 0.0604572 | 0.996345 | none |
| 1-3 | 25 | 25 | 0.0210817 | 0.23264 | 0.945879 | none |
| 1-4 | 25 | 25 | 0.0675719 | 1.35749 | -0.842784 | none |
| 1-5 | 25 | 25 | 0.0403706 | 0.27059 | 0.926781 | none |
| 1-6 | 24 | 24 | 0.0500699 | 1.38 | -0.904412 | none |
| 2-1 | 25 | 25 | 0.0312851 | 0.331122 | 0.890358 | none |
| 2-2 | 25 | 25 | 0.0253553 | 0.247303 | 0.938841 | none |
| 2-3 | 25 | 25 | 0.0103798 | 0.151181 | 0.977144 | none |
| 2-4 | 25 | 25 | 0.0623316 | 0.483112 | 0.766603 | none |
| 2-5 | 25 | 25 | 0.0710587 | 0.39841 | 0.84127 | none |
| 2-6 | 24 | 24 | 0.0380248 | 0.262905 | 0.930881 | none |
| 3-1 | 25 | 25 | 0.0425263 | 0.327688 | 0.89262 | none |
| 3-2 | 25 | 25 | 0.0175506 | 0.127935 | 0.983633 | none |
| 3-3 | 25 | 25 | 0.016979 | 0.117756 | 0.986134 | none |
| 3-4 | 25 | 25 | 0.0393206 | 0.393207 | 0.845389 | none |
| 3-5 | 25 | 25 | 0.03952 | 0.318611 | 0.898487 | none |
| 3-6 | 24 | 24 | 0.0356677 | 0.229542 | 0.947311 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1, 1; rank 2 of 2.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![CalibratedMidpoint test](plots/CalibratedMidpoint_test.png)

*Candidate CalibratedMidpoint, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of CalibratedMidpoint; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![CalibratedMidpoint train](plots/CalibratedMidpoint_train.png)

*Candidate CalibratedMidpoint, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of CalibratedMidpoint; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate WheelDeadzone

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = x + Ts*(gf*((sign(v_f + b*v_a)*Max(Abs(v_f + b*v_a)-dw, 0)) + (sign(v_f - b*v_a)*Max(Abs(v_f - b*v_a)-dw, 0)))/2)*cos(phi + 0.5*Ts*(ga*((sign(v_f + b*v_a)*Max(Abs(v_f + b*v_a)-dw, 0)) - (sign(v_f - b*v_a)*Max(Abs(v_f - b*v_a)-dw, 0)))/(2*b)))`
- `y_next = y + Ts*(gf*((sign(v_f + b*v_a)*Max(Abs(v_f + b*v_a)-dw, 0)) + (sign(v_f - b*v_a)*Max(Abs(v_f - b*v_a)-dw, 0)))/2)*sin(phi + 0.5*Ts*(ga*((sign(v_f + b*v_a)*Max(Abs(v_f + b*v_a)-dw, 0)) - (sign(v_f - b*v_a)*Max(Abs(v_f - b*v_a)-dw, 0)))/(2*b)))`
- `phi_next = atan2(sin(phi + Ts*(ga*((sign(v_f + b*v_a)*Max(Abs(v_f + b*v_a)-dw, 0)) - (sign(v_f - b*v_a)*Max(Abs(v_f - b*v_a)-dw, 0)))/(2*b))), cos(phi + Ts*(ga*((sign(v_f + b*v_a)*Max(Abs(v_f + b*v_a)-dw, 0)) - (sign(v_f - b*v_a)*Max(Abs(v_f - b*v_a)-dw, 0)))/(2*b))))`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 2 non-integer numeric literals; 309 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = 0.10000000000000001*P1*(sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))*cos(phi + 0.050000000000000003*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3) + x`; `y_next = 0.10000000000000001*P1*(sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))*sin(phi + 0.050000000000000003*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3) + y`; `phi_next = atan2(sin(phi + 0.10000000000000001*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3), cos(phi + 0.10000000000000001*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0447875 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0532914 | 0.19035 | 0.963767 | none |
| test-2 | 25 | 25 | 0.0100435 | 0.131146 | 0.982801 | none |
| test-3 | 25 | 25 | 0.0657975 | 0.449819 | 0.797663 | none |
| test-4 | 25 | 25 | 0.0209965 | 0.139698 | 0.980484 | none |
| test-5 | 25 | 25 | 0.0480979 | 0.215773 | 0.953442 | none |
| test-6 | 24 | 24 | 0.077795 | 0.618587 | 0.61735 | none |
| test-7 | 25 | 25 | 0.0284405 | 0.30681 | 0.905868 | none |
| test-8 | 25 | 25 | 0.00676687 | 0.0375695 | 0.998589 | none |
| test-9 | 25 | 25 | 0.0270377 | 0.204312 | 0.958257 | none |
| test-10 | 25 | 25 | 0.0136101 | 0.200395 | 0.959842 | none |
| test-11 | 25 | 25 | 0.0791492 | 1.01206 | -0.0242595 | none |
| test-12 | 24 | 24 | 0.00650254 | 0.0488587 | 0.997613 | none |

Output errors on the training data (pooled RMSE: 0.0374946 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0299559 | 0.587809 | 0.654481 | none |
| 1-2 | 25 | 25 | 0.00491201 | 0.0637931 | 0.99593 | none |
| 1-3 | 25 | 25 | 0.0382744 | 0.422364 | 0.821608 | none |
| 1-4 | 25 | 25 | 0.0571619 | 1.14836 | -0.31873 | none |
| 1-5 | 25 | 25 | 0.0395408 | 0.265028 | 0.92976 | none |
| 1-6 | 24 | 24 | 0.0537089 | 1.4803 | -1.19129 | none |
| 2-1 | 25 | 25 | 0.0329813 | 0.349075 | 0.878146 | none |
| 2-2 | 25 | 25 | 0.0197037 | 0.19218 | 0.963067 | none |
| 2-3 | 25 | 25 | 0.0114766 | 0.167155 | 0.972059 | none |
| 2-4 | 25 | 25 | 0.0489878 | 0.379688 | 0.855837 | none |
| 2-5 | 25 | 25 | 0.0725236 | 0.406623 | 0.834658 | none |
| 2-6 | 24 | 24 | 0.0192662 | 0.133207 | 0.982256 | none |
| 3-1 | 25 | 25 | 0.0306325 | 0.23604 | 0.944285 | none |
| 3-2 | 25 | 25 | 0.0103948 | 0.0757726 | 0.994259 | none |
| 3-3 | 25 | 25 | 0.0186991 | 0.129686 | 0.983182 | none |
| 3-4 | 25 | 25 | 0.029423 | 0.294231 | 0.913428 | none |
| 3-5 | 25 | 25 | 0.0409615 | 0.330232 | 0.890947 | none |
| 3-6 | 24 | 24 | 0.0406549 | 0.261637 | 0.931546 | none |

- Failed computation (sensitivity rank test): NameError: name 'DiracDelta' is not defined
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![WheelDeadzone test](plots/WheelDeadzone_test.png)

*Candidate WheelDeadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of WheelDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![WheelDeadzone train](plots/WheelDeadzone_train.png)

*Candidate WheelDeadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of WheelDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ForwardDeadzone

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = x + Ts*(gf*sign(v_f)*Max(Abs(v_f)-df, 0))*cos(phi + 0.5*Ts*(ga*v_a + ba))`
- `y_next = y + Ts*(gf*sign(v_f)*Max(Abs(v_f)-df, 0))*sin(phi + 0.5*Ts*(ga*v_a + ba))`
- `phi_next = atan2(sin(phi + Ts*(ga*v_a + ba)), cos(phi + Ts*(ga*v_a + ba)))`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 2 non-integer numeric literals; 73 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = 0.20000000000000001*P1*cos(0.10000000000000001*P3 + 0.10000000000000001*P4*v_a + phi)*sign(v_f)*Max(0, -P2 + Abs(v_f)) + x`; `y_next = 0.20000000000000001*P1*sin(0.10000000000000001*P3 + 0.10000000000000001*P4*v_a + phi)*sign(v_f)*Max(0, -P2 + Abs(v_f)) + y`; `phi_next = atan2(sin(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi), cos(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0421611 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0651819 | 0.232821 | 0.945794 | none |
| test-2 | 25 | 25 | 0.0112102 | 0.146379 | 0.978573 | none |
| test-3 | 25 | 25 | 0.0595008 | 0.406772 | 0.834537 | none |
| test-4 | 25 | 25 | 0.0249796 | 0.166199 | 0.972378 | none |
| test-5 | 25 | 25 | 0.0320454 | 0.14376 | 0.979333 | none |
| test-6 | 24 | 24 | 0.0485914 | 0.386374 | 0.850715 | none |
| test-7 | 25 | 25 | 0.0469126 | 0.506083 | 0.74388 | none |
| test-8 | 25 | 25 | 0.00736159 | 0.0408714 | 0.99833 | none |
| test-9 | 25 | 25 | 0.0328874 | 0.248515 | 0.93824 | none |
| test-10 | 25 | 25 | 0.0112666 | 0.165889 | 0.972481 | none |
| test-11 | 25 | 25 | 0.0762469 | 0.974946 | 0.0494807 | none |
| test-12 | 24 | 24 | 0.00908083 | 0.0682314 | 0.995344 | none |

Output errors on the training data (pooled RMSE: 0.0394138 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0287483 | 0.564111 | 0.681778 | none |
| 1-2 | 25 | 25 | 0.0123078 | 0.159844 | 0.97445 | none |
| 1-3 | 25 | 25 | 0.0249895 | 0.275764 | 0.923954 | none |
| 1-4 | 25 | 25 | 0.0613376 | 1.23225 | -0.518435 | none |
| 1-5 | 25 | 25 | 0.0356843 | 0.23918 | 0.942793 | none |
| 1-6 | 24 | 24 | 0.0505757 | 1.39394 | -0.943077 | none |
| 2-1 | 25 | 25 | 0.0330664 | 0.349976 | 0.877517 | none |
| 2-2 | 25 | 25 | 0.0307859 | 0.30027 | 0.909838 | none |
| 2-3 | 25 | 25 | 0.0171788 | 0.250206 | 0.937397 | none |
| 2-4 | 25 | 25 | 0.0695387 | 0.538971 | 0.70951 | none |
| 2-5 | 25 | 25 | 0.0575757 | 0.322813 | 0.895791 | none |
| 2-6 | 24 | 24 | 0.0374986 | 0.259266 | 0.932781 | none |
| 3-1 | 25 | 25 | 0.0398818 | 0.307311 | 0.90556 | none |
| 3-2 | 25 | 25 | 0.0123223 | 0.089823 | 0.991932 | none |
| 3-3 | 25 | 25 | 0.0127186 | 0.0882087 | 0.992219 | none |
| 3-4 | 25 | 25 | 0.0378316 | 0.378316 | 0.856877 | none |
| 3-5 | 25 | 25 | 0.0463028 | 0.373294 | 0.860652 | none |
| 3-6 | 24 | 24 | 0.0377195 | 0.242747 | 0.941074 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.05, 0.953, 0.38; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ForwardDeadzone test](plots/ForwardDeadzone_test.png)

*Candidate ForwardDeadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ForwardDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ForwardDeadzone train](plots/ForwardDeadzone_train.png)

*Candidate ForwardDeadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ForwardDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate AngularDeadzone

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `x_next = x + Ts*(gf*v_f)*cos(phi + 0.5*Ts*(ga*sign(v_a)*Max(Abs(v_a)-da, 0) + ba))`
- `y_next = y + Ts*(gf*v_f)*sin(phi + 0.5*Ts*(ga*sign(v_a)*Max(Abs(v_a)-da, 0) + ba))`
- `phi_next = atan2(sin(phi + Ts*(ga*sign(v_a)*Max(Abs(v_a)-da, 0) + ba)), cos(phi + Ts*(ga*sign(v_a)*Max(Abs(v_a)-da, 0) + ba)))`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 2 non-integer numeric literals; 91 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `x_next = 0.20000000000000001*P1*v_f*cos(0.10000000000000001*P2 + 0.10000000000000001*P3*sign(v_a)*Max(0, -P4 + Abs(v_a)) + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(0.10000000000000001*P2 + 0.10000000000000001*P3*sign(v_a)*Max(0, -P4 + Abs(v_a)) + phi) + y`; `phi_next = atan2(sin(0.20000000000000001*P2 + 0.20000000000000001*P3*sign(v_a)*Max(0, -P4 + Abs(v_a)) + phi), cos(0.20000000000000001*P2 + 0.20000000000000001*P3*sign(v_a)*Max(0, -P4 + Abs(v_a)) + phi))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0364221 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0514093 | 0.183627 | 0.966281 | none |
| test-2 | 25 | 25 | 0.0102641 | 0.134026 | 0.982037 | none |
| test-3 | 25 | 25 | 0.0546374 | 0.373524 | 0.86048 | none |
| test-4 | 25 | 25 | 0.0224664 | 0.149477 | 0.977657 | none |
| test-5 | 25 | 25 | 0.0345385 | 0.154944 | 0.975992 | none |
| test-6 | 24 | 24 | 0.0445599 | 0.354318 | 0.874459 | none |
| test-7 | 25 | 25 | 0.0434309 | 0.468523 | 0.780486 | none |
| test-8 | 25 | 25 | 0.00493923 | 0.0274225 | 0.999248 | none |
| test-9 | 25 | 25 | 0.0290081 | 0.219201 | 0.951951 | none |
| test-10 | 25 | 25 | 0.0104058 | 0.153215 | 0.976525 | none |
| test-11 | 25 | 25 | 0.0595791 | 0.761819 | 0.419631 | none |
| test-12 | 24 | 24 | 0.00824848 | 0.0619773 | 0.996159 | none |

Output errors on the training data (pooled RMSE: 0.0398998 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0335238 | 0.657819 | 0.567274 | none |
| 1-2 | 25 | 25 | 0.0043885 | 0.0569942 | 0.996752 | none |
| 1-3 | 25 | 25 | 0.0308593 | 0.340537 | 0.884035 | none |
| 1-4 | 25 | 25 | 0.0553464 | 1.11189 | -0.23629 | none |
| 1-5 | 25 | 25 | 0.0331177 | 0.221977 | 0.950726 | none |
| 1-6 | 24 | 24 | 0.0489919 | 1.35029 | -0.823288 | none |
| 2-1 | 25 | 25 | 0.0342351 | 0.362345 | 0.868706 | none |
| 2-2 | 25 | 25 | 0.0191105 | 0.186394 | 0.965257 | none |
| 2-3 | 25 | 25 | 0.0074973 | 0.109197 | 0.988076 | none |
| 2-4 | 25 | 25 | 0.0724111 | 0.561234 | 0.685016 | none |
| 2-5 | 25 | 25 | 0.0550485 | 0.308644 | 0.904739 | none |
| 2-6 | 24 | 24 | 0.0391678 | 0.270807 | 0.926663 | none |
| 3-1 | 25 | 25 | 0.0427577 | 0.329472 | 0.891448 | none |
| 3-2 | 25 | 25 | 0.0126042 | 0.0918779 | 0.991558 | none |
| 3-3 | 25 | 25 | 0.0174365 | 0.12093 | 0.985376 | none |
| 3-4 | 25 | 25 | 0.0430695 | 0.430695 | 0.814501 | none |
| 3-5 | 25 | 25 | 0.0556398 | 0.448569 | 0.798786 | none |
| 3-6 | 24 | 24 | 0.037129 | 0.238946 | 0.942905 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.37, 1, 0.992, 0.375; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![AngularDeadzone test](plots/AngularDeadzone_test.png)

*Candidate AngularDeadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of AngularDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![AngularDeadzone train](plots/AngularDeadzone_train.png)

*Candidate AngularDeadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of AngularDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate PhaseAdjusted

Position in the agent's order: 5. Status: evaluated.
File and expression checks: passed.
- `x_next = x + Ts*(gf*v_f)*cos(phi + alpha*Ts*(ga*v_a + ba))`
- `y_next = y + Ts*(gf*v_f)*sin(phi + alpha*Ts*(ga*v_a + ba))`
- `phi_next = atan2(sin(phi + Ts*(ga*v_a + ba)), cos(phi + Ts*(ga*v_a + ba)))`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 55 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 5: `x_next = 0.20000000000000001*P1*v_f*cos(0.20000000000000001*P2*(P3 + P4*v_a) + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(0.20000000000000001*P2*(P3 + P4*v_a) + phi) + y`; `phi_next = atan2(sin(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi), cos(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0401728 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0523733 | 0.18707 | 0.965005 | none |
| test-2 | 25 | 25 | 0.0077639 | 0.101379 | 0.989722 | none |
| test-3 | 25 | 25 | 0.0599557 | 0.409882 | 0.831997 | none |
| test-4 | 25 | 25 | 0.0228708 | 0.152168 | 0.976845 | none |
| test-5 | 25 | 25 | 0.0347389 | 0.155843 | 0.975713 | none |
| test-6 | 24 | 24 | 0.0495767 | 0.394209 | 0.8446 | none |
| test-7 | 25 | 25 | 0.0454562 | 0.490372 | 0.759535 | none |
| test-8 | 25 | 25 | 0.00926896 | 0.0514611 | 0.997352 | none |
| test-9 | 25 | 25 | 0.0294464 | 0.222514 | 0.950488 | none |
| test-10 | 25 | 25 | 0.00997965 | 0.14694 | 0.978409 | none |
| test-11 | 25 | 25 | 0.0747505 | 0.955812 | 0.0864233 | none |
| test-12 | 24 | 24 | 0.00671749 | 0.0504738 | 0.997452 | none |

Output errors on the training data (pooled RMSE: 0.040723 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.034165 | 0.670401 | 0.550562 | none |
| 1-2 | 25 | 25 | 0.00565319 | 0.073419 | 0.99461 | none |
| 1-3 | 25 | 25 | 0.0202143 | 0.223068 | 0.950241 | none |
| 1-4 | 25 | 25 | 0.0616873 | 1.23927 | -0.535797 | none |
| 1-5 | 25 | 25 | 0.0371387 | 0.248928 | 0.938035 | none |
| 1-6 | 24 | 24 | 0.0606475 | 1.67154 | -1.79404 | none |
| 2-1 | 25 | 25 | 0.0359589 | 0.38059 | 0.855151 | none |
| 2-2 | 25 | 25 | 0.0323359 | 0.315388 | 0.90053 | none |
| 2-3 | 25 | 25 | 0.0187244 | 0.272718 | 0.925625 | none |
| 2-4 | 25 | 25 | 0.0673036 | 0.521647 | 0.727884 | none |
| 2-5 | 25 | 25 | 0.0630231 | 0.353356 | 0.87514 | none |
| 2-6 | 24 | 24 | 0.0366424 | 0.253347 | 0.935815 | none |
| 3-1 | 25 | 25 | 0.0431311 | 0.332349 | 0.889544 | none |
| 3-2 | 25 | 25 | 0.0156655 | 0.114194 | 0.98696 | none |
| 3-3 | 25 | 25 | 0.0162194 | 0.112488 | 0.987346 | none |
| 3-4 | 25 | 25 | 0.036872 | 0.368721 | 0.864045 | none |
| 3-5 | 25 | 25 | 0.0435862 | 0.351393 | 0.876523 | none |
| 3-6 | 24 | 24 | 0.0356512 | 0.229436 | 0.947359 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.05, 1, 0.999, 0.952; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![PhaseAdjusted test](plots/PhaseAdjusted_test.png)

*Candidate PhaseAdjusted, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of PhaseAdjusted; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![PhaseAdjusted train](plots/PhaseAdjusted_train.png)

*Candidate PhaseAdjusted, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of PhaseAdjusted; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate SparseCommandMap

Position in the agent's order: 6. Status: evaluated.
File and expression checks: passed.
- `x_next = x + Ts*(gf*sign(v_f)*Max(Abs(v_f)-df, 0))*cos(phi + 0.5*Ts*(ga*v_a + gc*v_a**3 + gv*v_f*v_a + ba))`
- `y_next = y + Ts*(gf*sign(v_f)*Max(Abs(v_f)-df, 0))*sin(phi + 0.5*Ts*(ga*v_a + gc*v_a**3 + gv*v_f*v_a + ba))`
- `phi_next = atan2(sin(phi + Ts*(ga*v_a + gc*v_a**3 + gv*v_f*v_a + ba)), cos(phi + Ts*(ga*v_a + gc*v_a**3 + gv*v_f*v_a + ba)))`
Complexity: 6 fitted, 1 fixed and 0 tied parameters; 2 non-integer numeric literals; 109 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 6: `x_next = 0.20000000000000001*P1*cos(0.10000000000000001*P3 + 0.10000000000000001*P4*v_a + 0.10000000000000001*P5*v_a**3 + 0.10000000000000001*P6*v_a*v_f + phi)*sign(v_f)*Max(0, -P2 + Abs(v_f)) + x`; `y_next = 0.20000000000000001*P1*sin(0.10000000000000001*P3 + 0.10000000000000001*P4*v_a + 0.10000000000000001*P5*v_a**3 + 0.10000000000000001*P6*v_a*v_f + phi)*sign(v_f)*Max(0, -P2 + Abs(v_f)) + y`; `phi_next = atan2(sin(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + 0.20000000000000001*P5*v_a**3 + 0.20000000000000001*P6*v_a*v_f + phi), cos(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + 0.20000000000000001*P5*v_a**3 + 0.20000000000000001*P6*v_a*v_f + phi))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.042856 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.064435 | 0.230153 | 0.947029 | none |
| test-2 | 25 | 25 | 0.00999715 | 0.13054 | 0.982959 | none |
| test-3 | 25 | 25 | 0.0607192 | 0.415102 | 0.827691 | none |
| test-4 | 25 | 25 | 0.0239196 | 0.159146 | 0.974672 | none |
| test-5 | 25 | 25 | 0.0328636 | 0.14743 | 0.978264 | none |
| test-6 | 24 | 24 | 0.0619508 | 0.492602 | 0.757344 | none |
| test-7 | 25 | 25 | 0.0329668 | 0.355638 | 0.873521 | none |
| test-8 | 25 | 25 | 0.0065456 | 0.0363411 | 0.998679 | none |
| test-9 | 25 | 25 | 0.0352115 | 0.266078 | 0.929202 | none |
| test-10 | 25 | 25 | 0.0117513 | 0.173025 | 0.970062 | none |
| test-11 | 25 | 25 | 0.0769118 | 0.983447 | 0.032831 | none |
| test-12 | 24 | 24 | 0.0142322 | 0.106938 | 0.988564 | none |

Output errors on the training data (pooled RMSE: 0.0389385 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0296201 | 0.58122 | 0.662183 | none |
| 1-2 | 25 | 25 | 0.0115883 | 0.1505 | 0.97735 | none |
| 1-3 | 25 | 25 | 0.0301231 | 0.332413 | 0.889502 | none |
| 1-4 | 25 | 25 | 0.0622225 | 1.25003 | -0.562563 | none |
| 1-5 | 25 | 25 | 0.0317759 | 0.212983 | 0.954638 | none |
| 1-6 | 24 | 24 | 0.0499579 | 1.37692 | -0.895899 | none |
| 2-1 | 25 | 25 | 0.0361886 | 0.383021 | 0.853295 | none |
| 2-2 | 25 | 25 | 0.027857 | 0.271704 | 0.926177 | none |
| 2-3 | 25 | 25 | 0.0195621 | 0.284919 | 0.918821 | none |
| 2-4 | 25 | 25 | 0.0674447 | 0.522742 | 0.726741 | none |
| 2-5 | 25 | 25 | 0.0642706 | 0.360351 | 0.870148 | none |
| 2-6 | 24 | 24 | 0.0353322 | 0.244288 | 0.940323 | none |
| 3-1 | 25 | 25 | 0.0379176 | 0.292176 | 0.914633 | none |
| 3-2 | 25 | 25 | 0.0131133 | 0.0955894 | 0.990863 | none |
| 3-3 | 25 | 25 | 0.0127017 | 0.0880917 | 0.99224 | none |
| 3-4 | 25 | 25 | 0.0193026 | 0.193026 | 0.962741 | none |
| 3-5 | 25 | 25 | 0.0447985 | 0.361166 | 0.869559 | none |
| 3-6 | 24 | 24 | 0.0384145 | 0.247219 | 0.938883 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.66, 1.36, 1, 0.4, 0.381, 0.279; rank 6 of 6.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![SparseCommandMap test](plots/SparseCommandMap_test.png)

*Candidate SparseCommandMap, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of SparseCommandMap; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![SparseCommandMap train](plots/SparseCommandMap_train.png)

*Candidate SparseCommandMap, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of SparseCommandMap; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
