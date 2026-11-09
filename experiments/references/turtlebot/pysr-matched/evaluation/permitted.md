# Evaluation results permitted to the agent: task turtlebot

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This view contains no result derived from sealed data.

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

Note: the categories overlap; the counts need not sum to the pool size.

Distinct structures: 5 among 5 evaluated candidates; groups: ReferencePysrMatchedS1; ReferencePysrMatchedS2; ReferencePysrMatchedS3; ReferencePysrMatchedS4; ReferencePysrMatchedS5. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

The agent recommends no candidate. Its reason: Reference models found by PySR without the agent, one per seed; none is recommended.
- Harness note: the agent recommends no candidate.

## Candidates

### Candidate ReferencePysrMatchedS1

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `x_next = ca1*v_f + ca2*cos(sign(y)) + ca3 + ca4*v_f*cos(phi) + ca5*x`
- `y_next = cb1*sin(phi) + y`
- `phi_next = cc1*exp(y*(cc2 + y)) + cc3*phi*x + cc3*exp(cc5*v_f) + cc4*v_a + phi`
Complexity: 11 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 47 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `x_next = P1 + P2*v_f + P3*cos(sign(y)) + P4*x + P5*v_f*cos(phi)`; `y_next = P6*sin(phi) + y`; `phi_next = P11*v_a + P7*exp(y*(P8 + y)) + P9*phi*x + P9*exp(P10*v_f) + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0265723 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0118382 | 0.232295 | 0.946039 | none |
| 1-2 | 25 | 25 | 0.0169709 | 0.220404 | 0.951422 | none |
| 1-3 | 25 | 25 | 0.0119745 | 0.132141 | 0.982539 | none |
| 1-4 | 25 | 25 | 0.00938968 | 0.188635 | 0.964417 | none |
| 1-5 | 25 | 25 | 0.0502187 | 0.336599 | 0.886701 | none |
| 1-6 | 24 | 24 | 0.0510553 | 1.40716 | -0.980107 | none |
| 2-1 | 25 | 25 | 0.0117168 | 0.124011 | 0.984621 | none |
| 2-2 | 25 | 25 | 0.0179634 | 0.175206 | 0.969303 | none |
| 2-3 | 25 | 25 | 0.0237134 | 0.345383 | 0.880711 | none |
| 2-4 | 25 | 25 | 0.0404118 | 0.313218 | 0.901894 | none |
| 2-5 | 25 | 25 | 0.0512702 | 0.28746 | 0.917367 | none |
| 2-6 | 24 | 24 | 0.0232977 | 0.161081 | 0.974053 | none |
| 3-1 | 25 | 25 | 0.00651595 | 0.050209 | 0.997479 | none |
| 3-2 | 25 | 25 | 0.0137644 | 0.100336 | 0.989933 | none |
| 3-3 | 25 | 25 | 0.00655429 | 0.0454567 | 0.997934 | none |
| 3-4 | 25 | 25 | 0.017675 | 0.17675 | 0.96876 | none |
| 3-5 | 25 | 25 | 0.0216319 | 0.174397 | 0.969586 | none |
| 3-6 | 24 | 24 | 0.00915507 | 0.0589181 | 0.996529 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.86, 1.6, 1.03, 1, 0.988, 0.913, 0.608, 0.559, 0.484, 0.439, 0.048; rank 11 of 11.

![ReferencePysrMatchedS1 train](plots/ReferencePysrMatchedS1_train.png)

*Candidate ReferencePysrMatchedS1, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS1; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrMatchedS2

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `x_next = ca1*cos(sin(ca6*exp(sin(x)))) + ca2*sin(ca5*cos(phi)*sqrt(Abs(x))) + ca3*v_f*cos(phi) + ca4*x`
- `y_next = cb1*phi + y`
- `phi_next = cc1*(cc5 - phi*(cc3*phi*v_f - y))*(cc4*y - phi*x) + cc2*v_a + phi`
Complexity: 12 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 62 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `x_next = P1*cos(sin(P2*exp(sin(x)))) + P3*sin(P4*cos(phi)*sqrt(Abs(x))) + P5*x + P6*v_f*cos(phi)`; `y_next = P7*phi + y`; `phi_next = P8*v_a + P9*(P10 - phi*(P11*phi*v_f - y))*(P12*y - phi*x) + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0233384 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.00785139 | 0.154063 | 0.976264 | none |
| 1-2 | 25 | 25 | 0.00880051 | 0.114294 | 0.986937 | none |
| 1-3 | 25 | 25 | 0.00636136 | 0.0701986 | 0.995072 | none |
| 1-4 | 25 | 25 | 0.0167805 | 0.337113 | 0.886355 | none |
| 1-5 | 25 | 25 | 0.0148706 | 0.0996727 | 0.990065 | none |
| 1-6 | 24 | 24 | 0.024707 | 0.680963 | 0.53629 | none |
| 2-1 | 25 | 25 | 0.0180861 | 0.191424 | 0.963357 | none |
| 2-2 | 25 | 25 | 0.00435537 | 0.0424801 | 0.998195 | none |
| 2-3 | 25 | 25 | 0.0359157 | 0.523107 | 0.726359 | none |
| 2-4 | 25 | 25 | 0.0260381 | 0.201813 | 0.959272 | none |
| 2-5 | 25 | 25 | 0.0648931 | 0.363841 | 0.86762 | none |
| 2-6 | 24 | 24 | 0.0162211 | 0.112154 | 0.987422 | none |
| 3-1 | 25 | 25 | 0.0134688 | 0.103785 | 0.989229 | none |
| 3-2 | 25 | 25 | 0.00850476 | 0.0619953 | 0.996157 | none |
| 3-3 | 25 | 25 | 0.0103899 | 0.0720583 | 0.994808 | none |
| 3-4 | 25 | 25 | 0.0209547 | 0.209547 | 0.95609 | none |
| 3-5 | 25 | 25 | 0.00935876 | 0.0754505 | 0.994307 | none |
| 3-6 | 24 | 24 | 0.0289486 | 0.186301 | 0.965292 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.62, 1.48, 1.15, 1.06, 1, 0.998, 0.977, 0.869, 0.739, 0.449, 0.413, 0.34; rank 12 of 12.

![ReferencePysrMatchedS2 train](plots/ReferencePysrMatchedS2_train.png)

*Candidate ReferencePysrMatchedS2, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS2; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrMatchedS3

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `x_next = ca1 + ca4*tanh(Abs(ca2*sin(y) + ca7*x)**(1/4)) + ca6*x + (ca3 + ca5*v_f)*cos(phi)`
- `y_next = cb1*sin(phi) + y`
- `phi_next = cc1*y*(y + (cc2 + y)*(cc6*phi - v_f)) + cc3*phi*(cc5 + x) + cc4*v_a + phi`
Complexity: 14 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 60 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `x_next = P1 + P2*tanh(Abs(P3*sin(y) + P4*x)**(1/4)) + P5*x + (P6 + P7*v_f)*cos(phi)`; `y_next = P8*sin(phi) + y`; `phi_next = P10*y*(y + (P11 + y)*(P12*phi - v_f)) + P13*phi*(P14 + x) + P9*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0268559 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.00601163 | 0.117963 | 0.986085 | none |
| 1-2 | 25 | 25 | 0.0118689 | 0.154144 | 0.97624 | none |
| 1-3 | 25 | 25 | 0.00668527 | 0.073773 | 0.994558 | none |
| 1-4 | 25 | 25 | 0.0386978 | 0.777422 | 0.395614 | none |
| 1-5 | 25 | 25 | 0.0273264 | 0.183159 | 0.966453 | none |
| 1-6 | 24 | 24 | 0.0399126 | 1.10005 | -0.210116 | none |
| 2-1 | 25 | 25 | 0.00960819 | 0.101694 | 0.989658 | none |
| 2-2 | 25 | 25 | 0.0400589 | 0.390714 | 0.847342 | none |
| 2-3 | 25 | 25 | 0.0227155 | 0.330848 | 0.89054 | none |
| 2-4 | 25 | 25 | 0.0364032 | 0.282149 | 0.920392 | none |
| 2-5 | 25 | 25 | 0.0564734 | 0.316633 | 0.899743 | none |
| 2-6 | 24 | 24 | 0.0254094 | 0.175681 | 0.969136 | none |
| 3-1 | 25 | 25 | 0.00533725 | 0.0411265 | 0.998309 | none |
| 3-2 | 25 | 25 | 0.014373 | 0.104772 | 0.989023 | none |
| 3-3 | 25 | 25 | 0.0102684 | 0.0712156 | 0.994928 | none |
| 3-4 | 25 | 25 | 0.0136674 | 0.136674 | 0.98132 | none |
| 3-5 | 25 | 25 | 0.0163464 | 0.131785 | 0.982633 | none |
| 3-6 | 24 | 24 | 0.0281131 | 0.180924 | 0.967266 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1338 rows, 3 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.78, 1.78, 1.43, 1.14, 1.12, 1, 0.946, 0.61, 0.563, 0.526, 0.379, 0.315, 0.0221, 0.00363; rank 14 of 14.

![ReferencePysrMatchedS3 train](plots/ReferencePysrMatchedS3_train.png)

*Candidate ReferencePysrMatchedS3, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS3; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrMatchedS4

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `x_next = ca1 + ca3*x + ca3*tanh(v_f)*tanh(sin(ca2*exp(Abs(sign(x)))*cos(phi)))`
- `y_next = cb1*sin(phi) + y`
- `phi_next = (cc1*y**2 + cc2 + cc3*x*(phi - cos(phi*x)) + cc4*v_a + phi)*sign(Abs(x))`
Complexity: 8 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 51 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `x_next = P1 + P2*x + P2*tanh(v_f)*tanh(sin(P3*exp(Abs(sign(x)))*cos(phi)))`; `y_next = P4*sin(phi) + y`; `phi_next = (P5 + P6*y**2 + P7*v_a + P8*x*(phi - cos(phi*x)) + phi)*sign(Abs(x))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.031345 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.00433675 | 0.0850978 | 0.992758 | none |
| 1-2 | 25 | 25 | 0.0194746 | 0.25292 | 0.936031 | none |
| 1-3 | 25 | 25 | 0.0152619 | 0.168417 | 0.971636 | none |
| 1-4 | 25 | 25 | 0.0107147 | 0.215255 | 0.953665 | none |
| 1-5 | 25 | 25 | 0.0469291 | 0.314549 | 0.901059 | none |
| 1-6 | 24 | 24 | 0.0495098 | 1.36457 | -0.862038 | none |
| 2-1 | 25 | 25 | 0.0368781 | 0.390319 | 0.847651 | none |
| 2-2 | 25 | 25 | 0.0189973 | 0.18529 | 0.965668 | none |
| 2-3 | 25 | 25 | 0.0219636 | 0.319897 | 0.897666 | none |
| 2-4 | 25 | 25 | 0.0724007 | 0.561154 | 0.685107 | none |
| 2-5 | 25 | 25 | 0.0539828 | 0.302669 | 0.908391 | none |
| 2-6 | 24 | 24 | 0.0228474 | 0.157968 | 0.975046 | none |
| 3-1 | 25 | 25 | 0.00720399 | 0.0555107 | 0.996919 | none |
| 3-2 | 25 | 25 | 0.014317 | 0.104363 | 0.989108 | none |
| 3-3 | 25 | 25 | 0.00818756 | 0.0567841 | 0.996776 | none |
| 3-4 | 25 | 25 | 0.0287367 | 0.287367 | 0.91742 | none |
| 3-5 | 25 | 25 | 0.0135101 | 0.108919 | 0.988137 | none |
| 3-6 | 24 | 24 | 0.00873736 | 0.0562299 | 0.996838 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.4, 1.31, 1, 0.997, 0.971, 0.861, 0.591, 0.537; rank 8 of 8.

![ReferencePysrMatchedS4 train](plots/ReferencePysrMatchedS4_train.png)

*Candidate ReferencePysrMatchedS4, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS4; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate ReferencePysrMatchedS5

Position in the agent's order: 5. Status: evaluated.
File and expression checks: passed.
- `x_next = ca1 + ca2*v_f*cos(ca3*sign(v_a*x) + phi)/(ca4 - cos(sign(y))) + ca5*x`
- `y_next = cb1*phi + y`
- `phi_next = cc1*Abs(y) + cc2 + cc3*phi*tanh(x - sin(x*(cc5 + phi + x))) + cc4*v_a + phi`
Complexity: 11 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 56 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 5: `x_next = P1 + P2*x + P3*v_f*cos(P5*sign(v_a*x) + phi)/(P4 - cos(sign(y)))`; `y_next = P6*phi + y`; `phi_next = P10*phi*tanh(x - sin(x*(P11 + phi + x))) + P7 + P8*Abs(y) + P9*v_a + phi`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0235214 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.00960799 | 0.188532 | 0.964456 | none |
| 1-2 | 25 | 25 | 0.0187678 | 0.243741 | 0.94059 | none |
| 1-3 | 25 | 25 | 0.0214756 | 0.236987 | 0.943837 | none |
| 1-4 | 25 | 25 | 0.00851178 | 0.170998 | 0.97076 | none |
| 1-5 | 25 | 25 | 0.0358323 | 0.240172 | 0.942318 | none |
| 1-6 | 24 | 24 | 0.0091051 | 0.25095 | 0.937024 | none |
| 2-1 | 25 | 25 | 0.0156235 | 0.16536 | 0.972656 | none |
| 2-2 | 25 | 25 | 0.00869846 | 0.0848405 | 0.992802 | none |
| 2-3 | 25 | 25 | 0.0297504 | 0.433311 | 0.812242 | none |
| 2-4 | 25 | 25 | 0.00974703 | 0.0755459 | 0.994293 | none |
| 2-5 | 25 | 25 | 0.0352415 | 0.197591 | 0.960958 | none |
| 2-6 | 24 | 24 | 0.0233372 | 0.161355 | 0.973965 | none |
| 3-1 | 25 | 25 | 0.00851857 | 0.0656403 | 0.995691 | none |
| 3-2 | 25 | 25 | 0.00936456 | 0.0682628 | 0.99534 | none |
| 3-3 | 25 | 25 | 0.00801721 | 0.0556027 | 0.996908 | none |
| 3-4 | 25 | 25 | 0.0374741 | 0.374742 | 0.859569 | none |
| 3-5 | 25 | 25 | 0.0159874 | 0.128891 | 0.983387 | none |
| 3-6 | 24 | 24 | 0.0520557 | 0.335008 | 0.887769 | none |

Sensitivity rank test (diagnostic; never excludes): targets x_next, y_next, phi_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.64, 1.42, 1.05, 1.03, 1, 0.975, 0.946, 0.864, 0.551, 0.491, 0.0184; rank 11 of 11.

![ReferencePysrMatchedS5 train](plots/ReferencePysrMatchedS5_train.png)

*Candidate ReferencePysrMatchedS5, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS5; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
