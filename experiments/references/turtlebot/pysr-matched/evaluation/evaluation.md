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

Distinct structures: 5 among 5 evaluated candidates; groups: ReferencePysrMatchedS1; ReferencePysrMatchedS2; ReferencePysrMatchedS3; ReferencePysrMatchedS4; ReferencePysrMatchedS5. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

The agent recommends no candidate. Its reason: Reference models found by PySR without the agent, one per seed; none is recommended.
- Harness note: the agent recommends no candidate.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 5 eligible of 5 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (25 scored samples), test-2 (25 scored samples), test-3 (25 scored samples), test-4 (25 scored samples), test-5 (25 scored samples), test-6 (24 scored samples), test-7 (25 scored samples), test-8 (25 scored samples), test-9 (25 scored samples), test-10 (25 scored samples), test-11 (25 scored samples), test-12 (24 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (m) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | ReferencePysrMatchedS1 | 0.0437871 | none | none |
| 2 | ReferencePysrMatchedS5 | 0.0463674 | none | none |
| 3 | ReferencePysrMatchedS4 | 0.0530201 | none | none |
| 4 | ReferencePysrMatchedS3 | 0.0595408 | none | none |
| 5 | ReferencePysrMatchedS2 | 0.0761191 | none | none |

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

Output errors on the test data (sealed) (pooled RMSE: 0.0437871 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0233437 | 0.0833807 | 0.993048 | none |
| test-2 | 25 | 25 | 0.00733818 | 0.09582 | 0.990819 | none |
| test-3 | 25 | 25 | 0.0771489 | 0.527422 | 0.721826 | none |
| test-4 | 25 | 25 | 0.00537994 | 0.0357948 | 0.998719 | none |
| test-5 | 25 | 25 | 0.011972 | 0.0537079 | 0.997115 | none |
| test-6 | 24 | 24 | 0.01851 | 0.147182 | 0.978337 | none |
| test-7 | 25 | 25 | 0.0349493 | 0.377025 | 0.857852 | none |
| test-8 | 25 | 25 | 0.0419677 | 0.233004 | 0.945709 | none |
| test-9 | 25 | 25 | 0.0274355 | 0.207318 | 0.957019 | none |
| test-10 | 25 | 25 | 0.0143119 | 0.210729 | 0.955593 | none |
| test-11 | 25 | 25 | 0.102889 | 1.31562 | -0.730846 | none |
| test-12 | 24 | 24 | 0.0364556 | 0.273919 | 0.924968 | none |

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
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrMatchedS1 test](plots/ReferencePysrMatchedS1_test.png)

*Candidate ReferencePysrMatchedS1, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS1; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

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

Output errors on the test data (sealed) (pooled RMSE: 0.0761191 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0221388 | 0.0790768 | 0.993747 | none |
| test-2 | 25 | 25 | 0.0145692 | 0.190241 | 0.963808 | none |
| test-3 | 25 | 25 | 0.0702033 | 0.479939 | 0.769659 | none |
| test-4 | 25 | 25 | 0.0141608 | 0.0942175 | 0.991123 | none |
| test-5 | 25 | 25 | 0.0366948 | 0.164618 | 0.972901 | none |
| test-6 | 24 | 24 | 0.1687 | 1.34142 | -0.799407 | none |
| test-7 | 25 | 25 | 0.0212014 | 0.228716 | 0.947689 | none |
| test-8 | 25 | 25 | 0.0244539 | 0.135768 | 0.981567 | none |
| test-9 | 25 | 25 | 0.0392769 | 0.296798 | 0.911911 | none |
| test-10 | 25 | 25 | 0.0141545 | 0.20841 | 0.956565 | none |
| test-11 | 25 | 25 | 0.0911073 | 1.16496 | -0.357134 | none |
| test-12 | 24 | 24 | 0.156377 | 1.17498 | -0.380575 | none |

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
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrMatchedS2 test](plots/ReferencePysrMatchedS2_test.png)

*Candidate ReferencePysrMatchedS2, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS2; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

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

Output errors on the test data (sealed) (pooled RMSE: 0.0595408 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0197049 | 0.0703834 | 0.995046 | none |
| test-2 | 25 | 25 | 0.0289387 | 0.377873 | 0.857212 | none |
| test-3 | 25 | 25 | 0.0797838 | 0.545435 | 0.702501 | none |
| test-4 | 25 | 25 | 0.00450027 | 0.029942 | 0.999103 | none |
| test-5 | 25 | 25 | 0.010444 | 0.0468533 | 0.997805 | none |
| test-6 | 24 | 24 | 0.135083 | 1.07411 | -0.153712 | none |
| test-7 | 25 | 25 | 0.0543369 | 0.586175 | 0.656399 | none |
| test-8 | 25 | 25 | 0.0556035 | 0.30871 | 0.904698 | none |
| test-9 | 25 | 25 | 0.0345834 | 0.261331 | 0.931706 | none |
| test-10 | 25 | 25 | 0.00838805 | 0.123505 | 0.984746 | none |
| test-11 | 25 | 25 | 0.0798698 | 1.02127 | -0.0429938 | none |
| test-12 | 24 | 24 | 0.0588948 | 0.442523 | 0.804174 | none |

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
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrMatchedS3 test](plots/ReferencePysrMatchedS3_test.png)

*Candidate ReferencePysrMatchedS3, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS3; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

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

Output errors on the test data (sealed) (pooled RMSE: 0.0530201 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0272961 | 0.0974982 | 0.990494 | none |
| test-2 | 25 | 25 | 0.0153311 | 0.200189 | 0.959924 | none |
| test-3 | 25 | 25 | 0.0780455 | 0.533552 | 0.715323 | none |
| test-4 | 25 | 25 | 0.00324906 | 0.0216172 | 0.999533 | none |
| test-5 | 25 | 25 | 0.02051 | 0.0920106 | 0.991534 | none |
| test-6 | 24 | 24 | 0.0181954 | 0.144681 | 0.979067 | none |
| test-7 | 25 | 25 | 0.0118772 | 0.128128 | 0.983583 | none |
| test-8 | 25 | 25 | 0.0394604 | 0.219084 | 0.952002 | none |
| test-9 | 25 | 25 | 0.0394511 | 0.298115 | 0.911128 | none |
| test-10 | 25 | 25 | 0.00624294 | 0.0919209 | 0.991551 | none |
| test-11 | 25 | 25 | 0.109369 | 1.39847 | -0.955718 | none |
| test-12 | 24 | 24 | 0.10425 | 0.783309 | 0.386427 | none |

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
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrMatchedS4 test](plots/ReferencePysrMatchedS4_test.png)

*Candidate ReferencePysrMatchedS4, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS4; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

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

Output errors on the test data (sealed) (pooled RMSE: 0.0463674 m):

| trajectory | scored samples | completed | RMSE (m) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 25 | 25 | 0.0375319 | 0.134059 | 0.982028 | none |
| test-2 | 25 | 25 | 0.014199 | 0.185407 | 0.965624 | none |
| test-3 | 25 | 25 | 0.0803114 | 0.549042 | 0.698553 | none |
| test-4 | 25 | 25 | 0.00340784 | 0.0226737 | 0.999486 | none |
| test-5 | 25 | 25 | 0.00770661 | 0.0345728 | 0.998805 | none |
| test-6 | 24 | 24 | 0.0165897 | 0.131913 | 0.982599 | none |
| test-7 | 25 | 25 | 0.0236328 | 0.254945 | 0.935003 | none |
| test-8 | 25 | 25 | 0.0209666 | 0.116406 | 0.98645 | none |
| test-9 | 25 | 25 | 0.0318121 | 0.24039 | 0.942213 | none |
| test-10 | 25 | 25 | 0.00983812 | 0.144856 | 0.979017 | none |
| test-11 | 25 | 25 | 0.12142 | 1.55255 | -1.41043 | none |
| test-12 | 24 | 24 | 0.0199537 | 0.149928 | 0.977522 | none |

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
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![ReferencePysrMatchedS5 test](plots/ReferencePysrMatchedS5_test.png)

*Candidate ReferencePysrMatchedS5, test data (sealed), trajectories test-1, test-2, test-3, test-4, test-5, test-6, test-7, test-8, test-9, test-10, test-11, test-12. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS5; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 25; test-2: 1 to 25; test-3: 1 to 25; test-4: 1 to 25; test-5: 1 to 25; test-6: 1 to 24; test-7: 1 to 25; test-8: 1 to 25; test-9: 1 to 25; test-10: 1 to 25; test-11: 1 to 25; test-12: 1 to 24 (0-based sample indices). No numerical failure occurred.*

![ReferencePysrMatchedS5 train](plots/ReferencePysrMatchedS5_train.png)

*Candidate ReferencePysrMatchedS5, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output x (m) and model output of ReferencePysrMatchedS5; lower axes: residual (model output minus measured output, m). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
