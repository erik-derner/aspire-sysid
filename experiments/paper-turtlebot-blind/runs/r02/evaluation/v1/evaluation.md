# Evaluation report: task task-kt5o

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This report contains results on sealed data and is not shown to the agent.

Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])).
Error measures: for one trajectory with scoring interval I of N samples, measured output y[k] (y, not supplied) and model output ŷ[k], SSE = Σ_(k∈I) (ŷ[k] − y[k])²; RMSE = sqrt(SSE/N), in not supplied; NRMSE = RMSE/σ, with μ and σ the mean and the population standard deviation of y on I; R² = 1 − SSE / Σ_(k∈I) (y[k] − μ)²; NRMSE and R² are not applicable when σ = 0. The pooled RMSE over several trajectories is S = sqrt(ΣSSE / ΣN); on the test data it is the ranking score.
Numerical failure limits: y in [-100, 100] not supplied; x1 in [-100, 100] not supplied; x2 in [-1000, 1000] not supplied; evaluation time limit 60 s per candidate and data group; symbolic time limit 10 s per verification.
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

Distinct structures: 3 among 3 evaluated candidates; groups: K_deadzone; K_smooth; K_linear. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: K_deadzone. The agent's reason: The hard dead-zone family has the lowest pooled leave-one-trajectory-out `y` rollout RMSE among retained candidates: approximately `0.116` in unknown `y` units, compared with `0.122` for the smooth monotone family and `0.216` for the affine-input kinematic reference. All use only training data. The smooth family is competitive and has lower full-training error, so the recommendation is provisional given only three experiments. The threshold candidate also avoids local command-response reversal and prevents negative displacement length at small positive `x3`. Residuals still show unresolved input-change transients.
- Test score S of the recommended candidate (practical selection): 0.039405 not supplied; eligible: True; rank in the oracle-based selection: 2.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 3 eligible of 3 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (not supplied) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | K_smooth | 0.0339426 | none | none |
| 2 | K_deadzone | 0.039405 | none | none |
| 3 | K_linear | 0.0456553 | none | none |

## Candidates

### Candidate K_deadzone

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `y_next = y+(Max(0, speedoffset+speedgain*x3))*cos(x2+(turngain*sign(x4)*Max(0, Abs(x4)-threshold)+turnbias)/2)`
- `x1_next = x1+(Max(0, speedoffset+speedgain*x3))*sin(x2+(turngain*sign(x4)*Max(0, Abs(x4)-threshold)+turnbias)/2)`
- `x2_next = atan2(sin(x2+(turngain*sign(x4)*Max(0, Abs(x4)-threshold)+turnbias)), cos(x2+(turngain*sign(x4)*Max(0, Abs(x4)-threshold)+turnbias)))`
Complexity: 5 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 91 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `y_next = y + cos(P3/2 + P4*sign(x4)*Max(0, -P5 + Abs(x4))/2 + x2)*Max(0, P1 + P2*x3)`; `x1_next = x1 + sin(P3/2 + P4*sign(x4)*Max(0, -P5 + Abs(x4))/2 + x2)*Max(0, P1 + P2*x3)`; `x2_next = atan2(sin(P3 + P4*sign(x4)*Max(0, -P5 + Abs(x4)) + x2), cos(P3 + P4*sign(x4)*Max(0, -P5 + Abs(x4)) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.039405 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0633706 | 0.226352 | 0.948765 | none |
| test-2 | 25 | 25 | 0.0107119 | 0.139873 | 0.980436 | none |
| test-3 | 25 | 25 | 0.0372715 | 0.254803 | 0.935075 | none |
| test-4 | 25 | 25 | 0.0315323 | 0.209796 | 0.955985 | none |
| test-5 | 25 | 25 | 0.0364151 | 0.163363 | 0.973313 | none |
| test-6 | 24 | 24 | 0.0481367 | 0.382758 | 0.853496 | none |
| test-7 | 25 | 25 | 0.07796 | 0.841015 | 0.292694 | none |
| test-8 | 25 | 25 | 0.00729448 | 0.0404988 | 0.99836 | none |
| test-9 | 25 | 25 | 0.0376805 | 0.284735 | 0.918926 | none |
| test-10 | 25 | 25 | 0.0116532 | 0.171581 | 0.97056 | none |
| test-11 | 25 | 25 | 0.0260572 | 0.333186 | 0.888987 | none |
| test-12 | 24 | 24 | 0.00905539 | 0.0680402 | 0.995371 | none |

Output errors on the training data (pooled RMSE: 0.0384851 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0253248 | 0.496935 | 0.753056 | none |
| 1-2 | 25 | 25 | 0.0149533 | 0.194202 | 0.962286 | none |
| 1-3 | 25 | 25 | 0.0627104 | 0.69202 | 0.521109 | none |
| 1-4 | 25 | 25 | 0.0414422 | 0.832557 | 0.306849 | none |
| 1-5 | 25 | 25 | 0.0244846 | 0.164112 | 0.973067 | none |
| 1-6 | 24 | 24 | 0.0255799 | 0.705021 | 0.502946 | none |
| 2-1 | 25 | 25 | 0.0189667 | 0.200744 | 0.959702 | none |
| 2-2 | 25 | 25 | 0.0218687 | 0.213296 | 0.954505 | none |
| 2-3 | 25 | 25 | 0.0109819 | 0.15995 | 0.974416 | none |
| 2-4 | 25 | 25 | 0.0660886 | 0.512231 | 0.73762 | none |
| 2-5 | 25 | 25 | 0.042601 | 0.238854 | 0.942949 | none |
| 2-6 | 24 | 24 | 0.0550732 | 0.380778 | 0.855008 | none |
| 3-1 | 25 | 25 | 0.0363218 | 0.27988 | 0.921667 | none |
| 3-2 | 25 | 25 | 0.00768068 | 0.0559882 | 0.996865 | none |
| 3-3 | 25 | 25 | 0.0119689 | 0.0830091 | 0.993109 | none |
| 3-4 | 25 | 25 | 0.0460896 | 0.460896 | 0.787575 | none |
| 3-5 | 25 | 25 | 0.064543 | 0.520347 | 0.729239 | none |
| 3-6 | 24 | 24 | 0.0301912 | 0.194298 | 0.962248 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.38, 1.37, 0.991, 0.351, 0.35; rank 5 of 5.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![K_deadzone test](plots/K_deadzone_test.png)

*Candidate K_deadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of K_deadzone; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![K_deadzone train](plots/K_deadzone_train.png)

*Candidate K_deadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of K_deadzone; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate K_smooth

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `y_next = y+(speedgain*x3)*cos(x2+(turngain*(x4-width*tanh(x4/width))+turnbias)/2)`
- `x1_next = x1+(speedgain*x3)*sin(x2+(turngain*(x4-width*tanh(x4/width))+turnbias)/2)`
- `x2_next = atan2(sin(x2+(turngain*(x4-width*tanh(x4/width))+turnbias)), cos(x2+(turngain*(x4-width*tanh(x4/width))+turnbias)))`
Complexity: 4 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 85 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `y_next = P1*x3*cos(P2/2 + P3*(-P4*tanh(x4/P4) + x4)/2 + x2) + y`; `x1_next = P1*x3*sin(P2/2 + P3*(-P4*tanh(x4/P4) + x4)/2 + x2) + x1`; `x2_next = atan2(sin(P2 + P3*(-P4*tanh(x4/P4) + x4) + x2), cos(P2 + P3*(-P4*tanh(x4/P4) + x4) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0339426 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0376623 | 0.134525 | 0.981903 | none |
| test-2 | 25 | 25 | 0.0179154 | 0.233935 | 0.945275 | none |
| test-3 | 25 | 25 | 0.0219187 | 0.149845 | 0.977546 | none |
| test-4 | 25 | 25 | 0.038137 | 0.25374 | 0.935616 | none |
| test-5 | 25 | 25 | 0.0451882 | 0.20272 | 0.958905 | none |
| test-6 | 24 | 24 | 0.0315015 | 0.250484 | 0.937258 | none |
| test-7 | 25 | 25 | 0.0760982 | 0.820931 | 0.326072 | none |
| test-8 | 25 | 25 | 0.00542573 | 0.0301236 | 0.999093 | none |
| test-9 | 25 | 25 | 0.0286019 | 0.216132 | 0.953287 | none |
| test-10 | 25 | 25 | 0.00896792 | 0.132043 | 0.982565 | none |
| test-11 | 25 | 25 | 0.017299 | 0.221197 | 0.951072 | none |
| test-12 | 24 | 24 | 0.0069224 | 0.0520134 | 0.997295 | none |

Output errors on the training data (pooled RMSE: 0.0437366 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0299529 | 0.587749 | 0.654551 | none |
| 1-2 | 25 | 25 | 0.00561009 | 0.0728593 | 0.994692 | none |
| 1-3 | 25 | 25 | 0.0735205 | 0.811311 | 0.341775 | none |
| 1-4 | 25 | 25 | 0.0177483 | 0.356557 | 0.872867 | none |
| 1-5 | 25 | 25 | 0.0429178 | 0.287663 | 0.91725 | none |
| 1-6 | 24 | 24 | 0.023667 | 0.652298 | 0.574507 | none |
| 2-1 | 25 | 25 | 0.0111004 | 0.117487 | 0.986197 | none |
| 2-2 | 25 | 25 | 0.0141247 | 0.137765 | 0.981021 | none |
| 2-3 | 25 | 25 | 0.0192554 | 0.280453 | 0.921346 | none |
| 2-4 | 25 | 25 | 0.0711948 | 0.551807 | 0.695509 | none |
| 2-5 | 25 | 25 | 0.040252 | 0.225684 | 0.949067 | none |
| 2-6 | 24 | 24 | 0.0688406 | 0.475966 | 0.773456 | none |
| 3-1 | 25 | 25 | 0.0377058 | 0.290544 | 0.915584 | none |
| 3-2 | 25 | 25 | 0.00678835 | 0.0494836 | 0.997551 | none |
| 3-3 | 25 | 25 | 0.0139422 | 0.0966953 | 0.99065 | none |
| 3-4 | 25 | 25 | 0.0650393 | 0.650394 | 0.576988 | none |
| 3-5 | 25 | 25 | 0.0812241 | 0.65483 | 0.571197 | none |
| 3-6 | 24 | 24 | 0.0279952 | 0.180165 | 0.967541 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.41, 1, 0.991, 0.201; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![K_smooth test](plots/K_smooth_test.png)

*Candidate K_smooth, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of K_smooth; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![K_smooth train](plots/K_smooth_train.png)

*Candidate K_smooth, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of K_smooth; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate K_linear

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `y_next = y+(speedoffset+speedgain*x3)*cos(x2+(turngain*x4+turnbias)/2)`
- `x1_next = x1+(speedoffset+speedgain*x3)*sin(x2+(turngain*x4+turnbias)/2)`
- `x2_next = atan2(sin(x2+(turngain*x4+turnbias)), cos(x2+(turngain*x4+turnbias)))`
Complexity: 4 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 51 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `y_next = y + (P1 + P2*x3)*cos(P3/2 + P4*x4/2 + x2)`; `x1_next = x1 + (P1 + P2*x3)*sin(P3/2 + P4*x4/2 + x2)`; `x2_next = atan2(sin(P3 + P4*x4 + x2), cos(P3 + P4*x4 + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0456553 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0226032 | 0.0807358 | 0.993482 | none |
| test-2 | 25 | 25 | 0.00761634 | 0.0994521 | 0.990109 | none |
| test-3 | 25 | 25 | 0.0332825 | 0.227533 | 0.948229 | none |
| test-4 | 25 | 25 | 0.033821 | 0.225024 | 0.949364 | none |
| test-5 | 25 | 25 | 0.0516392 | 0.23166 | 0.946334 | none |
| test-6 | 24 | 24 | 0.10195 | 0.810656 | 0.342836 | none |
| test-7 | 25 | 25 | 0.0737491 | 0.79559 | 0.367037 | none |
| test-8 | 25 | 25 | 0.0109214 | 0.0606355 | 0.996323 | none |
| test-9 | 25 | 25 | 0.0458751 | 0.346658 | 0.879828 | none |
| test-10 | 25 | 25 | 0.0119739 | 0.176304 | 0.968917 | none |
| test-11 | 25 | 25 | 0.0393583 | 0.503263 | 0.746726 | none |
| test-12 | 24 | 24 | 0.0051752 | 0.0388853 | 0.998488 | none |

Output errors on the training data (pooled RMSE: 0.0406433 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0382781 | 0.751111 | 0.435832 | none |
| 1-2 | 25 | 25 | 0.00567624 | 0.0737183 | 0.994566 | none |
| 1-3 | 25 | 25 | 0.0656599 | 0.724568 | 0.475001 | none |
| 1-4 | 25 | 25 | 0.0605208 | 1.21584 | -0.47826 | none |
| 1-5 | 25 | 25 | 0.033085 | 0.221757 | 0.950824 | none |
| 1-6 | 24 | 24 | 0.0466953 | 1.287 | -0.656356 | none |
| 2-1 | 25 | 25 | 0.015279 | 0.161714 | 0.973849 | none |
| 2-2 | 25 | 25 | 0.0299199 | 0.291824 | 0.914839 | none |
| 2-3 | 25 | 25 | 0.0102873 | 0.149833 | 0.97755 | none |
| 2-4 | 25 | 25 | 0.041098 | 0.318537 | 0.898534 | none |
| 2-5 | 25 | 25 | 0.0879356 | 0.493035 | 0.756917 | none |
| 2-6 | 24 | 24 | 0.0516776 | 0.357301 | 0.872336 | none |
| 3-1 | 25 | 25 | 0.0268753 | 0.207089 | 0.957114 | none |
| 3-2 | 25 | 25 | 0.0172306 | 0.125602 | 0.984224 | none |
| 3-3 | 25 | 25 | 0.0117952 | 0.0818046 | 0.993308 | none |
| 3-4 | 25 | 25 | 0.0115623 | 0.115623 | 0.986631 | none |
| 3-5 | 25 | 25 | 0.0442922 | 0.357085 | 0.87249 | none |
| 3-6 | 24 | 24 | 0.0204771 | 0.131782 | 0.982634 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.05, 0.952, 0.387; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![K_linear test](plots/K_linear_test.png)

*Candidate K_linear, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of K_linear; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![K_linear train](plots/K_linear_train.png)

*Candidate K_linear, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of K_linear; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
