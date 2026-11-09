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
| candidates proposed | 4 |
| accepted by the file and expression checks | 4 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 4 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 4 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 4 among 4 evaluated candidates; groups: calibrated_unicycle; wheel_deadzone; body_offset; angular_deadzone. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: calibrated_unicycle. The agent's reason: Recommend the two-gain midpoint unicycle for stable calibration and low complexity. On leave-one-trajectory-out 5 s windows initialized at every available pose of data/train.csv, its held-out `x` RMSE is 0.029706 m, versus 0.029508 m for the four-parameter wheel dead-zone alternative, 0.029838 m for the body-frame correction, and 0.030819 m for the angular dead zone. The wheel model advantage is small and its fitted mixing length is unstable across trajectory splits, including one bound-active fit. With command-change-only starts the baseline validation RMSE is 0.032366 m versus 0.032973 m for the wheel alternative. These are internal validation, not hidden-test results. The pool tests genuinely different command-response and body-geometry structures, not multiple gain variants of the recommended form.
- Test score S of the recommended candidate (practical selection): 0.0423582 m; eligible: True; rank in the oracle-based selection: 3.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 4 eligible of 4 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | angular_deadzone | 0.0382131 | none | none |
| 2 | body_offset | 0.0416745 | none | none |
| 3 | calibrated_unicycle | 0.0423582 | none | none |
| 4 | wheel_deadzone | 0.0451697 | none | none |

## Candidates

### Candidate calibrated_unicycle

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = x + ts*gv*v_f*cos(phi + ts*gw*v_a/2)`
- `y_next = y + ts*gv*v_f*sin(phi + ts*gw*v_a/2)`
- `phi_next = phi + ts*gw*v_a`
Complexity: 2 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 34 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = 0.20000000000000001*P1*v_f*cos(0.10000000000000001*P2*v_a + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(0.10000000000000001*P2*v_a + phi) + y`; `phi_next = 0.20000000000000001*P2*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0423582 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0407359 | 0.145503 | 0.978829 | none |
| test-2 | 25 | 25 | 0.00834995 | 0.109031 | 0.988112 | none |
| test-3 | 25 | 25 | 0.0500503 | 0.342165 | 0.882923 | none |
| test-4 | 25 | 25 | 0.0274829 | 0.182854 | 0.966564 | none |
| test-5 | 25 | 25 | 0.0423659 | 0.190059 | 0.963878 | none |
| test-6 | 24 | 24 | 0.0773714 | 0.615219 | 0.621506 | none |
| test-7 | 25 | 25 | 0.0498204 | 0.537452 | 0.711145 | none |
| test-8 | 25 | 25 | 0.00682504 | 0.0378925 | 0.998564 | none |
| test-9 | 25 | 25 | 0.0402955 | 0.304495 | 0.907283 | none |
| test-10 | 25 | 25 | 0.00968927 | 0.142665 | 0.979647 | none |
| test-11 | 25 | 25 | 0.0676875 | 0.865499 | 0.250912 | none |
| test-12 | 24 | 24 | 0.00539545 | 0.0405402 | 0.998356 | none |

Output errors on the training data (pooled RMSE: 0.0390513 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0296969 | 0.582726 | 0.66043 | none |
| 1-2 | 25 | 25 | 0.00690531 | 0.0896805 | 0.991957 | none |
| 1-3 | 25 | 25 | 0.0348615 | 0.384702 | 0.852004 | none |
| 1-4 | 25 | 25 | 0.0671614 | 1.34925 | -0.820463 | none |
| 1-5 | 25 | 25 | 0.0400748 | 0.268608 | 0.92785 | none |
| 1-6 | 24 | 24 | 0.0446105 | 1.22954 | -0.511756 | none |
| 2-1 | 25 | 25 | 0.0227795 | 0.2411 | 0.941871 | none |
| 2-2 | 25 | 25 | 0.0245954 | 0.239891 | 0.942452 | none |
| 2-3 | 25 | 25 | 0.00770321 | 0.112196 | 0.987412 | none |
| 2-4 | 25 | 25 | 0.052713 | 0.408561 | 0.833078 | none |
| 2-5 | 25 | 25 | 0.0778635 | 0.436562 | 0.809413 | none |
| 2-6 | 24 | 24 | 0.0454333 | 0.314127 | 0.901324 | none |
| 3-1 | 25 | 25 | 0.0357152 | 0.275205 | 0.924262 | none |
| 3-2 | 25 | 25 | 0.0147852 | 0.107777 | 0.988384 | none |
| 3-3 | 25 | 25 | 0.0125827 | 0.0872666 | 0.992385 | none |
| 3-4 | 25 | 25 | 0.029167 | 0.29167 | 0.914929 | none |
| 3-5 | 25 | 25 | 0.0422358 | 0.340506 | 0.884056 | none |
| 3-6 | 24 | 24 | 0.0288996 | 0.185985 | 0.965409 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1, 1; rank 2 of 2.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![calibrated_unicycle test](plots/calibrated_unicycle_test.png)

*Candidate calibrated_unicycle, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of calibrated_unicycle; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![calibrated_unicycle train](plots/calibrated_unicycle_train.png)

*Candidate calibrated_unicycle, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of calibrated_unicycle; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate wheel_deadzone

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = x + ts*(gv*((sign(v_f + halftrack*v_a)*Max(Abs(v_f + halftrack*v_a) - fric, 0)) + (sign(v_f - halftrack*v_a)*Max(Abs(v_f - halftrack*v_a) - fric, 0)))/2)*cos(phi + ts*(gw*((sign(v_f + halftrack*v_a)*Max(Abs(v_f + halftrack*v_a) - fric, 0)) - (sign(v_f - halftrack*v_a)*Max(Abs(v_f - halftrack*v_a) - fric, 0)))/(2*halftrack))/2)`
- `y_next = y + ts*(gv*((sign(v_f + halftrack*v_a)*Max(Abs(v_f + halftrack*v_a) - fric, 0)) + (sign(v_f - halftrack*v_a)*Max(Abs(v_f - halftrack*v_a) - fric, 0)))/2)*sin(phi + ts*(gw*((sign(v_f + halftrack*v_a)*Max(Abs(v_f + halftrack*v_a) - fric, 0)) - (sign(v_f - halftrack*v_a)*Max(Abs(v_f - halftrack*v_a) - fric, 0)))/(2*halftrack))/2)`
- `phi_next = phi + ts*(gw*((sign(v_f + halftrack*v_a)*Max(Abs(v_f + halftrack*v_a) - fric, 0)) - (sign(v_f - halftrack*v_a)*Max(Abs(v_f - halftrack*v_a) - fric, 0)))/(2*halftrack))`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 254 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = 0.10000000000000001*P1*(sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))*cos(phi + 0.050000000000000003*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3) + x`; `y_next = 0.10000000000000001*P1*(sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))*sin(phi + 0.050000000000000003*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3) + y`; `phi_next = phi + 0.10000000000000001*P4*(-sign(-P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a - v_f)) + sign(P3*v_a + v_f)*Max(0, -P2 + Abs(P3*v_a + v_f)))/P3`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0451697 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0536005 | 0.191454 | 0.963345 | none |
| test-2 | 25 | 25 | 0.0102943 | 0.13442 | 0.981931 | none |
| test-3 | 25 | 25 | 0.0598648 | 0.409261 | 0.832506 | none |
| test-4 | 25 | 25 | 0.0207274 | 0.137907 | 0.980982 | none |
| test-5 | 25 | 25 | 0.0457228 | 0.205118 | 0.957927 | none |
| test-6 | 24 | 24 | 0.0899418 | 0.715171 | 0.48853 | none |
| test-7 | 25 | 25 | 0.0436443 | 0.470826 | 0.778323 | none |
| test-8 | 25 | 25 | 0.00745683 | 0.0414002 | 0.998286 | none |
| test-9 | 25 | 25 | 0.0308875 | 0.233403 | 0.945523 | none |
| test-10 | 25 | 25 | 0.0131013 | 0.192903 | 0.962788 | none |
| test-11 | 25 | 25 | 0.0660595 | 0.844683 | 0.286511 | none |
| test-12 | 24 | 24 | 0.00473212 | 0.0355561 | 0.998736 | none |

Output errors on the training data (pooled RMSE: 0.0373942 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.030409 | 0.5967 | 0.643949 | none |
| 1-2 | 25 | 25 | 0.00574692 | 0.0746362 | 0.994429 | none |
| 1-3 | 25 | 25 | 0.0510872 | 0.563756 | 0.682179 | none |
| 1-4 | 25 | 25 | 0.0611009 | 1.22749 | -0.506736 | none |
| 1-5 | 25 | 25 | 0.033921 | 0.227361 | 0.948307 | none |
| 1-6 | 24 | 24 | 0.0466735 | 1.28639 | -0.654811 | none |
| 2-1 | 25 | 25 | 0.0272605 | 0.288526 | 0.916753 | none |
| 2-2 | 25 | 25 | 0.0242263 | 0.236292 | 0.944166 | none |
| 2-3 | 25 | 25 | 0.00619357 | 0.0902085 | 0.991862 | none |
| 2-4 | 25 | 25 | 0.0459114 | 0.355844 | 0.873375 | none |
| 2-5 | 25 | 25 | 0.0735328 | 0.412281 | 0.830024 | none |
| 2-6 | 24 | 24 | 0.0243415 | 0.168298 | 0.971676 | none |
| 3-1 | 25 | 25 | 0.0304531 | 0.234658 | 0.944936 | none |
| 3-2 | 25 | 25 | 0.0136676 | 0.0996294 | 0.990074 | none |
| 3-3 | 25 | 25 | 0.0202177 | 0.140218 | 0.980339 | none |
| 3-4 | 25 | 25 | 0.0238499 | 0.238499 | 0.943118 | none |
| 3-5 | 25 | 25 | 0.0390101 | 0.3145 | 0.90109 | none |
| 3-6 | 24 | 24 | 0.0380987 | 0.245187 | 0.939883 | none |

- Failed computation (sensitivity rank test): NameError: name 'DiracDelta' is not defined
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![wheel_deadzone test](plots/wheel_deadzone_test.png)

*Candidate wheel_deadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of wheel_deadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![wheel_deadzone train](plots/wheel_deadzone_train.png)

*Candidate wheel_deadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of wheel_deadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate body_offset

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = x + ts*(gv*v_f*cos(phi + ts*(gw*v_a + bw)/2) - lever*(gw*v_a + bw)*sin(phi + ts*(gw*v_a + bw)/2))`
- `y_next = y + ts*(gv*v_f*sin(phi + ts*(gw*v_a + bw)/2) + lever*(gw*v_a + bw)*cos(phi + ts*(gw*v_a + bw)/2))`
- `phi_next = phi + ts*(gw*v_a + bw)`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 84 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = 0.20000000000000001*P1*v_f*cos(0.10000000000000001*P2 + 0.10000000000000001*P3*v_a + phi) - 0.20000000000000001*P4*(P2 + P3*v_a)*sin(0.10000000000000001*P2 + 0.10000000000000001*P3*v_a + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(0.10000000000000001*P2 + 0.10000000000000001*P3*v_a + phi) + 0.20000000000000001*P4*(P2 + P3*v_a)*cos(0.10000000000000001*P2 + 0.10000000000000001*P3*v_a + phi) + y`; `phi_next = 0.20000000000000001*P2 + 0.20000000000000001*P3*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0416745 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0427553 | 0.152716 | 0.976678 | none |
| test-2 | 25 | 25 | 0.0109924 | 0.143536 | 0.979398 | none |
| test-3 | 25 | 25 | 0.0444782 | 0.304071 | 0.907541 | none |
| test-4 | 25 | 25 | 0.0281313 | 0.187168 | 0.964968 | none |
| test-5 | 25 | 25 | 0.0413964 | 0.18571 | 0.965512 | none |
| test-6 | 24 | 24 | 0.0755398 | 0.600654 | 0.639214 | none |
| test-7 | 25 | 25 | 0.0600747 | 0.648073 | 0.580002 | none |
| test-8 | 25 | 25 | 0.00837364 | 0.0464903 | 0.997839 | none |
| test-9 | 25 | 25 | 0.0391662 | 0.295961 | 0.912407 | none |
| test-10 | 25 | 25 | 0.00850417 | 0.125215 | 0.984321 | none |
| test-11 | 25 | 25 | 0.0580328 | 0.742048 | 0.449365 | none |
| test-12 | 24 | 24 | 0.0120258 | 0.090359 | 0.991835 | none |

Output errors on the training data (pooled RMSE: 0.0396149 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0321265 | 0.630401 | 0.602595 | none |
| 1-2 | 25 | 25 | 0.00885628 | 0.115018 | 0.986771 | none |
| 1-3 | 25 | 25 | 0.0416012 | 0.459076 | 0.78925 | none |
| 1-4 | 25 | 25 | 0.0687566 | 1.38129 | -0.907968 | none |
| 1-5 | 25 | 25 | 0.0354762 | 0.237785 | 0.943458 | none |
| 1-6 | 24 | 24 | 0.0522637 | 1.44047 | -1.07495 | none |
| 2-1 | 25 | 25 | 0.024427 | 0.258536 | 0.933159 | none |
| 2-2 | 25 | 25 | 0.0272861 | 0.266135 | 0.929172 | none |
| 2-3 | 25 | 25 | 0.0161989 | 0.235935 | 0.944335 | none |
| 2-4 | 25 | 25 | 0.0519452 | 0.40261 | 0.837905 | none |
| 2-5 | 25 | 25 | 0.0769116 | 0.431225 | 0.814045 | none |
| 2-6 | 24 | 24 | 0.0439763 | 0.304054 | 0.907551 | none |
| 3-1 | 25 | 25 | 0.0352412 | 0.271553 | 0.926259 | none |
| 3-2 | 25 | 25 | 0.0143372 | 0.104511 | 0.989077 | none |
| 3-3 | 25 | 25 | 0.0132764 | 0.0920772 | 0.991522 | none |
| 3-4 | 25 | 25 | 0.0210553 | 0.210553 | 0.955667 | none |
| 3-5 | 25 | 25 | 0.0435091 | 0.350771 | 0.876959 | none |
| 3-6 | 24 | 24 | 0.0245006 | 0.157676 | 0.975138 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.05, 1, 0.999, 0.952; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![body_offset test](plots/body_offset_test.png)

*Candidate body_offset, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of body_offset; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![body_offset train](plots/body_offset_train.png)

*Candidate body_offset, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of body_offset; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate angular_deadzone

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `x_next = x + ts*gv*v_f*cos(phi + ts*(gw*sign(v_a)*Max(Abs(v_a) - dead, 0))/2)`
- `y_next = y + ts*gv*v_f*sin(phi + ts*(gw*sign(v_a)*Max(Abs(v_a) - dead, 0))/2)`
- `phi_next = phi + ts*(gw*sign(v_a)*Max(Abs(v_a) - dead, 0))`
Complexity: 3 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 61 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `x_next = 0.20000000000000001*P1*v_f*cos(0.10000000000000001*P2*sign(v_a)*Max(0, -P3 + Abs(v_a)) + phi) + x`; `y_next = 0.20000000000000001*P1*v_f*sin(0.10000000000000001*P2*sign(v_a)*Max(0, -P3 + Abs(v_a)) + phi) + y`; `phi_next = 0.20000000000000001*P2*sign(v_a)*Max(0, -P3 + Abs(v_a)) + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0382131 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0528368 | 0.188726 | 0.964382 | none |
| test-2 | 25 | 25 | 0.00790515 | 0.103223 | 0.989345 | none |
| test-3 | 25 | 25 | 0.0525162 | 0.359023 | 0.871103 | none |
| test-4 | 25 | 25 | 0.0211095 | 0.14045 | 0.980274 | none |
| test-5 | 25 | 25 | 0.0345273 | 0.154894 | 0.976008 | none |
| test-6 | 24 | 24 | 0.0592406 | 0.471051 | 0.778111 | none |
| test-7 | 25 | 25 | 0.0492951 | 0.531785 | 0.717205 | none |
| test-8 | 25 | 25 | 0.00584921 | 0.0324747 | 0.998945 | none |
| test-9 | 25 | 25 | 0.0325767 | 0.246167 | 0.939402 | none |
| test-10 | 25 | 25 | 0.00989497 | 0.145693 | 0.978773 | none |
| test-11 | 25 | 25 | 0.0559923 | 0.715957 | 0.487406 | none |
| test-12 | 24 | 24 | 0.00545962 | 0.0410224 | 0.998317 | none |

Output errors on the training data (pooled RMSE: 0.0398093 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0325952 | 0.639598 | 0.590915 | none |
| 1-2 | 25 | 25 | 0.00451741 | 0.0586684 | 0.996558 | none |
| 1-3 | 25 | 25 | 0.0375314 | 0.414165 | 0.828467 | none |
| 1-4 | 25 | 25 | 0.0647649 | 1.3011 | -0.69286 | none |
| 1-5 | 25 | 25 | 0.0315963 | 0.211779 | 0.95515 | none |
| 1-6 | 24 | 24 | 0.0383785 | 1.05777 | -0.118879 | none |
| 2-1 | 25 | 25 | 0.0264816 | 0.280283 | 0.921442 | none |
| 2-2 | 25 | 25 | 0.0169721 | 0.165538 | 0.972597 | none |
| 2-3 | 25 | 25 | 0.00757558 | 0.110337 | 0.987826 | none |
| 2-4 | 25 | 25 | 0.0654616 | 0.507371 | 0.742575 | none |
| 2-5 | 25 | 25 | 0.0608335 | 0.34108 | 0.883665 | none |
| 2-6 | 24 | 24 | 0.0439309 | 0.30374 | 0.907742 | none |
| 3-1 | 25 | 25 | 0.0440659 | 0.339552 | 0.884704 | none |
| 3-2 | 25 | 25 | 0.0158539 | 0.115567 | 0.986644 | none |
| 3-3 | 25 | 25 | 0.0195034 | 0.135264 | 0.981704 | none |
| 3-4 | 25 | 25 | 0.0458351 | 0.458351 | 0.789914 | none |
| 3-5 | 25 | 25 | 0.0504855 | 0.407015 | 0.834339 | none |
| 3-6 | 24 | 24 | 0.034295 | 0.220708 | 0.951288 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1, 0.377; rank 3 of 3.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![angular_deadzone test](plots/angular_deadzone_test.png)

*Candidate angular_deadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of angular_deadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![angular_deadzone train](plots/angular_deadzone_train.png)

*Candidate angular_deadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of angular_deadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
