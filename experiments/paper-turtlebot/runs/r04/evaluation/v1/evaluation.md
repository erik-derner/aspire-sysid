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
| candidates proposed | 5 |
| accepted by the file and expression checks | 5 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 5 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 5 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 5 among 5 evaluated candidates; groups: RectifiedEuler; AffineArc; TurnDeadzone; CubicArc; WheelDeadzone. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: RectifiedEuler. The agent's reason: Recommend `RectifiedEuler`: its pooled leave-one-trajectory-out `25`-step (`5` s) rolling-window `x` RMSE was `0.02906545` m, the lowest among explored model families, while retaining four interpretable parameters and preventing artificial negative forward speed at tiny nonnegative commands. The simpler proportional Euler fit was almost tied (`0.02908078` m), so the threshold benefit is small, not statistically established. Exact arcs, nonlinear angular response, and wheel thresholds did not improve this held-out scored-output metric. Actual test trajectories and test scores were not available; overlapping-window and three-trajectory validation limits confidence.
- Test score S of the recommended candidate (practical selection): 0.0443148 m; eligible: True; rank in the oracle-based selection: 4.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 5 eligible of 5 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | TurnDeadzone | 0.040756 | none | none |
| 2 | AffineArc | 0.0426796 | none | none |
| 3 | WheelDeadzone | 0.0435268 | none | none |
| 4 | RectifiedEuler | 0.0443148 | none | none |
| 5 | CubicArc | 0.0456915 | none | none |

## Candidates

### Candidate RectifiedEuler

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = x+Ts*(gf*Max(v_f-df,0))*cos(phi)`
- `y_next = y+Ts*(gf*Max(v_f-df,0))*sin(phi)`
- `phi_next = phi+Ts*(ga*v_a+ba)`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 37 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = 0.20000000000000001*P1*cos(phi)*Max(0, -P2 + v_f) + x`; `y_next = 0.20000000000000001*P1*sin(phi)*Max(0, -P2 + v_f) + y`; `phi_next = 0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0443148 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.054777 | 0.195656 | 0.961719 | none |
| test-2 | 25 | 25 | 0.0130325 | 0.170175 | 0.971041 | none |
| test-3 | 25 | 25 | 0.0493192 | 0.337167 | 0.886319 | none |
| test-4 | 25 | 25 | 0.0307016 | 0.204269 | 0.958274 | none |
| test-5 | 25 | 25 | 0.0400914 | 0.179855 | 0.967652 | none |
| test-6 | 24 | 24 | 0.0717861 | 0.570807 | 0.67418 | none |
| test-7 | 25 | 25 | 0.0671887 | 0.724818 | 0.474639 | none |
| test-8 | 25 | 25 | 0.0118016 | 0.0655224 | 0.995707 | none |
| test-9 | 25 | 25 | 0.0412886 | 0.312 | 0.902656 | none |
| test-10 | 25 | 25 | 0.0150779 | 0.222007 | 0.950713 | none |
| test-11 | 25 | 25 | 0.0606404 | 0.77539 | 0.39877 | none |
| test-12 | 24 | 24 | 0.00690653 | 0.0518942 | 0.997307 | none |

Output errors on the training data (pooled RMSE: 0.0391659 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0266557 | 0.523051 | 0.726418 | none |
| 1-2 | 25 | 25 | 0.0159178 | 0.206727 | 0.957264 | none |
| 1-3 | 25 | 25 | 0.0355019 | 0.39177 | 0.846517 | none |
| 1-4 | 25 | 25 | 0.0701026 | 1.40833 | -0.983399 | none |
| 1-5 | 25 | 25 | 0.0367955 | 0.246628 | 0.939175 | none |
| 1-6 | 24 | 24 | 0.0447438 | 1.23321 | -0.520799 | none |
| 2-1 | 25 | 25 | 0.0214549 | 0.227079 | 0.948435 | none |
| 2-2 | 25 | 25 | 0.0309761 | 0.302126 | 0.90872 | none |
| 2-3 | 25 | 25 | 0.0148646 | 0.216501 | 0.953127 | none |
| 2-4 | 25 | 25 | 0.0531539 | 0.411978 | 0.830274 | none |
| 2-5 | 25 | 25 | 0.0696341 | 0.390422 | 0.847571 | none |
| 2-6 | 24 | 24 | 0.0495587 | 0.342651 | 0.882591 | none |
| 3-1 | 25 | 25 | 0.0368556 | 0.283993 | 0.919348 | none |
| 3-2 | 25 | 25 | 0.0112953 | 0.0823369 | 0.993221 | none |
| 3-3 | 25 | 25 | 0.00976382 | 0.0677161 | 0.995415 | none |
| 3-4 | 25 | 25 | 0.0326159 | 0.326159 | 0.89362 | none |
| 3-5 | 25 | 25 | 0.0452269 | 0.36462 | 0.867052 | none |
| 3-6 | 24 | 24 | 0.026011 | 0.167396 | 0.971979 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.05, 0.952, 0.383; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![RectifiedEuler test](plots/RectifiedEuler_test.png)

*Candidate RectifiedEuler, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of RectifiedEuler; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![RectifiedEuler train](plots/RectifiedEuler_train.png)

*Candidate RectifiedEuler, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of RectifiedEuler; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate AffineArc

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = x+Piecewise((Ts*(gf*v_f+bf)*cos(phi), Eq((ga*v_a+ba),0)), ((gf*v_f+bf)*(sin(phi+Ts*(ga*v_a+ba))-sin(phi))/(ga*v_a+ba), True))`
- `y_next = y+Piecewise((Ts*(gf*v_f+bf)*sin(phi), Eq((ga*v_a+ba),0)), ((gf*v_f+bf)*(cos(phi)-cos(phi+Ts*(ga*v_a+ba)))/(ga*v_a+ba), True))`
- `phi_next = phi+Ts*(ga*v_a+ba)`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 105 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = x + Piecewise((0.20000000000000001*(P1 + P2*v_f)*cos(phi), Eq(P3 + P4*v_a, 0)), ((P1 + P2*v_f)*(-sin(phi) + sin(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi))/(P3 + P4*v_a), True))`; `y_next = y + Piecewise((0.20000000000000001*(P1 + P2*v_f)*sin(phi), Eq(P3 + P4*v_a, 0)), ((P1 + P2*v_f)*(cos(phi) - cos(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi))/(P3 + P4*v_a), True))`; `phi_next = 0.20000000000000001*P3 + 0.20000000000000001*P4*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0426796 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0572691 | 0.204558 | 0.958156 | none |
| test-2 | 25 | 25 | 0.0112112 | 0.146393 | 0.978569 | none |
| test-3 | 25 | 25 | 0.0519156 | 0.354917 | 0.874034 | none |
| test-4 | 25 | 25 | 0.0290783 | 0.193469 | 0.96257 | none |
| test-5 | 25 | 25 | 0.0374314 | 0.167922 | 0.971802 | none |
| test-6 | 24 | 24 | 0.0649391 | 0.516363 | 0.733369 | none |
| test-7 | 25 | 25 | 0.0560489 | 0.604643 | 0.634407 | none |
| test-8 | 25 | 25 | 0.00811748 | 0.0450681 | 0.997969 | none |
| test-9 | 25 | 25 | 0.0394165 | 0.297853 | 0.911284 | none |
| test-10 | 25 | 25 | 0.0121106 | 0.178316 | 0.968203 | none |
| test-11 | 25 | 25 | 0.0659564 | 0.843364 | 0.288737 | none |
| test-12 | 24 | 24 | 0.00784779 | 0.0589665 | 0.996523 | none |

Output errors on the training data (pooled RMSE: 0.038259 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0218327 | 0.428411 | 0.816464 | none |
| 1-2 | 25 | 25 | 0.0145743 | 0.189279 | 0.964173 | none |
| 1-3 | 25 | 25 | 0.0350229 | 0.386484 | 0.85063 | none |
| 1-4 | 25 | 25 | 0.0647987 | 1.30178 | -0.694632 | none |
| 1-5 | 25 | 25 | 0.0365461 | 0.244956 | 0.939997 | none |
| 1-6 | 24 | 24 | 0.042498 | 1.17131 | -0.371964 | none |
| 2-1 | 25 | 25 | 0.024599 | 0.260357 | 0.932214 | none |
| 2-2 | 25 | 25 | 0.0285226 | 0.278195 | 0.922607 | none |
| 2-3 | 25 | 25 | 0.012943 | 0.188513 | 0.964463 | none |
| 2-4 | 25 | 25 | 0.0597333 | 0.462973 | 0.785656 | none |
| 2-5 | 25 | 25 | 0.0657544 | 0.368669 | 0.864083 | none |
| 2-6 | 24 | 24 | 0.0442268 | 0.305786 | 0.906495 | none |
| 3-1 | 25 | 25 | 0.0354835 | 0.27342 | 0.925242 | none |
| 3-2 | 25 | 25 | 0.0111857 | 0.0815379 | 0.993352 | none |
| 3-3 | 25 | 25 | 0.0100287 | 0.069553 | 0.995162 | none |
| 3-4 | 25 | 25 | 0.0318652 | 0.318652 | 0.898461 | none |
| 3-5 | 25 | 25 | 0.0463864 | 0.373968 | 0.860148 | none |
| 3-6 | 24 | 24 | 0.0319563 | 0.205657 | 0.957705 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.05, 0.953, 0.387; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![AffineArc test](plots/AffineArc_test.png)

*Candidate AffineArc, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of AffineArc; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![AffineArc train](plots/AffineArc_train.png)

*Candidate AffineArc, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of AffineArc; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate TurnDeadzone

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = x+Piecewise((Ts*(gf*v_f+bf)*cos(phi), Eq((ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba),0)), ((gf*v_f+bf)*(sin(phi+Ts*(ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba))-sin(phi))/(ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba), True))`
- `y_next = y+Piecewise((Ts*(gf*v_f+bf)*sin(phi), Eq((ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba),0)), ((gf*v_f+bf)*(cos(phi)-cos(phi+Ts*(ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba)))/(ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba), True))`
- `phi_next = phi+Ts*(ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba)`
Complexity: 5 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 168 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = x + Piecewise((0.20000000000000001*(P1 + P2*v_f)*cos(phi), Eq(P3 + P4*sign(v_a)*Max(0, -P5 + Abs(v_a)), 0)), ((P1 + P2*v_f)*(-sin(phi) + sin(0.20000000000000001*P3 + 0.20000000000000001*P4*sign(v_a)*Max(0, -P5 + Abs(v_a)) + phi))/(P3 + P4*sign(v_a)*Max(0, -P5 + Abs(v_a))), True))`; `y_next = y + Piecewise((0.20000000000000001*(P1 + P2*v_f)*sin(phi), Eq(P3 + P4*sign(v_a)*Max(0, -P5 + Abs(v_a)), 0)), ((P1 + P2*v_f)*(cos(phi) - cos(0.20000000000000001*P3 + 0.20000000000000001*P4*sign(v_a)*Max(0, -P5 + Abs(v_a)) + phi))/(P3 + P4*sign(v_a)*Max(0, -P5 + Abs(v_a))), True))`; `phi_next = 0.20000000000000001*P3 + 0.20000000000000001*P4*sign(v_a)*Max(0, -P5 + Abs(v_a)) + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.040756 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0733495 | 0.261995 | 0.931359 | none |
| test-2 | 25 | 25 | 0.0125397 | 0.16374 | 0.973189 | none |
| test-3 | 25 | 25 | 0.0525961 | 0.359569 | 0.87071 | none |
| test-4 | 25 | 25 | 0.0251405 | 0.16727 | 0.972021 | none |
| test-5 | 25 | 25 | 0.0295569 | 0.132596 | 0.982418 | none |
| test-6 | 24 | 24 | 0.04827 | 0.383819 | 0.852683 | none |
| test-7 | 25 | 25 | 0.0614547 | 0.66296 | 0.560484 | none |
| test-8 | 25 | 25 | 0.00747908 | 0.0415237 | 0.998276 | none |
| test-9 | 25 | 25 | 0.0338976 | 0.256149 | 0.934388 | none |
| test-10 | 25 | 25 | 0.0128108 | 0.188626 | 0.96442 | none |
| test-11 | 25 | 25 | 0.050366 | 0.644014 | 0.585246 | none |
| test-12 | 24 | 24 | 0.00860067 | 0.0646235 | 0.995824 | none |

Output errors on the training data (pooled RMSE: 0.0390576 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.021324 | 0.41843 | 0.824917 | none |
| 1-2 | 25 | 25 | 0.0142729 | 0.185365 | 0.96564 | none |
| 1-3 | 25 | 25 | 0.0412606 | 0.455318 | 0.792686 | none |
| 1-4 | 25 | 25 | 0.0623965 | 1.25352 | -0.571314 | none |
| 1-5 | 25 | 25 | 0.0273507 | 0.183322 | 0.966393 | none |
| 1-6 | 24 | 24 | 0.0354466 | 0.976962 | 0.0455454 | none |
| 2-1 | 25 | 25 | 0.026876 | 0.284457 | 0.919084 | none |
| 2-2 | 25 | 25 | 0.0225898 | 0.22033 | 0.951455 | none |
| 2-3 | 25 | 25 | 0.00928535 | 0.13524 | 0.98171 | none |
| 2-4 | 25 | 25 | 0.0721902 | 0.559522 | 0.686935 | none |
| 2-5 | 25 | 25 | 0.0479253 | 0.268706 | 0.927797 | none |
| 2-6 | 24 | 24 | 0.043279 | 0.299232 | 0.91046 | none |
| 3-1 | 25 | 25 | 0.0413569 | 0.318678 | 0.898444 | none |
| 3-2 | 25 | 25 | 0.0106991 | 0.0779912 | 0.993917 | none |
| 3-3 | 25 | 25 | 0.0143739 | 0.099689 | 0.990062 | none |
| 3-4 | 25 | 25 | 0.0445363 | 0.445364 | 0.801651 | none |
| 3-5 | 25 | 25 | 0.0561224 | 0.45246 | 0.79528 | none |
| 3-6 | 24 | 24 | 0.0364793 | 0.234765 | 0.944885 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.37, 1.36, 0.992, 0.387, 0.382; rank 5 of 5.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![TurnDeadzone test](plots/TurnDeadzone_test.png)

*Candidate TurnDeadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of TurnDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![TurnDeadzone train](plots/TurnDeadzone_train.png)

*Candidate TurnDeadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of TurnDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate CubicArc

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `x_next = x+Piecewise((Ts*(gf*v_f+bf)*cos(phi), Eq((ga*v_a+ba+ca*v_a**3),0)), ((gf*v_f+bf)*(sin(phi+Ts*(ga*v_a+ba+ca*v_a**3))-sin(phi))/(ga*v_a+ba+ca*v_a**3), True))`
- `y_next = y+Piecewise((Ts*(gf*v_f+bf)*sin(phi), Eq((ga*v_a+ba+ca*v_a**3),0)), ((gf*v_f+bf)*(cos(phi)-cos(phi+Ts*(ga*v_a+ba+ca*v_a**3)))/(ga*v_a+ba+ca*v_a**3), True))`
- `phi_next = phi+Ts*(ga*v_a+ba+ca*v_a**3)`
Complexity: 5 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 140 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `x_next = x + Piecewise((0.20000000000000001*(P1 + P2*v_f)*cos(phi), Eq(P3 + P4*v_a**3 + P5*v_a, 0)), ((P1 + P2*v_f)*(-sin(phi) + sin(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a**3 + 0.20000000000000001*P5*v_a + phi))/(P3 + P4*v_a**3 + P5*v_a), True))`; `y_next = y + Piecewise((0.20000000000000001*(P1 + P2*v_f)*sin(phi), Eq(P3 + P4*v_a**3 + P5*v_a, 0)), ((P1 + P2*v_f)*(cos(phi) - cos(0.20000000000000001*P3 + 0.20000000000000001*P4*v_a**3 + 0.20000000000000001*P5*v_a + phi))/(P3 + P4*v_a**3 + P5*v_a), True))`; `phi_next = 0.20000000000000001*P3 + 0.20000000000000001*P4*v_a**3 + 0.20000000000000001*P5*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0456915 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0587009 | 0.209672 | 0.956038 | none |
| test-2 | 25 | 25 | 0.0152734 | 0.199436 | 0.960225 | none |
| test-3 | 25 | 25 | 0.0562372 | 0.384461 | 0.85219 | none |
| test-4 | 25 | 25 | 0.0270219 | 0.179787 | 0.967677 | none |
| test-5 | 25 | 25 | 0.0373798 | 0.16769 | 0.97188 | none |
| test-6 | 24 | 24 | 0.0787123 | 0.62588 | 0.608274 | none |
| test-7 | 25 | 25 | 0.0556935 | 0.60081 | 0.639028 | none |
| test-8 | 25 | 25 | 0.00912177 | 0.050644 | 0.997435 | none |
| test-9 | 25 | 25 | 0.0447138 | 0.337883 | 0.885835 | none |
| test-10 | 25 | 25 | 0.0125946 | 0.185442 | 0.965611 | none |
| test-11 | 25 | 25 | 0.0675886 | 0.864235 | 0.253099 | none |
| test-12 | 24 | 24 | 0.0077388 | 0.0581477 | 0.996619 | none |

Output errors on the training data (pooled RMSE: 0.0380322 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0218957 | 0.429648 | 0.815402 | none |
| 1-2 | 25 | 25 | 0.0157281 | 0.204264 | 0.958276 | none |
| 1-3 | 25 | 25 | 0.0282855 | 0.312136 | 0.902571 | none |
| 1-4 | 25 | 25 | 0.0706175 | 1.41868 | -1.01264 | none |
| 1-5 | 25 | 25 | 0.0311353 | 0.208689 | 0.956449 | none |
| 1-6 | 24 | 24 | 0.0471919 | 1.30068 | -0.691773 | none |
| 2-1 | 25 | 25 | 0.0311006 | 0.32917 | 0.891647 | none |
| 2-2 | 25 | 25 | 0.0333666 | 0.325441 | 0.894088 | none |
| 2-3 | 25 | 25 | 0.0171516 | 0.249811 | 0.937595 | none |
| 2-4 | 25 | 25 | 0.054979 | 0.426124 | 0.818419 | none |
| 2-5 | 25 | 25 | 0.0701109 | 0.393095 | 0.845476 | none |
| 2-6 | 24 | 24 | 0.0387466 | 0.267896 | 0.928232 | none |
| 3-1 | 25 | 25 | 0.0335846 | 0.258788 | 0.933029 | none |
| 3-2 | 25 | 25 | 0.0129209 | 0.0941865 | 0.991129 | none |
| 3-3 | 25 | 25 | 0.00930332 | 0.0645224 | 0.995837 | none |
| 3-4 | 25 | 25 | 0.0194813 | 0.194813 | 0.962048 | none |
| 3-5 | 25 | 25 | 0.0417529 | 0.336613 | 0.886692 | none |
| 3-6 | 24 | 24 | 0.0319973 | 0.205921 | 0.957597 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.39, 1.36, 0.988, 0.387, 0.292; rank 5 of 5.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![CubicArc test](plots/CubicArc_test.png)

*Candidate CubicArc, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of CubicArc; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![CubicArc train](plots/CubicArc_train.png)

*Candidate CubicArc, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of CubicArc; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate WheelDeadzone

Position in the agent's order: 5. Status: evaluated.
File and expression checks: passed.
- `x_next = x+Piecewise((Ts*(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))+(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/2+bf)*cos(phi), Eq((((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba),0)), ((((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))+(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/2+bf)*(sin(phi+Ts*(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba))-sin(phi))/(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba), True))`
- `y_next = y+Piecewise((Ts*(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))+(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/2+bf)*sin(phi), Eq((((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba),0)), ((((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))+(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/2+bf)*(cos(phi)-cos(phi+Ts*(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba)))/(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba), True))`
- `phi_next = phi+Ts*(((gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0))-(gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)))/ell+ba)`
Complexity: 5 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 628 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 5: `x_next = x + Piecewise((0.20000000000000001*(P1 + P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f))/2 + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f))/2)*cos(phi), Eq(P5 + (-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4, 0)), ((-sin(phi) + sin(0.20000000000000001*P5 + phi + 0.20000000000000001*(-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4))*(P1 + P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f))/2 + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f))/2)/(P5 + (-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4), True))`; `y_next = y + Piecewise((0.20000000000000001*(P1 + P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f))/2 + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f))/2)*sin(phi), Eq(P5 + (-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4, 0)), ((cos(phi) - cos(0.20000000000000001*P5 + phi + 0.20000000000000001*(-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4))*(P1 + P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f))/2 + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f))/2)/(P5 + (-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4), True))`; `phi_next = 0.20000000000000001*P5 + phi + 0.20000000000000001*(-P2*sign(-P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 - v_f)) + P2*sign(P4*v_a/2 + v_f)*Max(0, -P3 + Abs(P4*v_a/2 + v_f)))/P4`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0435268 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0328048 | 0.117175 | 0.98627 | none |
| test-2 | 25 | 25 | 0.00554492 | 0.0724041 | 0.994758 | none |
| test-3 | 25 | 25 | 0.0424746 | 0.290374 | 0.915683 | none |
| test-4 | 25 | 25 | 0.0338094 | 0.224947 | 0.949399 | none |
| test-5 | 25 | 25 | 0.0454421 | 0.203859 | 0.958441 | none |
| test-6 | 24 | 24 | 0.0975703 | 0.77583 | 0.398088 | none |
| test-7 | 25 | 25 | 0.0545855 | 0.588857 | 0.653248 | none |
| test-8 | 25 | 25 | 0.00474978 | 0.0263707 | 0.999305 | none |
| test-9 | 25 | 25 | 0.0403538 | 0.304936 | 0.907014 | none |
| test-10 | 25 | 25 | 0.0201508 | 0.2967 | 0.911969 | none |
| test-11 | 25 | 25 | 0.0474991 | 0.607357 | 0.631118 | none |
| test-12 | 24 | 24 | 0.00581374 | 0.0436832 | 0.998092 | none |

Output errors on the training data (pooled RMSE: 0.0402696 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0435737 | 0.855024 | 0.268934 | none |
| 1-2 | 25 | 25 | 0.00888748 | 0.115423 | 0.986677 | none |
| 1-3 | 25 | 25 | 0.0694672 | 0.766582 | 0.412352 | none |
| 1-4 | 25 | 25 | 0.0603001 | 1.2114 | -0.4675 | none |
| 1-5 | 25 | 25 | 0.0269432 | 0.180591 | 0.967387 | none |
| 1-6 | 24 | 24 | 0.0452781 | 1.24793 | -0.557342 | none |
| 2-1 | 25 | 25 | 0.0247865 | 0.262341 | 0.931177 | none |
| 2-2 | 25 | 25 | 0.0321501 | 0.313576 | 0.90167 | none |
| 2-3 | 25 | 25 | 0.0115525 | 0.168261 | 0.971688 | none |
| 2-4 | 25 | 25 | 0.046798 | 0.362716 | 0.868437 | none |
| 2-5 | 25 | 25 | 0.077878 | 0.436644 | 0.809342 | none |
| 2-6 | 24 | 24 | 0.0395837 | 0.273683 | 0.925098 | none |
| 3-1 | 25 | 25 | 0.0289449 | 0.223036 | 0.950255 | none |
| 3-2 | 25 | 25 | 0.0198014 | 0.144342 | 0.979165 | none |
| 3-3 | 25 | 25 | 0.0122262 | 0.084794 | 0.99281 | none |
| 3-4 | 25 | 25 | 0.00847428 | 0.0847428 | 0.992819 | none |
| 3-5 | 25 | 25 | 0.0453291 | 0.365444 | 0.86645 | none |
| 3-6 | 24 | 24 | 0.0291348 | 0.187499 | 0.964844 | none |

- Failed computation (sensitivity rank test): NameError: name 'DiracDelta' is not defined
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![WheelDeadzone test](plots/WheelDeadzone_test.png)

*Candidate WheelDeadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of WheelDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![WheelDeadzone train](plots/WheelDeadzone_train.png)

*Candidate WheelDeadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of WheelDeadzone; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
