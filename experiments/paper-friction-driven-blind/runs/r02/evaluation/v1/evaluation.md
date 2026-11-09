# Evaluation report: task task-jdhj

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This report contains results on sealed data and is not shown to the agent.

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
| failed numerically on test data | 0 |
| eligible for ranking | 3 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 3 among 3 evaluated candidates; groups: HarmonicFriction; BoundedStiction; QuinticOscillator. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: HarmonicFriction. The agent's reason: Recommended for its smooth closed form, position-dependent dissipative term and best pre-refit held-out validation output error among these delivered structures (`0.0763671` in recorded `y` units). After all-data refitting its training and reused-validation free-running errors are `0.0344979` and `0.0718753` in recorded `y` units. These final figures are no longer independent holdout evidence. BoundedStiction offers exact stopping behavior; QuinticOscillator provides a polynomial restoring alternative. No test data were accessed.
- Test score S of the recommended candidate (practical selection): 0.0321998 not supplied; eligible: True; rank in the oracle-based selection: 1.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 3 eligible of 3 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (449 scored samples), test-2 (299 scored samples), test-3 (140 scored samples), test-4 (90 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (not supplied) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | HarmonicFriction | 0.0321998 | none | none |
| 2 | BoundedStiction | 0.0367956 | none | none |
| 3 | QuinticOscillator | 0.0452749 | none | none |

## Candidates

### Candidate HarmonicFriction

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `dy = x1`
- `dx1 = b + k*sin(y) + c*x1 + g*x2 + l*(cos(y)-1) + m*sin(2*y) - (f + h*sin(y) + j*(cos(y)-1))*tanh(x1/s)`
Complexity: 10 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 45 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `dy = x1`; `dx1 = P1 + P2*x1 + P3*x2 + P4*sin(y) + P5*(cos(y) - 1) + P6*sin(2*y) - (P7 + P8*sin(y) + P9*(cos(y) - 1))*tanh(x1/P10)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0321998 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 449 | 449 | 0.0342954 | 0.0908273 | 0.99175 | none |
| test-2 | 299 | 299 | 0.0330809 | 0.0535257 | 0.997135 | none |
| test-3 | 140 | 140 | 0.0229497 | 0.433549 | 0.812035 | none |
| test-4 | 90 | 90 | 0.0307265 | 0.058191 | 0.996614 | none |

Output errors on the training data (pooled RMSE: 0.0344979 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0240577 | 0.0938003 | 0.991201 | none |
| 2 | 449 | 449 | 0.023675 | 0.0355238 | 0.998738 | none |
| 3 | 299 | 299 | 0.0405473 | 0.0858556 | 0.992629 | none |
| 4 | 299 | 299 | 0.0373567 | 0.0455828 | 0.997922 | none |
| 5 | 441 | 441 | 0.0308257 | 0.0805368 | 0.993514 | none |
| 6 | 441 | 441 | 0.0177179 | 0.0388175 | 0.998493 | none |
| 7 | 441 | 441 | 0.0418787 | 0.0807159 | 0.993485 | none |
| 8 | 140 | 140 | 0.0856258 | 0.521403 | 0.728139 | none |
| 9 | 140 | 140 | 0.0298695 | 0.136585 | 0.981344 | none |
| 10 | 140 | 140 | 0.0301241 | 0.612666 | 0.624641 | none |
| 11 | 90 | 90 | 0.00637048 | 0.0387068 | 0.998502 | none |
| 12 | 90 | 90 | 0.0152617 | 2.9912 | -7.94728 | none |
| 13 | 90 | 90 | 0.0367833 | 0.0677051 | 0.995416 | none |

Output errors on the validation data (pooled RMSE: 0.0718753 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0976215 | 0.178542 | 0.968123 | none |
| 2 | 299 | 299 | 0.0355753 | 0.0636271 | 0.995952 | none |
| 3 | 441 | 441 | 0.0580303 | 0.154394 | 0.976162 | none |

Sensitivity rank test (diagnostic; never excludes): targets dx1 on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.56, 1.36, 1.21, 1.01, 0.949, 0.861, 0.794, 0.74, 0.481, 0.418; rank 10 of 10.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![HarmonicFriction test](plots/HarmonicFriction_test.png)

*Candidate HarmonicFriction, test data (sealed), trajectories test-1, test-2, test-3, test-4. Upper axes: measured output y (not supplied) and model output of HarmonicFriction; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 449; test-2: 1 to 299; test-3: 1 to 140; test-4: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![HarmonicFriction train](plots/HarmonicFriction_train.png)

*Candidate HarmonicFriction, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output y (not supplied) and model output of HarmonicFriction; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![HarmonicFriction val](plots/HarmonicFriction_val.png)

*Candidate HarmonicFriction, validation data, trajectories 1, 2, 3. Upper axes: measured output y (not supplied) and model output of HarmonicFriction; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate BoundedStiction

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `dy = x1`
- `dx1 = (b + k*sin(y) + c*x1 + g*x2 + l*(cos(y)-1) + m*sin(2*y)) - Min((f + h*sin(y) + j*(cos(y)-1)), Max(-(f + h*sin(y) + j*(cos(y)-1)), (b + k*sin(y) + c*x1 + g*x2 + l*(cos(y)-1) + m*sin(2*y)) + x1/tau))`
Complexity: 10 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 86 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `dy = x1`; `dx1 = P1 + P5*x1 + P6*x2 + P7*sin(y) + P8*(cos(y) - 1) + P9*sin(2*y) - Min(P2 + P3*sin(y) + P4*(cos(y) - 1), Max(-P2 - P3*sin(y) - P4*(cos(y) - 1), P1 + P5*x1 + P6*x2 + P7*sin(y) + P8*(cos(y) - 1) + P9*sin(2*y) + x1/P10))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0367956 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 449 | 449 | 0.0375002 | 0.0993147 | 0.990137 | none |
| test-2 | 299 | 299 | 0.0400346 | 0.0647769 | 0.995804 | none |
| test-3 | 140 | 140 | 0.0314253 | 0.593664 | 0.647562 | none |
| test-4 | 90 | 90 | 0.0289119 | 0.0547545 | 0.997002 | none |

Output errors on the training data (pooled RMSE: 0.0326336 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0212025 | 0.0826682 | 0.993166 | none |
| 2 | 449 | 449 | 0.0243153 | 0.0364846 | 0.998669 | none |
| 3 | 299 | 299 | 0.0378943 | 0.0802382 | 0.993562 | none |
| 4 | 299 | 299 | 0.0414848 | 0.0506199 | 0.997438 | none |
| 5 | 441 | 441 | 0.0193334 | 0.0505115 | 0.997449 | none |
| 6 | 441 | 441 | 0.0124082 | 0.0271847 | 0.999261 | none |
| 7 | 441 | 441 | 0.0362133 | 0.0697966 | 0.995128 | none |
| 8 | 140 | 140 | 0.0930796 | 0.566791 | 0.678748 | none |
| 9 | 140 | 140 | 0.0144444 | 0.0660504 | 0.995637 | none |
| 10 | 140 | 140 | 0.0203731 | 0.414351 | 0.828314 | none |
| 11 | 90 | 90 | 0.0324173 | 0.196966 | 0.961204 | none |
| 12 | 90 | 90 | 0.00142634 | 0.279552 | 0.92185 | none |
| 13 | 90 | 90 | 0.0364523 | 0.0670958 | 0.995498 | none |

Output errors on the validation data (pooled RMSE: 0.0762124 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.104093 | 0.190379 | 0.963756 | none |
| 2 | 299 | 299 | 0.0394714 | 0.0705954 | 0.995016 | none |
| 3 | 441 | 441 | 0.0597644 | 0.159008 | 0.974716 | none |

Sensitivity rank test (diagnostic; never excludes): targets dx1 on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.57, 1.36, 1.26, 1, 0.921, 0.859, 0.759, 0.706, 0.514, 0.412; rank 10 of 10.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![BoundedStiction test](plots/BoundedStiction_test.png)

*Candidate BoundedStiction, test data (sealed), trajectories test-1, test-2, test-3, test-4. Upper axes: measured output y (not supplied) and model output of BoundedStiction; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 449; test-2: 1 to 299; test-3: 1 to 140; test-4: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![BoundedStiction train](plots/BoundedStiction_train.png)

*Candidate BoundedStiction, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output y (not supplied) and model output of BoundedStiction; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![BoundedStiction val](plots/BoundedStiction_val.png)

*Candidate BoundedStiction, validation data, trajectories 1, 2, 3. Upper axes: measured output y (not supplied) and model output of BoundedStiction; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate QuinticOscillator

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `dy = x1`
- `dx1 = b + k*y + a3*y**3 + a5*y**5 + c*x1 + g*x2 - f*tanh(x1/s)`
Complexity: 8 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 31 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `dy = x1`; `dx1 = P1 + P2*y**3 + P3*y**5 + P4*x1 + P5*x2 + P6*y - P7*tanh(x1/P8)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0452749 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 449 | 449 | 0.0359097 | 0.0951025 | 0.990956 | none |
| test-2 | 299 | 299 | 0.0646986 | 0.104684 | 0.989041 | none |
| test-3 | 140 | 140 | 0.00577553 | 0.109107 | 0.988096 | none |
| test-4 | 90 | 90 | 0.0433949 | 0.0821829 | 0.993246 | none |

Output errors on the training data (pooled RMSE: 0.0528176 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0357401 | 0.13935 | 0.980582 | none |
| 2 | 449 | 449 | 0.0356987 | 0.0535651 | 0.997131 | none |
| 3 | 299 | 299 | 0.0728377 | 0.154228 | 0.976214 | none |
| 4 | 299 | 299 | 0.0497651 | 0.0607236 | 0.996313 | none |
| 5 | 441 | 441 | 0.0298763 | 0.0780566 | 0.993907 | none |
| 6 | 441 | 441 | 0.0607179 | 0.133025 | 0.982304 | none |
| 7 | 441 | 441 | 0.0736735 | 0.141996 | 0.979837 | none |
| 8 | 140 | 140 | 0.0958996 | 0.583963 | 0.658987 | none |
| 9 | 140 | 140 | 0.0367552 | 0.168072 | 0.971752 | none |
| 10 | 140 | 140 | 0.0177352 | 0.3607 | 0.869896 | none |
| 11 | 90 | 90 | 0.0229115 | 0.13921 | 0.980621 | none |
| 12 | 90 | 90 | 0.0108209 | 2.12083 | -3.49792 | none |
| 13 | 90 | 90 | 0.0600851 | 0.110596 | 0.987769 | none |

Output errors on the validation data (pooled RMSE: 0.0777601 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.100824 | 0.1844 | 0.965997 | none |
| 2 | 299 | 299 | 0.0629318 | 0.112555 | 0.987331 | none |
| 3 | 441 | 441 | 0.0571618 | 0.152084 | 0.976871 | none |

Sensitivity rank test (diagnostic; never excludes): targets dx1 on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.64, 1.38, 1.04, 0.989, 0.867, 0.59, 0.47, 0.128; rank 8 of 8.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![QuinticOscillator test](plots/QuinticOscillator_test.png)

*Candidate QuinticOscillator, test data (sealed), trajectories test-1, test-2, test-3, test-4. Upper axes: measured output y (not supplied) and model output of QuinticOscillator; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 449; test-2: 1 to 299; test-3: 1 to 140; test-4: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![QuinticOscillator train](plots/QuinticOscillator_train.png)

*Candidate QuinticOscillator, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output y (not supplied) and model output of QuinticOscillator; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![QuinticOscillator val](plots/QuinticOscillator_val.png)

*Candidate QuinticOscillator, validation data, trajectories 1, 2, 3. Upper axes: measured output y (not supplied) and model output of QuinticOscillator; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*
