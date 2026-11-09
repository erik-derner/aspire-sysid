# Evaluation results permitted to the agent: task task-kt5o

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This view contains no result derived from sealed data.

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

Note: the categories overlap; the counts need not sum to the pool size.

Distinct structures: 4 among 4 evaluated candidates; groups: CoupledDeadzone; SmoothAngular; AbsoluteCoupling; LinearKinematic. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: CoupledDeadzone. The agent's reason: `CoupledDeadzone` has the lowest pooled leave-one-trajectory-out free-running `y` RMSE among the retained structurally different families: `0.115160` versus `0.127536` for `SmoothAngular`, `0.142038` for `AbsoluteCoupling` and `0.212931` for `LinearKinematic`, all in unspecified `y` units on the three training trajectories. The nonlinear coupled-input response is supported by residual structure and its static-map regularization limits path-specific fitting. `SmoothAngular` fits training paths better and remains a useful alternative. With only three validation trajectories and apparent missing input memory, the ranking is uncertain and is not a claim about unavailable test performance.

## Candidates

### Candidate CoupledDeadzone

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (a*(sign(x3+l*x4)*Max(Abs(x3+l*x4)-d,0)+sign(x3-l*x4)*Max(Abs(x3-l*x4)-d,0))/2)*cos(x2+m*(c*(sign(x3+l*x4)*Max(Abs(x3+l*x4)-d,0)-sign(x3-l*x4)*Max(Abs(x3-l*x4)-d,0))+e))`
- `x1_next = x1 + (a*(sign(x3+l*x4)*Max(Abs(x3+l*x4)-d,0)+sign(x3-l*x4)*Max(Abs(x3-l*x4)-d,0))/2)*sin(x2+m*(c*(sign(x3+l*x4)*Max(Abs(x3+l*x4)-d,0)-sign(x3-l*x4)*Max(Abs(x3-l*x4)-d,0))+e))`
- `x2_next = atan2(sin(x2+(c*(sign(x3+l*x4)*Max(Abs(x3+l*x4)-d,0)-sign(x3-l*x4)*Max(Abs(x3-l*x4)-d,0))+e)),cos(x2+(c*(sign(x3+l*x4)*Max(Abs(x3+l*x4)-d,0)-sign(x3-l*x4)*Max(Abs(x3-l*x4)-d,0))+e)))`
Complexity: 6 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 297 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `y_next = P1*(sign(-P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 - x3)) + sign(P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 + x3)))*cos(P4*(P5 + P6*(-sign(-P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 - x3)) + sign(P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 + x3)))) + x2)/2 + y`; `x1_next = P1*(sign(-P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 - x3)) + sign(P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 + x3)))*sin(P4*(P5 + P6*(-sign(-P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 - x3)) + sign(P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 + x3)))) + x2)/2 + x1`; `x2_next = atan2(sin(P5 + P6*(-sign(-P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 - x3)) + sign(P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 + x3))) + x2), cos(P5 + P6*(-sign(-P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 - x3)) + sign(P3*x4 + x3)*Max(0, -P2 + Abs(P3*x4 + x3))) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0411824 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0332407 | 0.652263 | 0.574552 | none |
| 1-2 | 25 | 25 | 0.00533323 | 0.0692635 | 0.995203 | none |
| 1-3 | 25 | 25 | 0.0132138 | 0.145816 | 0.978738 | none |
| 1-4 | 25 | 25 | 0.0701187 | 1.40866 | -0.984313 | none |
| 1-5 | 25 | 25 | 0.0482247 | 0.323234 | 0.89552 | none |
| 1-6 | 24 | 24 | 0.0414113 | 1.14136 | -0.3027 | none |
| 2-1 | 25 | 25 | 0.0287118 | 0.303887 | 0.907652 | none |
| 2-2 | 25 | 25 | 0.0255949 | 0.24964 | 0.93768 | none |
| 2-3 | 25 | 25 | 0.0315535 | 0.459573 | 0.788792 | none |
| 2-4 | 25 | 25 | 0.0597023 | 0.462732 | 0.785879 | none |
| 2-5 | 25 | 25 | 0.0658145 | 0.369007 | 0.863834 | none |
| 2-6 | 24 | 24 | 0.0459171 | 0.317473 | 0.899211 | none |
| 3-1 | 25 | 25 | 0.0441496 | 0.340197 | 0.884266 | none |
| 3-2 | 25 | 25 | 0.00833719 | 0.0607739 | 0.996307 | none |
| 3-3 | 25 | 25 | 0.00729863 | 0.050619 | 0.997438 | none |
| 3-4 | 25 | 25 | 0.0511179 | 0.51118 | 0.738695 | none |
| 3-5 | 25 | 25 | 0.0475862 | 0.383641 | 0.85282 | none |
| 3-6 | 24 | 24 | 0.0285625 | 0.183816 | 0.966212 | none |

- Failed computation (sensitivity rank test): NameError: name 'DiracDelta' is not defined

![CoupledDeadzone train](plots/CoupledDeadzone_train.png)

*Candidate CoupledDeadzone, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of CoupledDeadzone; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate SmoothAngular

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (a*x3+b)*cos(x2+m*(c*x4-d*tanh(x4/s)+e))`
- `x1_next = x1 + (a*x3+b)*sin(x2+m*(c*x4-d*tanh(x4/s)+e))`
- `x2_next = atan2(sin(x2+(c*x4-d*tanh(x4/s)+e)),cos(x2+(c*x4-d*tanh(x4/s)+e)))`
Complexity: 7 fitted, 0 fixed and 0 tied parameters; 0 non-integer numeric literals; 87 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `y_next = y + (P1 + P2*x3)*cos(P3*(P4 + P5*x4 - P6*tanh(x4/P7)) + x2)`; `x1_next = x1 + (P1 + P2*x3)*sin(P3*(P4 + P5*x4 - P6*tanh(x4/P7)) + x2)`; `x2_next = atan2(sin(P4 + P5*x4 - P6*tanh(x4/P7) + x2), cos(P4 + P5*x4 - P6*tanh(x4/P7) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0391632 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0304769 | 0.598033 | 0.642357 | none |
| 1-2 | 25 | 25 | 0.00642591 | 0.0834545 | 0.993035 | none |
| 1-3 | 25 | 25 | 0.0495751 | 0.547069 | 0.700715 | none |
| 1-4 | 25 | 25 | 0.0448668 | 0.901356 | 0.187558 | none |
| 1-5 | 25 | 25 | 0.0287626 | 0.192785 | 0.962834 | none |
| 1-6 | 24 | 24 | 0.038275 | 1.05492 | -0.112853 | none |
| 2-1 | 25 | 25 | 0.0245889 | 0.26025 | 0.93227 | none |
| 2-2 | 25 | 25 | 0.0170378 | 0.166178 | 0.972385 | none |
| 2-3 | 25 | 25 | 0.00591181 | 0.0861048 | 0.992586 | none |
| 2-4 | 25 | 25 | 0.0689776 | 0.534622 | 0.714179 | none |
| 2-5 | 25 | 25 | 0.0492056 | 0.275885 | 0.923888 | none |
| 2-6 | 24 | 24 | 0.0506637 | 0.350291 | 0.877296 | none |
| 3-1 | 25 | 25 | 0.0409114 | 0.315245 | 0.90062 | none |
| 3-2 | 25 | 25 | 0.00918378 | 0.066945 | 0.995518 | none |
| 3-3 | 25 | 25 | 0.0159021 | 0.110287 | 0.987837 | none |
| 3-4 | 25 | 25 | 0.0459811 | 0.459811 | 0.788574 | none |
| 3-5 | 25 | 25 | 0.0643078 | 0.51845 | 0.731209 | none |
| 3-6 | 24 | 24 | 0.0308774 | 0.198714 | 0.960513 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.42, 1.36, 1, 1, 0.962, 0.387, 0.248; rank 7 of 7.

![SmoothAngular train](plots/SmoothAngular_train.png)

*Candidate SmoothAngular, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of SmoothAngular; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate AbsoluteCoupling

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (a*x3+b)*cos(x2+m*(c*x4+d*(Abs(x3-l*x4)-Abs(x3+l*x4))+e))`
- `x1_next = x1 + (a*x3+b)*sin(x2+m*(c*x4+d*(Abs(x3-l*x4)-Abs(x3+l*x4))+e))`
- `x2_next = atan2(sin(x2+(c*x4+d*(Abs(x3-l*x4)-Abs(x3+l*x4))+e)),cos(x2+(c*x4+d*(Abs(x3-l*x4)-Abs(x3+l*x4))+e)))`
Complexity: 7 fitted, 1 fixed and 1 tied parameters; 0 non-integer numeric literals; 127 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `y_next = y + (P1 + P2*x3)*cos(x2 + (P3 - P4)*(P5 + P6*x4 + P7*(Abs(x3 - 0.10000000000000001*x4) - Abs(x3 + 0.10000000000000001*x4))))`; `x1_next = x1 + (P1 + P2*x3)*sin(x2 + (P3 - P4)*(P5 + P6*x4 + P7*(Abs(x3 - 0.10000000000000001*x4) - Abs(x3 + 0.10000000000000001*x4))))`; `x2_next = atan2(sin(P5 + P6*x4 + P7*(Abs(x3 - 0.10000000000000001*x4) - Abs(x3 + 0.10000000000000001*x4)) + x2), cos(P5 + P6*x4 + P7*(Abs(x3 - 0.10000000000000001*x4) - Abs(x3 + 0.10000000000000001*x4)) + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0424509 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0388699 | 0.762723 | 0.418254 | none |
| 1-2 | 25 | 25 | 0.00355779 | 0.0462056 | 0.997865 | none |
| 1-3 | 25 | 25 | 0.0112554 | 0.124205 | 0.984573 | none |
| 1-4 | 25 | 25 | 0.072421 | 1.45491 | -1.11675 | none |
| 1-5 | 25 | 25 | 0.047702 | 0.31973 | 0.897773 | none |
| 1-6 | 24 | 24 | 0.0426908 | 1.17662 | -0.384445 | none |
| 2-1 | 25 | 25 | 0.0357695 | 0.378586 | 0.856672 | none |
| 2-2 | 25 | 25 | 0.0241549 | 0.235595 | 0.944495 | none |
| 2-3 | 25 | 25 | 0.0256067 | 0.372958 | 0.860903 | none |
| 2-4 | 25 | 25 | 0.062927 | 0.487726 | 0.762123 | none |
| 2-5 | 25 | 25 | 0.0711582 | 0.398967 | 0.840825 | none |
| 2-6 | 24 | 24 | 0.0382628 | 0.264551 | 0.930013 | none |
| 3-1 | 25 | 25 | 0.0491148 | 0.378457 | 0.856771 | none |
| 3-2 | 25 | 25 | 0.0163364 | 0.119084 | 0.985819 | none |
| 3-3 | 25 | 25 | 0.0170166 | 0.118017 | 0.986072 | none |
| 3-4 | 25 | 25 | 0.0533183 | 0.533183 | 0.715716 | none |
| 3-5 | 25 | 25 | 0.0387053 | 0.312043 | 0.902629 | none |
| 3-6 | 24 | 24 | 0.0329782 | 0.212234 | 0.954957 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.42, 1.4, 1.36, 0.992, 0.387, 0.154, 3.34e-16; rank 6 of 7.
- Locally indistinguishable combination: arc (+0.707), delay (+0.707); relative singular value 2.35e-16.

![AbsoluteCoupling train](plots/AbsoluteCoupling_train.png)

*Candidate AbsoluteCoupling, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of AbsoluteCoupling; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*

### Candidate LinearKinematic

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `y_next = y + (a*x3+b)*cos(x2+m*(c*x4+d))`
- `x1_next = x1 + (a*x3+b)*sin(x2+m*(c*x4+d))`
- `x2_next = atan2(sin(x2+(c*x4+d)),cos(x2+(c*x4+d)))`
Complexity: 5 fitted, 1 fixed and 1 tied parameters; 0 non-integer numeric literals; 51 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `y_next = y + (P1 + P2*x3)*cos(x2 + (0.45000000000000001 - P3)*(P4 + P5*x4))`; `x1_next = x1 + (P1 + P2*x3)*sin(x2 + (0.45000000000000001 - P3)*(P4 + P5*x4))`; `x2_next = atan2(sin(P4 + P5*x4 + x2), cos(P4 + P5*x4 + x2))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|

Output errors on the training data (pooled RMSE: 0.0447348 not supplied):

| trajectory | scored samples | completed | RMSE (not supplied) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1-1 | 25 | 25 | 0.0344683 | 0.676352 | 0.542548 | none |
| 1-2 | 25 | 25 | 0.00395793 | 0.0514023 | 0.997358 | none |
| 1-3 | 25 | 25 | 0.0144477 | 0.159433 | 0.974581 | none |
| 1-4 | 25 | 25 | 0.0700614 | 1.4075 | -0.981067 | none |
| 1-5 | 25 | 25 | 0.0506973 | 0.339807 | 0.884532 | none |
| 1-6 | 24 | 24 | 0.0649717 | 1.79072 | -2.20668 | none |
| 2-1 | 25 | 25 | 0.040405 | 0.427648 | 0.817117 | none |
| 2-2 | 25 | 25 | 0.0232742 | 0.227005 | 0.948469 | none |
| 2-3 | 25 | 25 | 0.030215 | 0.440077 | 0.806332 | none |
| 2-4 | 25 | 25 | 0.0670488 | 0.519673 | 0.72994 | none |
| 2-5 | 25 | 25 | 0.0691111 | 0.38749 | 0.849852 | none |
| 2-6 | 24 | 24 | 0.0369695 | 0.255609 | 0.934664 | none |
| 3-1 | 25 | 25 | 0.0508813 | 0.392069 | 0.846282 | none |
| 3-2 | 25 | 25 | 0.0155668 | 0.113474 | 0.987124 | none |
| 3-3 | 25 | 25 | 0.017245 | 0.119601 | 0.985696 | none |
| 3-4 | 25 | 25 | 0.0574428 | 0.574428 | 0.670032 | none |
| 3-5 | 25 | 25 | 0.0393717 | 0.317415 | 0.899248 | none |
| 3-6 | 24 | 24 | 0.0351795 | 0.2264 | 0.948743 | none |

Sensitivity rank test (diagnostic; never excludes): targets y_next, x1_next, x2_next on the train data (1341 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.36, 1.05, 1, 0.952, 0.387; rank 5 of 5.

![LinearKinematic train](plots/LinearKinematic_train.png)

*Candidate LinearKinematic, training data, trajectories 1-1, 1-2, 1-3, 1-4, 1-5, 1-6, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 3-1, 3-2, 3-3, 3-4, 3-5, 3-6. Upper axes: measured output y (not supplied) and model output of LinearKinematic; lower axes: residual (model output minus measured output, not supplied). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; the state-update equation at the sampling period T_s = 0.2 s; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1-1: 1 to 25; 1-2: 1 to 25; 1-3: 1 to 25; 1-4: 1 to 25; 1-5: 1 to 25; 1-6: 1 to 24; 2-1: 1 to 25; 2-2: 1 to 25; 2-3: 1 to 25; 2-4: 1 to 25; 2-5: 1 to 25; 2-6: 1 to 24; 3-1: 1 to 25; 3-2: 1 to 25; 3-3: 1 to 25; 3-4: 1 to 25; 3-5: 1 to 25; 3-6: 1 to 24 (0-based sample indices). No numerical failure occurred.*
