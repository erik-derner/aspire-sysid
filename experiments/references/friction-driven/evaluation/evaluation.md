# Evaluation report: task friction-driven

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This report contains results on sealed data and is not shown to the agent.

Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])).
Error measures: for one trajectory with scoring interval I of N samples, measured output y[k] (theta, rad) and model output ŷ[k], SSE = Σ_(k∈I) (ŷ[k] − y[k])²; RMSE = sqrt(SSE/N), in rad; NRMSE = RMSE/σ, with μ and σ the mean and the population standard deviation of y on I; R² = 1 − SSE / Σ_(k∈I) (y[k] − μ)²; NRMSE and R² are not applicable when σ = 0. The pooled RMSE over several trajectories is S = sqrt(ΣSSE / ΣN); on the test data it is the ranking score.
Numerical failure limits: theta in [-1000, 1000] rad; omega in [-1000, 1000] rad/s; evaluation time limit 60 s per candidate and data group; symbolic time limit 10 s per verification.
Discontinuous expressions: expressions with jumps (Piecewise, sign) are evaluated pointwise at the sample instants and Runge-Kutta stages; no event detection or step refinement is applied at a jump.
Harness version 0.1.0.dev0; NumPy 2.5.1; SymPy 1.14.0.

## Pool

| category | count |
|---|---|
| candidates proposed | 3 |
| accepted by the file and expression checks | 3 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 3 |
| excluded by physical requirements | 2 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 1 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 3 among 3 evaluated candidates; groups: ReferencePhysical; ReferenceSindy; ReferenceSindyThreshold. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

The agent recommends no candidate. Its reason: Reference models estimated without the agent; none is recommended.
- Harness note: the agent recommends no candidate.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 1 eligible of 3 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (449 scored samples), test-2 (299 scored samples), test-3 (140 scored samples), test-4 (90 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (rad) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | ReferencePhysical | 0.0402002 | none | none |

## Candidates

### Candidate ReferencePhysical

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `dtheta = omega`
- `domega = -a*sin(theta) - b*omega - c*tanh(s*omega) + k*u`
Complexity: 4 fitted, 1 fixed and 0 tied parameters; 0 non-integer numeric literals; 21 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `dtheta = omega`; `domega = P1*u - P2*sin(theta) - P3*omega - P4*tanh(10.0*omega)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | equation | proof | satisfied | evaluation of a constant | the quantity is identically zero on the domain |
| R2 | inequality | proof | satisfied | interval arithmetic (branch and bound) | verified enclosures on 3 sub-box(es) covering the domain do not exceed the tolerance 0.0 |
| R3 | monotonicity | proof | satisfied | evaluation of a constant | the quantity reduces to the constant -28.119833426953274, which does not exceed the tolerance 0.0 |

Output errors on the test data (sealed) (pooled RMSE: 0.0402002 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 449 | 449 | 0.0317252 | 0.0840204 | 0.992941 | none |
| test-2 | 299 | 299 | 0.0585591 | 0.0947498 | 0.991022 | none |
| test-3 | 140 | 140 | 0.0157261 | 0.297087 | 0.91174 | none |
| test-4 | 90 | 90 | 0.0276174 | 0.0523029 | 0.997264 | none |

Output errors on the training data (pooled RMSE: 0.0655649 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0472422 | 0.184196 | 0.966072 | none |
| 2 | 449 | 449 | 0.0600099 | 0.0900436 | 0.991892 | none |
| 3 | 299 | 299 | 0.0796176 | 0.168584 | 0.971579 | none |
| 4 | 299 | 299 | 0.0630956 | 0.0769896 | 0.994073 | none |
| 5 | 441 | 441 | 0.0192482 | 0.050289 | 0.997471 | none |
| 6 | 441 | 441 | 0.0309553 | 0.067819 | 0.995401 | none |
| 7 | 441 | 441 | 0.120478 | 0.232206 | 0.94608 | none |
| 8 | 140 | 140 | 0.109118 | 0.664455 | 0.558499 | none |
| 9 | 140 | 140 | 0.0509757 | 0.233099 | 0.945665 | none |
| 10 | 140 | 140 | 0.0164086 | 0.33372 | 0.888631 | none |
| 11 | 90 | 90 | 0.036853 | 0.223917 | 0.949861 | none |
| 12 | 90 | 90 | 0.00747341 | 1.46474 | -1.14546 | none |
| 13 | 90 | 90 | 0.0467718 | 0.0860904 | 0.992588 | none |

Output errors on the validation data (pooled RMSE: 0.0864818 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.116714 | 0.213461 | 0.954434 | none |
| 2 | 299 | 299 | 0.0763963 | 0.136636 | 0.981331 | none |
| 3 | 441 | 441 | 0.0483564 | 0.128656 | 0.983448 | none |

Sensitivity rank test (diagnostic; never excludes): targets domega on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.41, 1.08, 0.774, 0.517; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePhysical test](plots/ReferencePhysical_test.png)

*Candidate ReferencePhysical, test data (sealed), trajectories test-1, test-2, test-3, test-4. Upper axes: measured output theta (rad) and model output of ReferencePhysical; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 449; test-2: 1 to 299; test-3: 1 to 140; test-4: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![ReferencePhysical train](plots/ReferencePhysical_train.png)

*Candidate ReferencePhysical, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output theta (rad) and model output of ReferencePhysical; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![ReferencePhysical val](plots/ReferencePhysical_val.png)

*Candidate ReferencePhysical, validation data, trajectories 1, 2, 3. Upper axes: measured output theta (rad) and model output of ReferencePhysical; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferenceSindy

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `dtheta = omega`
- `domega = c_omega_1 + c_omega_2*theta + c_omega_3*omega + c_omega_4*u + c_omega_5*theta**2 + c_omega_6*theta*omega + c_omega_7*theta*u + c_omega_8*u**2`
Complexity: 8 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 30 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `dtheta = omega`; `domega = P1 + P2*theta + P3*omega + P4*u + P5*theta**2 + P6*u**2 + P7*omega*theta + P8*theta*u`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | equation | proof | satisfied | evaluation of a constant | the quantity is identically zero on the domain |
| R2 | inequality | counterexample | violated | interval arithmetic (branch and bound) | on a sub-box around {'theta': 0.006135923151542565} the verified lower bound 0.001617129560350975 of the quantity exceeds the tolerance 0.0 Excludes the candidate. |
| R3 | monotonicity | proof | satisfied | interval arithmetic (branch and bound) | verified enclosures on 1 sub-box(es) covering the domain do not exceed the tolerance 0.0 |

Output errors on the test data (sealed) (pooled RMSE: 0.266769 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 449 | 449 | 0.266996 | 0.707107 | 0.5 | none |
| test-2 | 299 | 299 | 0.335967 | 0.543602 | 0.704497 | none |
| test-3 | 140 | 140 | 0.0793751 | 1.4995 | -1.2485 | none |
| test-4 | 90 | 90 | 0.181387 | 0.343518 | 0.881996 | none |

Output errors on the training data (pooled RMSE: 0.195745 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.210894 | 0.82227 | 0.323872 | none |
| 2 | 449 | 449 | 0.283346 | 0.425155 | 0.819243 | none |
| 3 | 299 | 299 | 0.121219 | 0.256672 | 0.934119 | none |
| 4 | 299 | 299 | 0.24092 | 0.293972 | 0.91358 | none |
| 5 | 441 | 441 | 0.10677 | 0.278953 | 0.922185 | none |
| 6 | 441 | 441 | 0.179097 | 0.392377 | 0.84604 | none |
| 7 | 441 | 441 | 0.230042 | 0.443376 | 0.803417 | none |
| 8 | 140 | 140 | 0.127758 | 0.777956 | 0.394785 | none |
| 9 | 140 | 140 | 0.152154 | 0.695762 | 0.515915 | none |
| 10 | 140 | 140 | 0.135136 | 2.7484 | -6.55372 | none |
| 11 | 90 | 90 | 0.134122 | 0.81492 | 0.335906 | none |
| 12 | 90 | 90 | 0.081552 | 15.9836 | -254.477 | none |
| 13 | 90 | 90 | 0.207504 | 0.381941 | 0.854121 | none |

Output errors on the validation data (pooled RMSE: 0.270429 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.283369 | 0.51826 | 0.731407 | none |
| 2 | 299 | 299 | 0.387683 | 0.693379 | 0.519225 | none |
| 3 | 441 | 441 | 0.116263 | 0.309326 | 0.904317 | none |

Sensitivity rank test (diagnostic; never excludes): targets domega on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.27, 1.13, 1.04, 0.836, 0.792, 0.662, 0.645; rank 8 of 8.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: False (demonstrated violation of mandatory requirement(s) R2).

![ReferenceSindy test](plots/ReferenceSindy_test.png)

*Candidate ReferenceSindy, test data (sealed), trajectories test-1, test-2, test-3, test-4. Upper axes: measured output theta (rad) and model output of ReferenceSindy; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 449; test-2: 1 to 299; test-3: 1 to 140; test-4: 1 to 90 (0-based sample indices). No numerical failure occurred. The candidate is excluded from ranking by the demonstrated violation of R2.*

![ReferenceSindy train](plots/ReferenceSindy_train.png)

*Candidate ReferenceSindy, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output theta (rad) and model output of ReferenceSindy; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred. The candidate is excluded from ranking by the demonstrated violation of R2.*

![ReferenceSindy val](plots/ReferenceSindy_val.png)

*Candidate ReferenceSindy, validation data, trajectories 1, 2, 3. Upper axes: measured output theta (rad) and model output of ReferenceSindy; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred. The candidate is excluded from ranking by the demonstrated violation of R2.*

### Candidate ReferenceSindyThreshold

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `dtheta = omega`
- `domega = c_omega_1 + c_omega_2*theta + c_omega_3*omega + c_omega_4*u + c_omega_5*theta**2 + c_omega_6*theta*omega + c_omega_7*theta*u + c_omega_8*omega**2 + c_omega_9*omega*u + c_omega_10*u**2`
Complexity: 10 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 39 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `dtheta = omega`; `domega = P1 + P10*omega*u + P2*u**2 + P3*theta + P4*omega + P5*u + P6*theta**2 + P7*omega**2 + P8*omega*theta + P9*theta*u`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | equation | proof | satisfied | evaluation of a constant | the quantity is identically zero on the domain |
| R2 | inequality | counterexample | violated | interval arithmetic (branch and bound) | on a sub-box around {'theta': 0.01227184630308513} the verified lower bound 0.001211549113276446 of the quantity exceeds the tolerance 0.0 Excludes the candidate. |
| R3 | monotonicity | proof | satisfied | interval arithmetic (branch and bound) | verified enclosures on 1 sub-box(es) covering the domain do not exceed the tolerance 0.0 |

Output errors on the test data (sealed) (pooled RMSE: 0.269178 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 449 | 449 | 0.268829 | 0.711962 | 0.49311 | none |
| test-2 | 299 | 299 | 0.340215 | 0.550476 | 0.696977 | none |
| test-3 | 140 | 140 | 0.0805184 | 1.5211 | -1.31374 | none |
| test-4 | 90 | 90 | 0.179437 | 0.339825 | 0.884519 | none |

Output errors on the training data (pooled RMSE: 0.193434 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.210495 | 0.820713 | 0.32643 | none |
| 2 | 449 | 449 | 0.275636 | 0.413586 | 0.828947 | none |
| 3 | 299 | 299 | 0.119269 | 0.252543 | 0.936222 | none |
| 4 | 299 | 299 | 0.234313 | 0.285909 | 0.918256 | none |
| 5 | 441 | 441 | 0.111993 | 0.292598 | 0.914386 | none |
| 6 | 441 | 441 | 0.185569 | 0.406557 | 0.834711 | none |
| 7 | 441 | 441 | 0.222926 | 0.429661 | 0.815391 | none |
| 8 | 140 | 140 | 0.126869 | 0.772546 | 0.403172 | none |
| 9 | 140 | 140 | 0.148772 | 0.680297 | 0.537196 | none |
| 10 | 140 | 140 | 0.136882 | 2.78391 | -6.75018 | none |
| 11 | 90 | 90 | 0.130796 | 0.79471 | 0.368436 | none |
| 12 | 90 | 90 | 0.0847778 | 16.6159 | -275.087 | none |
| 13 | 90 | 90 | 0.206136 | 0.379424 | 0.856037 | none |

Output errors on the validation data (pooled RMSE: 0.269004 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.288699 | 0.528009 | 0.721206 | none |
| 2 | 299 | 299 | 0.379296 | 0.678378 | 0.539803 | none |
| 3 | 441 | 441 | 0.112696 | 0.299838 | 0.910097 | none |

Sensitivity rank test (diagnostic; never excludes): targets domega on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.58, 1.3, 1.14, 1.06, 0.888, 0.867, 0.828, 0.674, 0.621, 0.541; rank 10 of 10.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: False (demonstrated violation of mandatory requirement(s) R2).

![ReferenceSindyThreshold test](plots/ReferenceSindyThreshold_test.png)

*Candidate ReferenceSindyThreshold, test data (sealed), trajectories test-1, test-2, test-3, test-4. Upper axes: measured output theta (rad) and model output of ReferenceSindyThreshold; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 449; test-2: 1 to 299; test-3: 1 to 140; test-4: 1 to 90 (0-based sample indices). No numerical failure occurred. The candidate is excluded from ranking by the demonstrated violation of R2.*

![ReferenceSindyThreshold train](plots/ReferenceSindyThreshold_train.png)

*Candidate ReferenceSindyThreshold, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output theta (rad) and model output of ReferenceSindyThreshold; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred. The candidate is excluded from ranking by the demonstrated violation of R2.*

![ReferenceSindyThreshold val](plots/ReferenceSindyThreshold_val.png)

*Candidate ReferenceSindyThreshold, validation data, trajectories 1, 2, 3. Upper axes: measured output theta (rad) and model output of ReferenceSindyThreshold; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred. The candidate is excluded from ranking by the demonstrated violation of R2.*
