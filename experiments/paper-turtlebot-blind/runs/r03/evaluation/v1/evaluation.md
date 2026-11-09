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
| candidates proposed | 4 |
| accepted by the file and expression checks | 4 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 4 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 4 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 4 among 4 evaluated candidates; groups: FourierRidge; Deadzone; Rational; Periodic. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: FourierRidge. The agent's reason: The regularized Fourier-feature map has the lowest pooled leave-one-trajectory-out free-running `y` RMSE: `0.061109` native `y` units (not supplied), across the three training trajectories with each validation trajectory fitted using only the other two. Its separate coordinate maps relax the shared-displacement hypothesis, while a centered ridge penalty prevents the poor validation of unregularized fits. No test data were accessed. Deadzone, Rational and Periodic retain compact alternative hard-threshold, smooth-rational and angular-feedback structures; their validation errors are larger. Residuals still suggest omitted input-response dynamics, so the recommendation is comparative, not a claim of exact identification.
- Test score S of the recommended candidate (practical selection): 0.0415413 not supplied; eligible: True; rank in the oracle-based selection: 3.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 4 eligible of 4 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (not supplied) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | Rational | 0.0376516 | none | none |
| 2 | Deadzone | 0.0406524 | none | none |
| 3 | FourierRidge | 0.0415413 | none | none |
| 4 | Periodic | 0.0416793 | none | none |

## Candidates

### Candidate FourierRidge

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `y_next = y + c0*x3*cos(x2) + c1*x3*sin(x2) + c2*cos(x2) + c3*sin(x2) + c4*x3*x4*cos(x2) + c5*x3*x4*sin(x2)`
- `x1_next = x1 + c6*x3*cos(x2) + c7*x3*sin(x2) + c8*cos(x2) + c9*sin(x2) + c10*x3*x4*cos(x2) + c11*x3*x4*sin(x2)`
- `x2_next = atan2(sin(x2 + (turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias)), cos(x2 + (turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias)))`
Complexity: 15 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 97 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `y_next = P1*cos(x2) + P2*sin(x2) + P3*x3*cos(x2) + P4*x3*sin(x2) + P5*x3*x4*cos(x2) + P6*x3*x4*sin(x2) + y`; `x1_next = P10*x3*sin(x2) + P11*x3*x4*cos(x2) + P12*x3*x4*sin(x2) + P7*cos(x2) + P8*sin(x2) + P9*x3*cos(x2) + x1`; `x2_next = atan2(sin(P13 + P14*sign(x4)*Max(0, -P15 + Abs(x4)) + x2), cos(P13 + P14*sign(x4)*Max(0, -P15 + Abs(x4)) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0415413 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0236032 | 0.0843075 | 0.992892 | none |
| test-2 | 25 | 25 | 0.0159197 | 0.207875 | 0.956788 | none |
| test-3 | 25 | 25 | 0.0221786 | 0.151622 | 0.977011 | none |
| test-4 | 25 | 25 | 0.0474886 | 0.31596 | 0.900169 | none |
| test-5 | 25 | 25 | 0.0642987 | 0.288452 | 0.916795 | none |
| test-6 | 24 | 24 | 0.0647505 | 0.514863 | 0.734916 | none |
| test-7 | 25 | 25 | 0.0702723 | 0.758082 | 0.425312 | none |
| test-8 | 25 | 25 | 0.0256602 | 0.142465 | 0.979704 | none |
| test-9 | 25 | 25 | 0.0467873 | 0.353551 | 0.875002 | none |
| test-10 | 25 | 25 | 0.0122388 | 0.180203 | 0.967527 | none |
| test-11 | 25 | 25 | 0.026354 | 0.336981 | 0.886444 | none |
| test-12 | 24 | 24 | 0.0152487 | 0.114575 | 0.986873 | none |

Output errors on the training data (pooled RMSE: 0.0406688 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0241761 | 0.474395 | 0.774949 | none |
| 1-2 | 25 | 25 | 0.015617 | 0.202821 | 0.958864 | none |
| 1-3 | 25 | 25 | 0.0547544 | 0.604224 | 0.634914 | none |
| 1-4 | 25 | 25 | 0.0336751 | 0.676518 | 0.542323 | none |
| 1-5 | 25 | 25 | 0.0495929 | 0.332404 | 0.889507 | none |
| 1-6 | 24 | 24 | 0.0449426 | 1.23869 | -0.534343 | none |
| 2-1 | 25 | 25 | 0.0151734 | 0.160596 | 0.974209 | none |
| 2-2 | 25 | 25 | 0.0111222 | 0.108481 | 0.988232 | none |
| 2-3 | 25 | 25 | 0.012337 | 0.179687 | 0.967712 | none |
| 2-4 | 25 | 25 | 0.0443506 | 0.343747 | 0.881838 | none |
| 2-5 | 25 | 25 | 0.0762122 | 0.427304 | 0.817411 | none |
| 2-6 | 24 | 24 | 0.0683237 | 0.472393 | 0.776845 | none |
| 3-1 | 25 | 25 | 0.0237386 | 0.182919 | 0.966541 | none |
| 3-2 | 25 | 25 | 0.0110323 | 0.08042 | 0.993533 | none |
| 3-3 | 25 | 25 | 0.00590493 | 0.0409531 | 0.998323 | none |
| 3-4 | 25 | 25 | 0.0320167 | 0.320167 | 0.897493 | none |
| 3-5 | 25 | 25 | 0.0739148 | 0.595903 | 0.6449 | none |
| 3-6 | 24 | 24 | 0.0158872 | 0.102243 | 0.989546 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.41, 1.41, 1.38, 1.34, 1.34, 0.993, 0.993, 0.991, 0.988, 0.988, 0.374, 0.374, 0.354, 0.354, 0.351; rank 15 of 15.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![FourierRidge test](plots/FourierRidge_test.png)

*Candidate FourierRidge, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of FourierRidge; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![FourierRidge train](plots/FourierRidge_train.png)

*Candidate FourierRidge, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of FourierRidge; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate Deadzone

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (speed_gain*x3 + speed_bias)*cos(x2 + direction_factor*(turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias) + direction_bias)`
- `x1_next = x1 + (speed_gain*x3 + speed_bias)*sin(x2 + direction_factor*(turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias) + direction_bias)`
- `x2_next = atan2(sin(x2 + (turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias)), cos(x2 + (turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias)))`
Complexity: 7 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 89 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `y_next = y + (P1 + P2*x3)*cos(P3 + P4*(P5 + P6*sign(x4)*Max(0, -P7 + Abs(x4))) + x2)`; `x1_next = x1 + (P1 + P2*x3)*sin(P3 + P4*(P5 + P6*sign(x4)*Max(0, -P7 + Abs(x4))) + x2)`; `x2_next = atan2(sin(P5 + P6*sign(x4)*Max(0, -P7 + Abs(x4)) + x2), cos(P5 + P6*sign(x4)*Max(0, -P7 + Abs(x4)) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0406524 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0235404 | 0.0840833 | 0.99293 | none |
| test-2 | 25 | 25 | 0.0106437 | 0.138983 | 0.980684 | none |
| test-3 | 25 | 25 | 0.0218545 | 0.149407 | 0.977678 | none |
| test-4 | 25 | 25 | 0.0474235 | 0.315527 | 0.900443 | none |
| test-5 | 25 | 25 | 0.0636818 | 0.285685 | 0.918384 | none |
| test-6 | 24 | 24 | 0.0583917 | 0.464301 | 0.784425 | none |
| test-7 | 25 | 25 | 0.0720215 | 0.776952 | 0.396345 | none |
| test-8 | 25 | 25 | 0.0257424 | 0.142922 | 0.979573 | none |
| test-9 | 25 | 25 | 0.0468735 | 0.354202 | 0.874541 | none |
| test-10 | 25 | 25 | 0.012392 | 0.182459 | 0.966709 | none |
| test-11 | 25 | 25 | 0.0226524 | 0.289649 | 0.916103 | none |
| test-12 | 24 | 24 | 0.0165518 | 0.124367 | 0.984533 | none |

Output errors on the training data (pooled RMSE: 0.0392911 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0253112 | 0.496668 | 0.753321 | none |
| 1-2 | 25 | 25 | 0.0132551 | 0.172146 | 0.970366 | none |
| 1-3 | 25 | 25 | 0.057185 | 0.631046 | 0.601781 | none |
| 1-4 | 25 | 25 | 0.028069 | 0.563895 | 0.682022 | none |
| 1-5 | 25 | 25 | 0.0433746 | 0.290725 | 0.915479 | none |
| 1-6 | 24 | 24 | 0.0451232 | 1.24366 | -0.5467 | none |
| 2-1 | 25 | 25 | 0.0162779 | 0.172286 | 0.970318 | none |
| 2-2 | 25 | 25 | 0.0139543 | 0.136104 | 0.981476 | none |
| 2-3 | 25 | 25 | 0.0125874 | 0.183334 | 0.966389 | none |
| 2-4 | 25 | 25 | 0.0483068 | 0.37441 | 0.859817 | none |
| 2-5 | 25 | 25 | 0.0666576 | 0.373734 | 0.860323 | none |
| 2-6 | 24 | 24 | 0.0672031 | 0.464645 | 0.784105 | none |
| 3-1 | 25 | 25 | 0.0242663 | 0.186985 | 0.965036 | none |
| 3-2 | 25 | 25 | 0.0104225 | 0.0759746 | 0.994228 | none |
| 3-3 | 25 | 25 | 0.00535418 | 0.0371334 | 0.998621 | none |
| 3-4 | 25 | 25 | 0.0245774 | 0.245774 | 0.939595 | none |
| 3-5 | 25 | 25 | 0.0745701 | 0.601185 | 0.638576 | none |
| 3-6 | 24 | 24 | 0.016808 | 0.108169 | 0.988299 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.38, 1.36, 1.08, 0.99, 0.916, 0.387, 0.359; rank 7 of 7.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![Deadzone test](plots/Deadzone_test.png)

*Candidate Deadzone, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of Deadzone; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![Deadzone train](plots/Deadzone_train.png)

*Candidate Deadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of Deadzone; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate Rational

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (speed_gain*x3 + speed_bias)*cos(x2 + direction_factor*(turn_gain*x4**3/(x4**2 + turn_width**2) + turn_bias) + direction_bias)`
- `x1_next = x1 + (speed_gain*x3 + speed_bias)*sin(x2 + direction_factor*(turn_gain*x4**3/(x4**2 + turn_width**2) + turn_bias) + direction_bias)`
- `x2_next = atan2(sin(x2 + (turn_gain*x4**3/(x4**2 + turn_width**2) + turn_bias)), cos(x2 + (turn_gain*x4**3/(x4**2 + turn_width**2) + turn_bias)))`
Complexity: 7 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 97 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `y_next = y + (P1 + P2*x3)*cos(P3 + P4*(P5 + P6*x4**3/(P7**2 + x4**2)) + x2)`; `x1_next = x1 + (P1 + P2*x3)*sin(P3 + P4*(P5 + P6*x4**3/(P7**2 + x4**2)) + x2)`; `x2_next = atan2(sin(P5 + P6*x4**3/(P7**2 + x4**2) + x2), cos(P5 + P6*x4**3/(P7**2 + x4**2) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0376516 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0267713 | 0.0956235 | 0.990856 | none |
| test-2 | 25 | 25 | 0.00844907 | 0.110326 | 0.987828 | none |
| test-3 | 25 | 25 | 0.0182727 | 0.12492 | 0.984395 | none |
| test-4 | 25 | 25 | 0.0497858 | 0.331244 | 0.890277 | none |
| test-5 | 25 | 25 | 0.0598659 | 0.268566 | 0.927872 | none |
| test-6 | 24 | 24 | 0.0341022 | 0.271164 | 0.92647 | none |
| test-7 | 25 | 25 | 0.0755633 | 0.81516 | 0.335513 | none |
| test-8 | 25 | 25 | 0.0218466 | 0.121292 | 0.985288 | none |
| test-9 | 25 | 25 | 0.0394583 | 0.298169 | 0.911095 | none |
| test-10 | 25 | 25 | 0.0132207 | 0.194662 | 0.962107 | none |
| test-11 | 25 | 25 | 0.0201288 | 0.257381 | 0.933755 | none |
| test-12 | 24 | 24 | 0.0168729 | 0.126779 | 0.983927 | none |

Output errors on the training data (pooled RMSE: 0.0416518 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0231782 | 0.454813 | 0.793146 | none |
| 1-2 | 25 | 25 | 0.014526 | 0.188652 | 0.96441 | none |
| 1-3 | 25 | 25 | 0.0566176 | 0.624785 | 0.609644 | none |
| 1-4 | 25 | 25 | 0.0139842 | 0.280936 | 0.921075 | none |
| 1-5 | 25 | 25 | 0.0503653 | 0.337581 | 0.886039 | none |
| 1-6 | 24 | 24 | 0.0386339 | 1.06481 | -0.133822 | none |
| 2-1 | 25 | 25 | 0.0132161 | 0.13988 | 0.980434 | none |
| 2-2 | 25 | 25 | 0.0134709 | 0.131388 | 0.982737 | none |
| 2-3 | 25 | 25 | 0.0115865 | 0.168756 | 0.971521 | none |
| 2-4 | 25 | 25 | 0.0601442 | 0.466158 | 0.782697 | none |
| 2-5 | 25 | 25 | 0.0493376 | 0.276624 | 0.923479 | none |
| 2-6 | 24 | 24 | 0.0730284 | 0.504921 | 0.745055 | none |
| 3-1 | 25 | 25 | 0.0293203 | 0.225929 | 0.948956 | none |
| 3-2 | 25 | 25 | 0.0137308 | 0.10009 | 0.989982 | none |
| 3-3 | 25 | 25 | 0.00475422 | 0.0329725 | 0.998913 | none |
| 3-4 | 25 | 25 | 0.0487527 | 0.487527 | 0.762318 | none |
| 3-5 | 25 | 25 | 0.0861212 | 0.694311 | 0.517933 | none |
| 3-6 | 24 | 24 | 0.0197507 | 0.127107 | 0.983844 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.39, 1.36, 1.08, 0.993, 0.911, 0.387, 0.263; rank 7 of 7.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![Rational test](plots/Rational_test.png)

*Candidate Rational, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of Rational; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![Rational train](plots/Rational_train.png)

*Candidate Rational, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of Rational; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate Periodic

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (speed_gain*x3 + speed_bias)*cos(x2 + direction_factor*((turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias) + sine_bias*sin(x2) + cosine_bias*cos(x2)) + direction_bias)`
- `x1_next = x1 + (speed_gain*x3 + speed_bias)*sin(x2 + direction_factor*((turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias) + sine_bias*sin(x2) + cosine_bias*cos(x2)) + direction_bias)`
- `x2_next = atan2(sin(x2 + ((turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias) + sine_bias*sin(x2) + cosine_bias*cos(x2))), cos(x2 + ((turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias) + sine_bias*sin(x2) + cosine_bias*cos(x2))))`
Complexity: 9 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 121 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `y_next = y + (P1 + P2*x3)*cos(P3 + P4*(P5 + P6*cos(x2) + P7*sin(x2) + P8*sign(x4)*Max(0, -P9 + Abs(x4))) + x2)`; `x1_next = x1 + (P1 + P2*x3)*sin(P3 + P4*(P5 + P6*cos(x2) + P7*sin(x2) + P8*sign(x4)*Max(0, -P9 + Abs(x4))) + x2)`; `x2_next = atan2(sin(P5 + P6*cos(x2) + P7*sin(x2) + P8*sign(x4)*Max(0, -P9 + Abs(x4)) + x2), cos(P5 + P6*cos(x2) + P7*sin(x2) + P8*sign(x4)*Max(0, -P9 + Abs(x4)) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0416793 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0714004 | 0.255033 | 0.934958 | none |
| test-2 | 25 | 25 | 0.01789 | 0.233603 | 0.94543 | none |
| test-3 | 25 | 25 | 0.0547565 | 0.374338 | 0.859871 | none |
| test-4 | 25 | 25 | 0.0318198 | 0.21171 | 0.955179 | none |
| test-5 | 25 | 25 | 0.0361561 | 0.162201 | 0.973691 | none |
| test-6 | 24 | 24 | 0.0337818 | 0.268615 | 0.927846 | none |
| test-7 | 25 | 25 | 0.0593171 | 0.6399 | 0.590528 | none |
| test-8 | 25 | 25 | 0.0188584 | 0.104701 | 0.989038 | none |
| test-9 | 25 | 25 | 0.0340781 | 0.257513 | 0.933687 | none |
| test-10 | 25 | 25 | 0.0231281 | 0.340537 | 0.884034 | none |
| test-11 | 25 | 25 | 0.0559933 | 0.715969 | 0.487388 | none |
| test-12 | 24 | 24 | 0.0132939 | 0.0998872 | 0.990023 | none |

Output errors on the training data (pooled RMSE: 0.0405969 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0184833 | 0.362689 | 0.868457 | none |
| 1-2 | 25 | 25 | 0.0204764 | 0.265931 | 0.929281 | none |
| 1-3 | 25 | 25 | 0.0210891 | 0.232721 | 0.945841 | none |
| 1-4 | 25 | 25 | 0.0524072 | 1.05284 | -0.108471 | none |
| 1-5 | 25 | 25 | 0.0434499 | 0.29123 | 0.915185 | none |
| 1-6 | 24 | 24 | 0.0476073 | 1.31213 | -0.721684 | none |
| 2-1 | 25 | 25 | 0.030755 | 0.325512 | 0.894042 | none |
| 2-2 | 25 | 25 | 0.0131649 | 0.128404 | 0.983512 | none |
| 2-3 | 25 | 25 | 0.0267116 | 0.389051 | 0.848639 | none |
| 2-4 | 25 | 25 | 0.065857 | 0.510436 | 0.739456 | none |
| 2-5 | 25 | 25 | 0.0512706 | 0.287462 | 0.917365 | none |
| 2-6 | 24 | 24 | 0.0529223 | 0.365907 | 0.866112 | none |
| 3-1 | 25 | 25 | 0.0429385 | 0.330865 | 0.890528 | none |
| 3-2 | 25 | 25 | 0.0059723 | 0.043535 | 0.998105 | none |
| 3-3 | 25 | 25 | 0.00769977 | 0.0534011 | 0.997148 | none |
| 3-4 | 25 | 25 | 0.0512741 | 0.512741 | 0.737097 | none |
| 3-5 | 25 | 25 | 0.0663311 | 0.534762 | 0.714029 | none |
| 3-6 | 24 | 24 | 0.0322345 | 0.207448 | 0.956965 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.37, 1.36, 1.23, 1.08, 1.01, 0.906, 0.676, 0.387, 0.376; rank 9 of 9.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![Periodic test](plots/Periodic_test.png)

*Candidate Periodic, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output y (not supplied) and model output of Periodic; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![Periodic train](plots/Periodic_train.png)

*Candidate Periodic, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of Periodic; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
