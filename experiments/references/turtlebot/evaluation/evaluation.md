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
| candidates proposed | 3 |
| accepted by the file and expression checks | 3 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 3 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 3 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 3 among 3 evaluated candidates; groups: ReferenceUnicycle; ReferenceSindy; ReferenceSindyThreshold. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

The agent recommends no candidate. Its reason: Reference models estimated without the agent; none is recommended.
- Harness note: the agent recommends no candidate.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 3 eligible of 3 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | ReferenceUnicycle | 0.0444837 | none | none |
| 2 | ReferenceSindyThreshold | 0.15296 | none | none |
| 3 | ReferenceSindy | 0.21401 | none | none |

## Candidates

### Candidate ReferenceUnicycle

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = x + p_v*v_f*cos(phi)`
- `y_next = y + p_v*v_f*sin(phi)`
- `phi_next = phi + p_w*v_a`
Complexity: 2 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 19 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = P1*v_f*cos(phi) + x`; `y_next = P1*v_f*sin(phi) + y`; `phi_next = P2*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.0444837 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0385722 | 0.137775 | 0.981018 | none |
| test-2 | 25 | 25 | 0.0141064 | 0.184197 | 0.966071 | none |
| test-3 | 25 | 25 | 0.0447553 | 0.305966 | 0.906385 | none |
| test-4 | 25 | 25 | 0.0312299 | 0.207784 | 0.956826 | none |
| test-5 | 25 | 25 | 0.0459683 | 0.20622 | 0.957473 | none |
| test-6 | 24 | 24 | 0.0852927 | 0.678204 | 0.540039 | none |
| test-7 | 25 | 25 | 0.0658625 | 0.71051 | 0.495175 | none |
| test-8 | 25 | 25 | 0.0120522 | 0.0669134 | 0.995523 | none |
| test-9 | 25 | 25 | 0.0439135 | 0.331835 | 0.889885 | none |
| test-10 | 25 | 25 | 0.0125121 | 0.184228 | 0.96606 | none |
| test-11 | 25 | 25 | 0.0568263 | 0.72662 | 0.472023 | none |
| test-12 | 24 | 24 | 0.00539497 | 0.0405366 | 0.998357 | none |

Output errors on the training data (pooled RMSE: 0.039598 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0287424 | 0.563996 | 0.681909 | none |
| 1-2 | 25 | 25 | 0.0103804 | 0.134812 | 0.981826 | none |
| 1-3 | 25 | 25 | 0.0397859 | 0.439044 | 0.80724 | none |
| 1-4 | 25 | 25 | 0.0710968 | 1.42831 | -1.04006 | none |
| 1-5 | 25 | 25 | 0.0392206 | 0.262882 | 0.930893 | none |
| 1-6 | 24 | 24 | 0.0456345 | 1.25776 | -0.581953 | none |
| 2-1 | 25 | 25 | 0.0185676 | 0.19652 | 0.96138 | none |
| 2-2 | 25 | 25 | 0.0277166 | 0.270333 | 0.92692 | none |
| 2-3 | 25 | 25 | 0.00903247 | 0.131557 | 0.982693 | none |
| 2-4 | 25 | 25 | 0.0451945 | 0.350287 | 0.877299 | none |
| 2-5 | 25 | 25 | 0.0808265 | 0.453175 | 0.794632 | none |
| 2-6 | 24 | 24 | 0.0525859 | 0.363581 | 0.867809 | none |
| 3-1 | 25 | 25 | 0.0349544 | 0.269343 | 0.927454 | none |
| 3-2 | 25 | 25 | 0.0135463 | 0.0987452 | 0.990249 | none |
| 3-3 | 25 | 25 | 0.0106805 | 0.0740737 | 0.994513 | none |
| 3-4 | 25 | 25 | 0.0264352 | 0.264352 | 0.930118 | none |
| 3-5 | 25 | 25 | 0.0428904 | 0.345783 | 0.880434 | none |
| 3-6 | 24 | 24 | 0.0215138 | 0.138454 | 0.980831 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1, 1; rank 2 of 2.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferenceUnicycle test](plots/ReferenceUnicycle_test.png)

*Candidate ReferenceUnicycle, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferenceUnicycle; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferenceUnicycle train](plots/ReferenceUnicycle_train.png)

*Candidate ReferenceUnicycle, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferenceUnicycle; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferenceSindy

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = c_x_1*x`
- `y_next = c_y_1*y`
- `phi_next = c_phi_1*phi`
Complexity: 3 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 9 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = P1*x`; `y_next = P2*y`; `phi_next = P3*phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.21401 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.587948 | 2.10007 | -3.41031 | none |
| test-2 | 25 | 25 | 0.0623397 | 0.814014 | 0.337381 | none |
| test-3 | 25 | 25 | 0.100104 | 0.68435 | 0.531666 | none |
| test-4 | 25 | 25 | 0.0508343 | 0.33822 | 0.885607 | none |
| test-5 | 25 | 25 | 0.0603767 | 0.270858 | 0.926636 | none |
| test-6 | 24 | 24 | 0.155482 | 1.23631 | -0.528464 | none |
| test-7 | 25 | 25 | 0.167656 | 1.80864 | -2.27118 | none |
| test-8 | 25 | 25 | 0.237437 | 1.31825 | -0.737773 | none |
| test-9 | 25 | 25 | 0.174738 | 1.32042 | -0.743507 | none |
| test-10 | 25 | 25 | 0.108842 | 1.60258 | -1.56828 | none |
| test-11 | 25 | 25 | 0.100118 | 1.28018 | -0.638871 | none |
| test-12 | 24 | 24 | 0.144429 | 1.08521 | -0.177676 | none |

Output errors on the training data (pooled RMSE: 0.221663 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.115053 | 2.25762 | -4.09686 | none |
| 1-2 | 25 | 25 | 0.143343 | 1.86162 | -2.46565 | none |
| 1-3 | 25 | 25 | 0.187052 | 2.06415 | -3.26072 | none |
| 1-4 | 25 | 25 | 0.0574838 | 1.15483 | -0.333621 | none |
| 1-5 | 25 | 25 | 0.451521 | 3.02639 | -8.15905 | none |
| 1-6 | 24 | 24 | 0.0784176 | 2.16131 | -3.67125 | none |
| 2-1 | 25 | 25 | 0.211956 | 2.24335 | -4.03261 | none |
| 2-2 | 25 | 25 | 0.116259 | 1.13393 | -0.285796 | none |
| 2-3 | 25 | 25 | 0.213051 | 3.10306 | -8.62896 | none |
| 2-4 | 25 | 25 | 0.362803 | 2.81197 | -6.90715 | none |
| 2-5 | 25 | 25 | 0.412723 | 2.31404 | -4.3548 | none |
| 2-6 | 24 | 24 | 0.231151 | 1.59819 | -1.5542 | none |
| 3-1 | 25 | 25 | 0.275057 | 2.11946 | -3.49212 | none |
| 3-2 | 25 | 25 | 0.176605 | 1.28736 | -0.657295 | none |
| 3-3 | 25 | 25 | 0.147542 | 1.02326 | -0.0470648 | none |
| 3-4 | 25 | 25 | 0.0890597 | 0.890597 | 0.206836 | none |
| 3-5 | 25 | 25 | 0.0233205 | 0.18801 | 0.964652 | none |
| 3-6 | 24 | 24 | 0.0509019 | 0.327583 | 0.892689 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1, 1, 1; rank 3 of 3.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferenceSindy test](plots/ReferenceSindy_test.png)

*Candidate ReferenceSindy, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferenceSindy; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferenceSindy train](plots/ReferenceSindy_train.png)

*Candidate ReferenceSindy, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferenceSindy; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferenceSindyThreshold

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = c_x_1 + c_x_2*x + c_x_3*y + c_x_4*phi + c_x_5*v_f + c_x_6*x**2 + c_x_7*x*y + c_x_8*x*v_f + c_x_9*y**2 + c_x_10*y*phi + c_x_11*y*v_f + c_x_12*y*v_a + c_x_13*phi**2 + c_x_14*phi*v_f + c_x_15*phi*v_a + c_x_16*v_f**2 + c_x_17*v_f*v_a`
- `y_next = c_y_1 + c_y_2*x + c_y_3*y + c_y_4*v_f + c_y_5*v_a + c_y_6*x**2 + c_y_7*x*y + c_y_8*x*phi + c_y_9*x*v_f + c_y_10*x*v_a + c_y_11*y**2 + c_y_12*y*phi + c_y_13*y*v_f + c_y_14*y*v_a + c_y_15*phi**2 + c_y_16*phi*v_f + c_y_17*phi*v_a + c_y_18*v_f**2 + c_y_19*v_f*v_a`
- `phi_next = c_phi_1 + c_phi_2*x + c_phi_3*y + c_phi_4*phi + c_phi_5*v_f + c_phi_6*v_a + c_phi_7*x**2 + c_phi_8*x*y + c_phi_9*x*phi + c_phi_10*x*v_f + c_phi_11*y**2 + c_phi_12*y*phi + c_phi_13*y*v_f + c_phi_14*y*v_a + c_phi_15*phi**2 + c_phi_16*phi*v_f + c_phi_17*v_f**2 + c_phi_18*v_f*v_a + c_phi_19*v_a**2`
Complexity: 55 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 214 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = P1 + P10*phi*y + P11*v_f*y + P12*v_a*y + P13*phi*v_f + P14*phi*v_a + P15*v_a*v_f + P16*x*y + P17*v_f*x + P2*phi**2 + P3*v_f**2 + P4*x + P5*y + P6*phi + P7*v_f + P8*x**2 + P9*y**2`; `y_next = P18 + P19*y**2 + P20*phi**2 + P21*v_f**2 + P22*x + P23*y + P24*v_f + P25*v_a + P26*x**2 + P27*v_a*x + P28*phi*y + P29*v_f*y + P30*v_a*y + P31*phi*v_f + P32*phi*v_a + P33*v_a*v_f + P34*x*y + P35*phi*x + P36*v_f*x`; `phi_next = P37 + P38*y**2 + P39*phi**2 + P40*v_f**2 + P41*v_a**2 + P42*x + P43*y + P44*phi + P45*v_f + P46*v_a + P47*x**2 + P48*v_f*x + P49*phi*y + P50*v_f*y + P51*v_a*y + P52*phi*v_f + P53*v_a*v_f + P54*x*y + P55*phi*x`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the test data (sealed) (pooled RMSE: 0.15296 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.318129 | 1.13631 | -0.291211 | none |
| test-2 | 25 | 25 | 0.147531 | 1.92642 | -2.7111 | none |
| test-3 | 25 | 25 | 0.153431 | 1.04892 | -0.100232 | none |
| test-4 | 25 | 25 | 0.0838586 | 0.557943 | 0.688699 | none |
| test-5 | 25 | 25 | 0.0772528 | 0.346566 | 0.879892 | none |
| test-6 | 24 | 24 | 0.260832 | 2.074 | -3.30149 | none |
| test-7 | 25 | 25 | 0.0210386 | 0.22696 | 0.948489 | none |
| test-8 | 25 | 25 | 0.132566 | 0.736002 | 0.458301 | none |
| test-9 | 25 | 25 | 0.119787 | 0.905176 | 0.180656 | none |
| test-10 | 25 | 25 | 0.0255603 | 0.376349 | 0.858361 | none |
| test-11 | 25 | 25 | 0.136618 | 1.74689 | -2.05162 | none |
| test-12 | 24 | 24 | 0.0498232 | 0.374361 | 0.859854 | none |

Output errors on the training data (pooled RMSE: 0.0445852 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0185384 | 0.363769 | 0.867672 | none |
| 1-2 | 25 | 25 | 0.00721022 | 0.0936404 | 0.991231 | none |
| 1-3 | 25 | 25 | 0.0163993 | 0.180969 | 0.96725 | none |
| 1-4 | 25 | 25 | 0.016492 | 0.331318 | 0.890229 | none |
| 1-5 | 25 | 25 | 0.0785651 | 0.526595 | 0.722698 | none |
| 1-6 | 24 | 24 | 0.0226469 | 0.624183 | 0.610395 | none |
| 2-1 | 25 | 25 | 0.0357669 | 0.378558 | 0.856694 | none |
| 2-2 | 25 | 25 | 0.0563428 | 0.549539 | 0.698006 | none |
| 2-3 | 25 | 25 | 0.0737675 | 1.07441 | -0.154367 | none |
| 2-4 | 25 | 25 | 0.0197069 | 0.152741 | 0.97667 | none |
| 2-5 | 25 | 25 | 0.0682617 | 0.382728 | 0.853519 | none |
| 2-6 | 24 | 24 | 0.0543948 | 0.376088 | 0.858558 | none |
| 3-1 | 25 | 25 | 0.0395956 | 0.305106 | 0.90691 | none |
| 3-2 | 25 | 25 | 0.0705697 | 0.514417 | 0.735375 | none |
| 3-3 | 25 | 25 | 0.0257304 | 0.178451 | 0.968155 | none |
| 3-4 | 25 | 25 | 0.0357144 | 0.357145 | 0.872448 | none |
| 3-5 | 25 | 25 | 0.0374569 | 0.301978 | 0.908809 | none |
| 3-6 | 24 | 24 | 0.0167325 | 0.107683 | 0.988404 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.78, 2.69, 2.69, 1.74, 1.67, 1.64, 1.51, 1.49, 1.37, 1.3, 1.2, 1.18, 1.11, 1.06, 1.04, 0.948, 0.885, 0.839, 0.838, 0.831, 0.759, 0.753, 0.742, 0.708, 0.667, 0.641, 0.605, 0.563, 0.554, 0.484, 0.442, 0.422, 0.421, 0.4, 0.387, 0.383, 0.354, 0.35, 0.346, 0.315, 0.308, 0.308, 0.291, 0.193, 0.166, 0.131, 0.13, 0.128, 0.119, 0.101, 0.1, 0.0965, 0.0895, 0.0876, 0.0832; rank 55 of 55.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferenceSindyThreshold test](plots/ReferenceSindyThreshold_test.png)

*Candidate ReferenceSindyThreshold, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferenceSindyThreshold; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferenceSindyThreshold train](plots/ReferenceSindyThreshold_train.png)

*Candidate ReferenceSindyThreshold, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferenceSindyThreshold; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
