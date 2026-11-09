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

Distinct structures: 5 among 5 evaluated candidates; groups: ReferencePysrDefaultS1; ReferencePysrDefaultS2; ReferencePysrDefaultS3; ReferencePysrDefaultS4; ReferencePysrDefaultS5. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

The agent recommends no candidate. Its reason: Reference models found by PySR without the agent, one per seed; none is recommended.
- Harness note: the agent recommends no candidate.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 5 eligible of 5 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | ReferencePysrDefaultS4 | 0.045849 | none | none |
| 2 | ReferencePysrDefaultS2 | 0.0458512 | none | none |
| 3 | ReferencePysrDefaultS5 | 0.0458535 | none | none |
| 4 | ReferencePysrDefaultS1 | 0.0531243 | none | none |
| 5 | ReferencePysrDefaultS3 | 0.0611749 | none | none |

## Candidates

### Candidate ReferencePysrDefaultS1

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = ca1*v_f*(ca2 + phi*(ca4 + phi + v_f*(phi + phi/(ca3 + phi)))) + x`
- `y_next = phi*v_f*(cb3 - phi**2)*(cb1*phi**2 + cb2) + y`
- `phi_next = cc1*v_a + phi`
Complexity: 8 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 47 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = P1*v_f*(P2 + phi*(P3 + phi + v_f*(phi + phi/(P4 + phi)))) + x`; `y_next = phi*v_f*(P5 + P6*phi**2)*(P7 - phi**2) + y`; `phi_next = P8*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0531243 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0485728 | 0.173496 | 0.969899 | none |
| test-2 | 25 | 25 | 0.0338485 | 0.441984 | 0.80465 | none |
| test-3 | 25 | 25 | 0.024428 | 0.167 | 0.972111 | none |
| test-4 | 25 | 25 | 0.065005 | 0.432503 | 0.812941 | none |
| test-5 | 25 | 25 | 0.0955156 | 0.428495 | 0.816392 | none |
| test-6 | 24 | 24 | 0.0485642 | 0.386158 | 0.850882 | none |
| test-7 | 25 | 25 | 0.00469885 | 0.0506901 | 0.997431 | none |
| test-8 | 25 | 25 | 0.047569 | 0.264102 | 0.93025 | none |
| test-9 | 25 | 25 | 0.0584719 | 0.441846 | 0.804772 | none |
| test-10 | 25 | 25 | 0.00660854 | 0.097304 | 0.990532 | none |
| test-11 | 25 | 25 | 0.0841074 | 1.07546 | -0.156604 | none |
| test-12 | 24 | 24 | 0.0339142 | 0.254824 | 0.935065 | none |

Output errors on the training data (pooled RMSE: 0.0991978 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0162947 | 0.319742 | 0.897765 | none |
| 1-2 | 25 | 25 | 0.0210646 | 0.273569 | 0.92516 | none |
| 1-3 | 25 | 25 | 0.00882395 | 0.0973737 | 0.990518 | none |
| 1-4 | 25 | 25 | 0.0638518 | 1.28276 | -0.645464 | none |
| 1-5 | 25 | 25 | 0.0758606 | 0.508467 | 0.741461 | none |
| 1-6 | 24 | 24 | 0.0646082 | 1.7807 | -2.1709 | none |
| 2-1 | 25 | 25 | 0.0370086 | 0.3917 | 0.846571 | none |
| 2-2 | 25 | 25 | 0.0418757 | 0.408434 | 0.833181 | none |
| 2-3 | 25 | 25 | 0.106282 | 1.54798 | -1.39624 | none |
| 2-4 | 25 | 25 | 0.118807 | 0.920834 | 0.152065 | none |
| 2-5 | 25 | 25 | 0.0822006 | 0.46088 | 0.78759 | none |
| 2-6 | 24 | 24 | 0.351154 | 2.42789 | -4.89464 | none |
| 3-1 | 25 | 25 | 0.009783 | 0.0753834 | 0.994317 | none |
| 3-2 | 25 | 25 | 0.0292789 | 0.213428 | 0.954449 | none |
| 3-3 | 25 | 25 | 0.0295962 | 0.205262 | 0.957867 | none |
| 3-4 | 25 | 25 | 0.0379127 | 0.379127 | 0.856263 | none |
| 3-5 | 25 | 25 | 0.0628063 | 0.506346 | 0.743614 | none |
| 3-6 | 24 | 24 | 0.0213616 | 0.137474 | 0.981101 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.66, 1.44, 1.11, 1, 0.654, 0.512, 0.496, 0.0214; rank 8 of 8.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrDefaultS1 test](plots/ReferencePysrDefaultS1_test.png)

*Candidate ReferencePysrDefaultS1, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS1; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferencePysrDefaultS1 train](plots/ReferencePysrDefaultS1_train.png)

*Candidate ReferencePysrDefaultS1, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS1; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrDefaultS2

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = v_f*(ca3 + phi**2*(ca1 + ca2*phi**2)) + x`
- `y_next = phi*v_f*(cb1 + cb2/(cb3 + cb4*phi**2)) + y`
- `phi_next = cc1*v_a + phi`
Complexity: 8 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 40 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = v_f*(P1 + phi**2*(P2 + P3*phi**2)) + x`; `y_next = phi*v_f*(P4 + P5/(P6 + P7*phi**2)) + y`; `phi_next = P8*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0458512 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0187859 | 0.0671007 | 0.995497 | none |
| test-2 | 25 | 25 | 0.0104744 | 0.136771 | 0.981294 | none |
| test-3 | 25 | 25 | 0.0513281 | 0.3509 | 0.876869 | none |
| test-4 | 25 | 25 | 0.0393942 | 0.262104 | 0.931301 | none |
| test-5 | 25 | 25 | 0.064851 | 0.29093 | 0.91536 | none |
| test-6 | 24 | 24 | 0.0427338 | 0.339797 | 0.884538 | none |
| test-7 | 25 | 25 | 0.00638645 | 0.0688957 | 0.995253 | none |
| test-8 | 25 | 25 | 0.0281502 | 0.15629 | 0.975574 | none |
| test-9 | 25 | 25 | 0.0427939 | 0.323375 | 0.895429 | none |
| test-10 | 25 | 25 | 0.00848747 | 0.124969 | 0.984383 | none |
| test-11 | 25 | 25 | 0.105261 | 1.34594 | -0.811545 | none |
| test-12 | 24 | 24 | 0.025729 | 0.193322 | 0.962627 | none |

Output errors on the training data (pooled RMSE: 0.0484104 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0251488 | 0.493482 | 0.756476 | none |
| 1-2 | 25 | 25 | 0.0127361 | 0.165406 | 0.972641 | none |
| 1-3 | 25 | 25 | 0.0200358 | 0.221098 | 0.951116 | none |
| 1-4 | 25 | 25 | 0.0599264 | 1.2039 | -0.449367 | none |
| 1-5 | 25 | 25 | 0.0646466 | 0.433304 | 0.812248 | none |
| 1-6 | 24 | 24 | 0.0764141 | 2.10609 | -3.43562 | none |
| 2-1 | 25 | 25 | 0.0385877 | 0.408414 | 0.833198 | none |
| 2-2 | 25 | 25 | 0.0104069 | 0.101504 | 0.989697 | none |
| 2-3 | 25 | 25 | 0.049409 | 0.719635 | 0.482125 | none |
| 2-4 | 25 | 25 | 0.0919949 | 0.713022 | 0.4916 | none |
| 2-5 | 25 | 25 | 0.0644381 | 0.361289 | 0.86947 | none |
| 2-6 | 24 | 24 | 0.0585852 | 0.40506 | 0.835926 | none |
| 3-1 | 25 | 25 | 0.0307033 | 0.236586 | 0.944027 | none |
| 3-2 | 25 | 25 | 0.0103614 | 0.075529 | 0.994295 | none |
| 3-3 | 25 | 25 | 0.00766521 | 0.0531614 | 0.997174 | none |
| 3-4 | 25 | 25 | 0.0549647 | 0.549648 | 0.697887 | none |
| 3-5 | 25 | 25 | 0.0529783 | 0.427112 | 0.817576 | none |
| 3-6 | 24 | 24 | 0.0215411 | 0.138629 | 0.980782 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.94, 1.57, 1, 0.713, 0.469, 0.16, 0.0274, 1.27e-16; rank 7 of 8.
- Locally indistinguishable combination: cb2 (+0.783), cb3 (+0.570), cb4 (+0.249); relative singular value 6.54e-17.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrDefaultS2 test](plots/ReferencePysrDefaultS2_test.png)

*Candidate ReferencePysrDefaultS2, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS2; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferencePysrDefaultS2 train](plots/ReferencePysrDefaultS2_train.png)

*Candidate ReferencePysrDefaultS2, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS2; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrDefaultS3

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = ca3*x - v_f*(ca1 + ca2*phi*(phi + v_f + y*(v_a*(phi*v_f + v_a) - v_f)))`
- `y_next = phi*v_f/(cb1*phi**4 + cb2) + y`
- `phi_next = cc1*v_a + phi`
Complexity: 6 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 47 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = P1*x - v_f*(P2 + P3*phi*(phi + v_f + y*(v_a*(phi*v_f + v_a) - v_f)))`; `y_next = phi*v_f/(P4 + P5*phi**4) + y`; `phi_next = P6*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0611749 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0854475 | 0.305207 | 0.906848 | none |
| test-2 | 25 | 25 | 0.0497769 | 0.649972 | 0.577536 | none |
| test-3 | 25 | 25 | 0.0358766 | 0.245268 | 0.939844 | none |
| test-4 | 25 | 25 | 0.0367821 | 0.244725 | 0.940109 | none |
| test-5 | 25 | 25 | 0.0615307 | 0.276035 | 0.923805 | none |
| test-6 | 24 | 24 | 0.088613 | 0.704606 | 0.503531 | none |
| test-7 | 25 | 25 | 0.00727659 | 0.0784983 | 0.993838 | none |
| test-8 | 25 | 25 | 0.0539823 | 0.299709 | 0.910175 | none |
| test-9 | 25 | 25 | 0.0534225 | 0.40369 | 0.837034 | none |
| test-10 | 25 | 25 | 0.0322138 | 0.474315 | 0.775025 | none |
| test-11 | 25 | 25 | 0.111281 | 1.42291 | -1.02468 | none |
| test-12 | 24 | 24 | 0.0411261 | 0.309012 | 0.904512 | none |

Output errors on the training data (pooled RMSE: 0.0827133 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.00732767 | 0.143787 | 0.979325 | none |
| 1-2 | 25 | 25 | 0.0271383 | 0.35245 | 0.875779 | none |
| 1-3 | 25 | 25 | 0.0134206 | 0.148098 | 0.978067 | none |
| 1-4 | 25 | 25 | 0.0938159 | 1.88472 | -2.55218 | none |
| 1-5 | 25 | 25 | 0.124062 | 0.831546 | 0.308531 | none |
| 1-6 | 24 | 24 | 0.0612794 | 1.68896 | -1.85257 | none |
| 2-1 | 25 | 25 | 0.018111 | 0.191688 | 0.963256 | none |
| 2-2 | 25 | 25 | 0.0439724 | 0.428885 | 0.816058 | none |
| 2-3 | 25 | 25 | 0.0667434 | 0.97211 | 0.0550023 | none |
| 2-4 | 25 | 25 | 0.136422 | 1.05736 | -0.118011 | none |
| 2-5 | 25 | 25 | 0.0958484 | 0.5374 | 0.711202 | none |
| 2-6 | 24 | 24 | 0.235604 | 1.62897 | -1.65355 | none |
| 3-1 | 25 | 25 | 0.0185751 | 0.143131 | 0.979514 | none |
| 3-2 | 25 | 25 | 0.0329237 | 0.239997 | 0.942402 | none |
| 3-3 | 25 | 25 | 0.0274626 | 0.190465 | 0.963723 | none |
| 3-4 | 25 | 25 | 0.0477313 | 0.477314 | 0.772172 | none |
| 3-5 | 25 | 25 | 0.0301813 | 0.243322 | 0.940794 | none |
| 3-6 | 24 | 24 | 0.0199609 | 0.12846 | 0.983498 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.4, 1.2, 1, 0.933, 0.748, 0.396; rank 6 of 6.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrDefaultS3 test](plots/ReferencePysrDefaultS3_test.png)

*Candidate ReferencePysrDefaultS3, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS3; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferencePysrDefaultS3 train](plots/ReferencePysrDefaultS3_train.png)

*Candidate ReferencePysrDefaultS3, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS3; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrDefaultS4

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `x_next = ca3*v_f + phi**2*v_f*(ca1 + ca2*phi**2) + x`
- `y_next = -phi*(cb1 + cb2*phi**2)*(cb3*x + v_f) + y`
- `phi_next = cc1*v_a + phi`
Complexity: 7 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 39 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `x_next = P1*v_f + phi**2*v_f*(P2 + P3*phi**2) + x`; `y_next = -phi*(P4 + P5*phi**2)*(P6*x + v_f) + y`; `phi_next = P7*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.045849 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0187892 | 0.0671126 | 0.995496 | none |
| test-2 | 25 | 25 | 0.0104745 | 0.136773 | 0.981293 | none |
| test-3 | 25 | 25 | 0.0513427 | 0.351 | 0.876799 | none |
| test-4 | 25 | 25 | 0.0393812 | 0.262018 | 0.931346 | none |
| test-5 | 25 | 25 | 0.0648345 | 0.290856 | 0.915403 | none |
| test-6 | 24 | 24 | 0.0427197 | 0.339686 | 0.884614 | none |
| test-7 | 25 | 25 | 0.00639325 | 0.068969 | 0.995243 | none |
| test-8 | 25 | 25 | 0.0281345 | 0.156202 | 0.975601 | none |
| test-9 | 25 | 25 | 0.0427822 | 0.323286 | 0.895486 | none |
| test-10 | 25 | 25 | 0.00848357 | 0.124912 | 0.984397 | none |
| test-11 | 25 | 25 | 0.105275 | 1.34612 | -0.812049 | none |
| test-12 | 24 | 24 | 0.0257114 | 0.19319 | 0.962678 | none |

Output errors on the training data (pooled RMSE: 0.0484135 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0251549 | 0.493601 | 0.756358 | none |
| 1-2 | 25 | 25 | 0.0127284 | 0.165306 | 0.972674 | none |
| 1-3 | 25 | 25 | 0.020051 | 0.221266 | 0.951041 | none |
| 1-4 | 25 | 25 | 0.059952 | 1.20441 | -0.450605 | none |
| 1-5 | 25 | 25 | 0.0646644 | 0.433423 | 0.812145 | none |
| 1-6 | 24 | 24 | 0.0763997 | 2.10569 | -3.43395 | none |
| 2-1 | 25 | 25 | 0.0385998 | 0.408541 | 0.833094 | none |
| 2-2 | 25 | 25 | 0.0104246 | 0.101676 | 0.989662 | none |
| 2-3 | 25 | 25 | 0.0494205 | 0.719804 | 0.481883 | none |
| 2-4 | 25 | 25 | 0.0919906 | 0.712988 | 0.491648 | none |
| 2-5 | 25 | 25 | 0.0644656 | 0.361444 | 0.869358 | none |
| 2-6 | 24 | 24 | 0.0585348 | 0.404712 | 0.836208 | none |
| 3-1 | 25 | 25 | 0.0307163 | 0.236686 | 0.94398 | none |
| 3-2 | 25 | 25 | 0.0103526 | 0.075465 | 0.994305 | none |
| 3-3 | 25 | 25 | 0.00765644 | 0.0531006 | 0.99718 | none |
| 3-4 | 25 | 25 | 0.0549908 | 0.549908 | 0.697601 | none |
| 3-5 | 25 | 25 | 0.0529629 | 0.426988 | 0.817681 | none |
| 3-6 | 24 | 24 | 0.0215479 | 0.138673 | 0.98077 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.57, 1.43, 1, 0.948, 0.713, 0.239, 0.16; rank 7 of 7.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrDefaultS4 test](plots/ReferencePysrDefaultS4_test.png)

*Candidate ReferencePysrDefaultS4, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS4; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferencePysrDefaultS4 train](plots/ReferencePysrDefaultS4_train.png)

*Candidate ReferencePysrDefaultS4, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS4; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrDefaultS5

Position in the agent's order: 5. Status: evaluated.
File and expression checks: passed.
- `x_next = -v_f*(ca2 - phi**2*(ca1 + ca3*phi**2)) + x`
- `y_next = phi*v_f*(cb1*phi*(cb2*phi**3 + phi) + cb3) + y`
- `phi_next = cc1*v_a + phi`
Complexity: 7 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 41 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 5: `x_next = -v_f*(P1 - phi**2*(P2 + P3*phi**2)) + x`; `y_next = phi*v_f*(P4 + P5*phi*(P6*phi**3 + phi)) + y`; `phi_next = P7*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0458535 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0187812 | 0.0670839 | 0.9955 | none |
| test-2 | 25 | 25 | 0.0104748 | 0.136777 | 0.981292 | none |
| test-3 | 25 | 25 | 0.0513081 | 0.350763 | 0.876965 | none |
| test-4 | 25 | 25 | 0.0394116 | 0.26222 | 0.931241 | none |
| test-5 | 25 | 25 | 0.0648734 | 0.29103 | 0.915301 | none |
| test-6 | 24 | 24 | 0.0427479 | 0.33991 | 0.884461 | none |
| test-7 | 25 | 25 | 0.00637978 | 0.0688236 | 0.995263 | none |
| test-8 | 25 | 25 | 0.0281647 | 0.15637 | 0.975548 | none |
| test-9 | 25 | 25 | 0.0428097 | 0.323494 | 0.895351 | none |
| test-10 | 25 | 25 | 0.00849032 | 0.125011 | 0.984372 | none |
| test-11 | 25 | 25 | 0.105245 | 1.34574 | -0.811021 | none |
| test-12 | 24 | 24 | 0.0257374 | 0.193385 | 0.962602 | none |

Output errors on the training data (pooled RMSE: 0.0484067 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0251407 | 0.493322 | 0.756634 | none |
| 1-2 | 25 | 25 | 0.0127456 | 0.165529 | 0.9726 | none |
| 1-3 | 25 | 25 | 0.0200207 | 0.220932 | 0.951189 | none |
| 1-4 | 25 | 25 | 0.0599211 | 1.20379 | -0.44911 | none |
| 1-5 | 25 | 25 | 0.0646576 | 0.433377 | 0.812184 | none |
| 1-6 | 24 | 24 | 0.0764102 | 2.10598 | -3.43516 | none |
| 2-1 | 25 | 25 | 0.0385733 | 0.408261 | 0.833323 | none |
| 2-2 | 25 | 25 | 0.0103998 | 0.101435 | 0.989711 | none |
| 2-3 | 25 | 25 | 0.0494126 | 0.719688 | 0.482049 | none |
| 2-4 | 25 | 25 | 0.0919887 | 0.712974 | 0.491668 | none |
| 2-5 | 25 | 25 | 0.0644541 | 0.361379 | 0.869405 | none |
| 2-6 | 24 | 24 | 0.05855 | 0.404817 | 0.836123 | none |
| 3-1 | 25 | 25 | 0.030686 | 0.236452 | 0.94409 | none |
| 3-2 | 25 | 25 | 0.0103716 | 0.0756039 | 0.994284 | none |
| 3-3 | 25 | 25 | 0.00767704 | 0.0532435 | 0.997165 | none |
| 3-4 | 25 | 25 | 0.0549481 | 0.549482 | 0.69807 | none |
| 3-5 | 25 | 25 | 0.0529887 | 0.427196 | 0.817503 | none |
| 3-6 | 24 | 24 | 0.0215315 | 0.138567 | 0.980799 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.67, 1.57, 1, 0.713, 0.454, 0.16, 0.131; rank 7 of 7.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrDefaultS5 test](plots/ReferencePysrDefaultS5_test.png)

*Candidate ReferencePysrDefaultS5, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS5; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferencePysrDefaultS5 train](plots/ReferencePysrDefaultS5_train.png)

*Candidate ReferencePysrDefaultS5, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrDefaultS5; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
