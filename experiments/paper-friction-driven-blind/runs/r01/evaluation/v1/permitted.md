# Evaluation results permitted to the agent: task task-jdhj

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This view contains no result derived from sealed data.

Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])).
Error measures: for one trajectory with scoring interval I of N samples, measured output y[k] (y, not supplied) and model output ŷ[k], SSE = Σ_(k∈I) (ŷ[k] − y[k])²; RMSE = sqrt(SSE/N), in not supplied; NRMSE = RMSE/σ, with μ and σ the mean and the population standard deviation of y on I; R² = 1 − SSE / Σ_(k∈I) (y[k] − μ)²; NRMSE and R² are not applicable when σ = 0. The pooled RMSE over several trajectories is S = sqrt(ΣSSE / ΣN); on the test data it is the ranking score.
Numerical failure limits: y in [-1000, 1000] not supplied; x1 in [-1000, 1000] not supplied; evaluation time limit 60 s per candidate and data group; symbolic time limit 10 s per verification.
Discontinuous expressions: expressions with jumps (Piecewise, sign) are evaluated pointwise at the sample instants and Runge-Kutta stages; no event detection or step refinement is applied at a jump.
Harness version 0.1.0.dev0; NumPy 2.5.1; SymPy 1.14.0.

## Pool

| category | count |
|---|---|
| candidates proposed | 3 |
| accepted by the file and expression checks | 3 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 3 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |

Note: the categories overlap; the counts need not sum to the pool size.

Distinct structures: 3 among 3 evaluated candidates; groups: QuinticDamping; TrigDamping; StaticBlend. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: QuinticDamping. The agent's reason: Recommend QuinticDamping: its training-only fit gave validation RMSE 0.0712333 Y and four-fold trajectory-grouped diagnostic RMSE 0.0543695 Y, compared with 0.0728230 Y / 0.0557991 Y for TrigDamping and 0.0759100 Y / 0.0557450 Y for StaticBlend. Y is the unknown output unit. These small differences are not statistically decisive; it is recommended for its consistent held-trajectory output accuracy, not a proven physical spring interpretation. All three delivered candidates were subsequently refitted on both supplied files, so their final validation-file errors are in-sample. Grouped diagnostics use the final coefficients as numerical warm starts and reuse structure/smoothing choices screened on these files; they are not a completely untouched assessment. Quintic extrapolation can be stiff and have extra equilibria; the trigonometric model is the simpler bounded-force alternative.

## Candidates

### Candidate QuinticDamping

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `dy = x1`
- `dx1 = bias - linearRest*y + quadraticForce*y**2 + cubicRest*y**3 - quinticRest*y**5 - visc*exp(Min(Max(-dampSlope*y, -expCap), expCap))*x1 + gain*x2 - fric*tanh(x1/velScale)`
Complexity: 9 fitted, 2 fixed and 0 tied parameters; 0 non-integer numeric literals; 50 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `dy = x1`; `dx1 = P1 + P2*y**3 + P3*x2 + P4*y**2 - P5*tanh(4.9999999999999997*x1) - P6*y - P7*y**5 - P8*x1*exp(Min(40.0, Max(-40.0, -P9*y)))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0429612 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.032384 | 0.126264 | 0.984057 | none |
| 2 | 449 | 449 | 0.0331266 | 0.0497058 | 0.997529 | none |
| 3 | 299 | 299 | 0.0596455 | 0.126295 | 0.98405 | none |
| 4 | 299 | 299 | 0.0449515 | 0.0548501 | 0.996991 | none |
| 5 | 441 | 441 | 0.0417395 | 0.109051 | 0.988108 | none |
| 6 | 441 | 441 | 0.0245245 | 0.0537298 | 0.997113 | none |
| 7 | 441 | 441 | 0.0524876 | 0.101163 | 0.989766 | none |
| 8 | 140 | 140 | 0.0669098 | 0.407435 | 0.833997 | none |
| 9 | 140 | 140 | 0.0476592 | 0.217934 | 0.952505 | none |
| 10 | 140 | 140 | 0.0456777 | 0.928997 | 0.136964 | none |
| 11 | 90 | 90 | 0.0210936 | 0.128164 | 0.983574 | none |
| 12 | 90 | 90 | 0.0278766 | 5.46363 | -28.8513 | none |
| 13 | 90 | 90 | 0.052666 | 0.0969396 | 0.990603 | none |

Output errors on the validation data (pooled RMSE: 0.0687207 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0883572 | 0.161599 | 0.973886 | none |
| 2 | 299 | 299 | 0.0543619 | 0.0972274 | 0.990547 | none |
| 3 | 441 | 441 | 0.0527291 | 0.14029 | 0.980319 | none |

Sensitivity rank test (diagnostic; never excludes): targets dx1 on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.67, 1.39, 1.23, 0.946, 0.865, 0.727, 0.584, 0.489, 0.127; rank 9 of 9.

![QuinticDamping train](plots/QuinticDamping_train.png)

*Candidate QuinticDamping, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output y (not supplied) and model output of QuinticDamping; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![QuinticDamping val](plots/QuinticDamping_val.png)

*Candidate QuinticDamping, validation data, trajectories 1, 2, 3. Upper axes: measured output y (not supplied) and model output of QuinticDamping; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate TrigDamping

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `dy = x1`
- `dx1 = bias - rest*sin(freq*y) + even*(cos(freq*y) - 1) + gain*x2 - visc*exp(Min(Max(-dampSlope*y, -expCap), expCap))*x1 - fric*tanh(x1/velScale)`
Complexity: 8 fitted, 2 fixed and 0 tied parameters; 0 non-integer numeric literals; 45 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `dy = x1`; `dx1 = P1 + P2*(cos(P3*y) - 1) + P4*x2 - P5*tanh(4.9999999999999997*x1) - P6*sin(P3*y) - P7*x1*exp(Min(40.0, Max(-40.0, -P8*y)))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0436178 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0340174 | 0.132633 | 0.982408 | none |
| 2 | 449 | 449 | 0.0351178 | 0.0526935 | 0.997223 | none |
| 3 | 299 | 299 | 0.0590222 | 0.124975 | 0.984381 | none |
| 4 | 299 | 299 | 0.0477849 | 0.0583074 | 0.9966 | none |
| 5 | 441 | 441 | 0.0402643 | 0.105197 | 0.988934 | none |
| 6 | 441 | 441 | 0.0261498 | 0.0572907 | 0.996718 | none |
| 7 | 441 | 441 | 0.0535224 | 0.103158 | 0.989359 | none |
| 8 | 140 | 140 | 0.0669727 | 0.407818 | 0.833685 | none |
| 9 | 140 | 140 | 0.0471055 | 0.215402 | 0.953602 | none |
| 10 | 140 | 140 | 0.0488318 | 0.993145 | 0.0136631 | none |
| 11 | 90 | 90 | 0.0191945 | 0.116625 | 0.986399 | none |
| 12 | 90 | 90 | 0.0289956 | 5.68293 | -31.2957 | none |
| 13 | 90 | 90 | 0.0491232 | 0.0904186 | 0.991824 | none |

Output errors on the validation data (pooled RMSE: 0.0694111 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0888143 | 0.162435 | 0.973615 | none |
| 2 | 299 | 299 | 0.0548979 | 0.0981861 | 0.990359 | none |
| 3 | 441 | 441 | 0.0539937 | 0.143655 | 0.979363 | none |

Sensitivity rank test (diagnostic; never excludes): targets dx1 on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.44, 1.3, 1.21, 0.971, 0.83, 0.746, 0.605, 0.485; rank 8 of 8.

![TrigDamping train](plots/TrigDamping_train.png)

*Candidate TrigDamping, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output y (not supplied) and model output of TrigDamping; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![TrigDamping val](plots/TrigDamping_val.png)

*Candidate TrigDamping, validation data, trajectories 1, 2, 3. Upper axes: measured output y (not supplied) and model output of TrigDamping; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate StaticBlend

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `dy = x1`
- `dx1 = (1 - exp(-(x1/gateSpeed)**2))*(bias - rest*sin(freq*y) + even*(cos(freq*y) - 1) + gain*x2 - visc*exp(Min(Max(-dampSlope*y, -expCap), expCap))*x1 - fric*tanh(x1/velScale)) + exp(-(x1/gateSpeed)**2)*(((bias - rest*sin(freq*y) + even*(cos(freq*y) - 1) + gain*x2) - staticForce + sqrt(((bias - rest*sin(freq*y) + even*(cos(freq*y) - 1) + gain*x2) - staticForce)**2 + softWidth**2))/2 - (-(bias - rest*sin(freq*y) + even*(cos(freq*y) - 1) + gain*x2) - staticForce + sqrt((-(bias - rest*sin(freq*y) + even*(cos(freq*y) - 1) + gain*x2) - staticForce)**2 + softWidth**2))/2 - stickRate*x1)`
Complexity: 11 fitted, 3 fixed and 0 tied parameters; 0 non-integer numeric literals; 163 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `dy = x1`; `dx1 = (1 - exp(-x1**2/P1**2))*(P2 + P3*(cos(P4*y) - 1) + P5*x2 - P6*tanh(x1/P7) - P8*sin(P4*y) - P9*x1*exp(Min(40.0, Max(-40.0, -P10*y)))) + (P2 + P3*(cos(P4*y) - 1) + P5*x2 - P8*sin(P4*y) - 100.0*x1 - sqrt((-P11 - P2 - P3*(cos(P4*y) - 1) - P5*x2 + P8*sin(P4*y))**2 + 0.010000000000000001)/2 + sqrt((-P11 + P2 + P3*(cos(P4*y) - 1) + P5*x2 - P8*sin(P4*y))**2 + 0.010000000000000001)/2)*exp(-x1**2/P1**2)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0388289 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0218946 | 0.0853664 | 0.992713 | none |
| 2 | 449 | 449 | 0.0314836 | 0.0472404 | 0.997768 | none |
| 3 | 299 | 299 | 0.0605904 | 0.128295 | 0.98354 | none |
| 4 | 299 | 299 | 0.0481008 | 0.0586928 | 0.996555 | none |
| 5 | 441 | 441 | 0.0304493 | 0.0795535 | 0.993671 | none |
| 6 | 441 | 441 | 0.0229235 | 0.0502223 | 0.997478 | none |
| 7 | 441 | 441 | 0.0499649 | 0.0963011 | 0.990726 | none |
| 8 | 140 | 140 | 0.069118 | 0.420881 | 0.822859 | none |
| 9 | 140 | 140 | 0.0245453 | 0.11224 | 0.987402 | none |
| 10 | 140 | 140 | 0.0273984 | 0.557231 | 0.689494 | none |
| 11 | 90 | 90 | 0.0134158 | 0.0815138 | 0.993355 | none |
| 12 | 90 | 90 | 0.00216526 | 0.424376 | 0.819905 | none |
| 13 | 90 | 90 | 0.0499156 | 0.0918771 | 0.991559 | none |

Output errors on the validation data (pooled RMSE: 0.0687876 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0882961 | 0.161487 | 0.973922 | none |
| 2 | 299 | 299 | 0.0528315 | 0.0944902 | 0.991072 | none |
| 3 | 441 | 441 | 0.0541055 | 0.143952 | 0.979278 | none |

Sensitivity rank test (diagnostic; never excludes): targets dx1 on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.49, 1.32, 1.29, 1.21, 0.994, 0.957, 0.817, 0.722, 0.598, 0.549, 0.427; rank 11 of 11.

![StaticBlend train](plots/StaticBlend_train.png)

*Candidate StaticBlend, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output y (not supplied) and model output of StaticBlend; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![StaticBlend val](plots/StaticBlend_val.png)

*Candidate StaticBlend, validation data, trajectories 1, 2, 3. Upper axes: measured output y (not supplied) and model output of StaticBlend; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*
