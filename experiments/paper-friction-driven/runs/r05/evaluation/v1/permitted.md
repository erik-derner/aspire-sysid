# Evaluation results permitted to the agent: task friction-driven

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This view contains no result derived from sealed data.

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
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |

Note: the categories overlap; the counts need not sum to the pool size.

Distinct structures: 3 among 3 evaluated candidates; groups: BlendedStiction; ProjectedFriction; KarnoppBand. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: BlendedStiction. The agent's reason: Recommended for exact resting force cancellation, continuous low-speed dynamics and the best final all-data angle fit: training RMSE `0.04552` rad and reused-validation RMSE `0.07699` rad. The independent audit excluded training tails of validation recordings: blended and Karnopp validation RMSEs were nearly tied (`0.08554` rad versus `0.08520` rad), while projection gave `0.08963` rad. Thus the recommendation also rests on avoiding Karnopp discontinuous mode switches, not on claiming a decisive independent validation win. All three satisfy the requirements analytically and in the recorded sampled checks. Test data were not accessed.
- Harness note: the recommendation involves unresolved formal requirement(s) R2, R3, for human assessment.

## Candidates

### Candidate BlendedStiction

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `dtheta = omega`
- `domega = (a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp*cos(theta))-exp(-(omega/v)**2)*Min(Max((a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp*cos(theta)),-(f*(1+h*cos(theta)))),(f*(1+h*cos(theta))))-(1-exp(-(omega/v)**2))*(f*(1+h*cos(theta)))*tanh(omega/e)-k*omega*exp(-(omega/v)**2)`
Complexity: 10 fitted, 0 fixed and 1 tied parameters; 0 non-integer numeric literals; 118 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `dtheta = omega`; `domega = P1*u - P2*omega + P3*P7*(1 - Abs(P4))*cos(theta) - P3*(1 - exp(-omega**2/P8**2))*(P4*cos(theta) + 1)*tanh(omega/P10) - P5*(P6*cos(theta) + 1)*sin(theta) - P9*omega*exp(-omega**2/P8**2) - exp(-omega**2/P8**2)*Min(P3*(P4*cos(theta) + 1), Max(-P3*(P4*cos(theta) + 1), P1*u - P2*omega + P3*P7*(1 - Abs(P4))*cos(theta) - P5*(P6*cos(theta) + 1)*sin(theta)))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | equation | proof | satisfied | evaluation of a constant | the quantity is identically zero on the domain |
| R2 | inequality | inconclusive | unresolved | SymPy simplification and extremum then sampling (10000 points, seed 20261009) | no violation found at the 10000 sampled points (largest value of Q -0.0, tolerance 0.0); this is not a proof |
| R3 | monotonicity | inconclusive | unresolved | interval arithmetic and symbolic simplification then sampling (10000 points, seed 20261009) | no violation found at the 10000 sampled points (largest value of Q -0.12897860127838, tolerance 0.0); this is not a proof |

Output errors on the training data (pooled RMSE: 0.0455211 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0262483 | 0.102341 | 0.989526 | none |
| 2 | 449 | 449 | 0.0376887 | 0.0565511 | 0.996802 | none |
| 3 | 299 | 299 | 0.0792865 | 0.167883 | 0.971815 | none |
| 4 | 299 | 299 | 0.0532727 | 0.0650036 | 0.995775 | none |
| 5 | 441 | 441 | 0.0357658 | 0.0934436 | 0.991268 | none |
| 6 | 441 | 441 | 0.0389928 | 0.0854281 | 0.992702 | none |
| 7 | 441 | 441 | 0.0480607 | 0.092631 | 0.991419 | none |
| 8 | 140 | 140 | 0.0798112 | 0.485995 | 0.763808 | none |
| 9 | 140 | 140 | 0.0230925 | 0.105596 | 0.988849 | none |
| 10 | 140 | 140 | 0.0141238 | 0.287252 | 0.917486 | none |
| 11 | 90 | 90 | 0.0215345 | 0.130843 | 0.98288 | none |
| 12 | 90 | 90 | 0.00181204 | 0.355148 | 0.87387 | none |
| 13 | 90 | 90 | 0.0583356 | 0.107375 | 0.988471 | none |

Output errors on the validation data (pooled RMSE: 0.0769901 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0976385 | 0.178573 | 0.968112 | none |
| 2 | 299 | 299 | 0.0535464 | 0.0957689 | 0.990828 | none |
| 3 | 441 | 441 | 0.0658112 | 0.175096 | 0.969341 | none |

Sensitivity rank test (diagnostic; never excludes): targets domega on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.71, 1.37, 1.29, 1.01, 0.943, 0.82, 0.644, 0.518, 0.438, 0.288; rank 10 of 10.

![BlendedStiction train](plots/BlendedStiction_train.png)

*Candidate BlendedStiction, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output theta (rad) and model output of BlendedStiction; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![BlendedStiction val](plots/BlendedStiction_val.png)

*Candidate BlendedStiction, validation data, trajectories 1, 2, 3. Upper axes: measured output theta (rad) and model output of BlendedStiction; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate ProjectedFriction

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `dtheta = omega`
- `domega = (a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp*cos(theta))-Min(Max((a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp*cos(theta))+k*omega,-(f*(1+h*cos(theta)))),(f*(1+h*cos(theta))))`
Complexity: 8 fitted, 0 fixed and 1 tied parameters; 0 non-integer numeric literals; 71 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `dtheta = omega`; `domega = P1*P8*(1 - Abs(P2))*cos(theta) + P3*u - P5*omega - P6*(P7*cos(theta) + 1)*sin(theta) - Min(P1*(P2*cos(theta) + 1), Max(-P1*(P2*cos(theta) + 1), P1*P8*(1 - Abs(P2))*cos(theta) + P3*u + P4*omega - P5*omega - P6*(P7*cos(theta) + 1)*sin(theta)))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | equation | proof | satisfied | evaluation of a constant | the quantity is identically zero on the domain |
| R2 | inequality | inconclusive | unresolved | SymPy simplification and extremum then sampling (10000 points, seed 20261009) | no violation found at the 10000 sampled points (largest value of Q -0.0, tolerance 0.0); this is not a proof |
| R3 | monotonicity | inconclusive | unresolved | interval arithmetic and symbolic simplification then sampling (10000 points, seed 20261009) | no violation found at the 10000 sampled points (largest value of Q 0.0, tolerance 0.0); this is not a proof |

Output errors on the training data (pooled RMSE: 0.0473935 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0246398 | 0.0960699 | 0.990771 | none |
| 2 | 449 | 449 | 0.0365476 | 0.0548388 | 0.996993 | none |
| 3 | 299 | 299 | 0.0884713 | 0.187331 | 0.964907 | none |
| 4 | 299 | 299 | 0.0472986 | 0.057714 | 0.996669 | none |
| 5 | 441 | 441 | 0.0305106 | 0.0797137 | 0.993646 | none |
| 6 | 441 | 441 | 0.0382782 | 0.0838625 | 0.992967 | none |
| 7 | 441 | 441 | 0.0440061 | 0.0848163 | 0.992806 | none |
| 8 | 140 | 140 | 0.109027 | 0.663898 | 0.55924 | none |
| 9 | 140 | 140 | 0.0140569 | 0.0642785 | 0.995868 | none |
| 10 | 140 | 140 | 0.00591741 | 0.120349 | 0.985516 | none |
| 11 | 90 | 90 | 0.0298329 | 0.181264 | 0.967143 | none |
| 12 | 90 | 90 | 0.00771111 | 1.51133 | -1.28411 | none |
| 13 | 90 | 90 | 0.0584317 | 0.107552 | 0.988433 | none |

Output errors on the validation data (pooled RMSE: 0.0812517 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.103711 | 0.189679 | 0.964022 | none |
| 2 | 299 | 299 | 0.0574708 | 0.102788 | 0.989435 | none |
| 3 | 441 | 441 | 0.0678903 | 0.180628 | 0.967374 | none |

Sensitivity rank test (diagnostic; never excludes): targets domega on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.68, 1.33, 1, 1, 0.817, 0.648, 0.499, 0.275; rank 8 of 8.

![ProjectedFriction train](plots/ProjectedFriction_train.png)

*Candidate ProjectedFriction, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output theta (rad) and model output of ProjectedFriction; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![ProjectedFriction val](plots/ProjectedFriction_val.png)

*Candidate ProjectedFriction, validation data, trajectories 1, 2, 3. Upper axes: measured output theta (rad) and model output of ProjectedFriction; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*

### Candidate KarnoppBand

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `dtheta = omega`
- `domega = Piecewise(((a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp)-f*sign(omega), (Abs(omega) > v)), (Max((a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp)-f,0)+Min((a*u-b*omega-c*sin(theta)*(1+j*cos(theta))+biasAmp)+f,0)-k*omega, True))`
Complexity: 8 fitted, 0 fixed and 1 tied parameters; 0 non-integer numeric literals; 85 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `dtheta = omega`; `domega = Piecewise((P1*u + P2*P3 - P2*sign(omega) - P4*omega - P5*(P6*cos(theta) + 1)*sin(theta), P7 < Abs(omega)), (-P8*omega + Max(0, P1*u + P2*P3 - P2 - P4*omega - P5*(P6*cos(theta) + 1)*sin(theta)) + Min(0, P1*u + P2*P3 + P2 - P4*omega - P5*(P6*cos(theta) + 1)*sin(theta)), True))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | equation | proof | satisfied | evaluation of a constant | the quantity is identically zero on the domain |
| R2 | inequality | proof | satisfied | interval arithmetic (branch and bound) | verified enclosures on 3 sub-box(es) covering the domain do not exceed the tolerance 0.0 |
| R3 | monotonicity | inconclusive | unresolved | interval arithmetic and symbolic simplification then sampling (10000 points, seed 20261009) | no violation found at the 10000 sampled points (largest value of Q -0.0, tolerance 0.0); this is not a proof |

Output errors on the training data (pooled RMSE: 0.0557296 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.0445153 | 0.173564 | 0.969876 | none |
| 2 | 449 | 449 | 0.0339931 | 0.0510059 | 0.997398 | none |
| 3 | 299 | 299 | 0.0865672 | 0.183299 | 0.966401 | none |
| 4 | 299 | 299 | 0.0514081 | 0.0627284 | 0.996065 | none |
| 5 | 441 | 441 | 0.0213279 | 0.0557225 | 0.996895 | none |
| 6 | 441 | 441 | 0.0390176 | 0.0854823 | 0.992693 | none |
| 7 | 441 | 441 | 0.0872025 | 0.168072 | 0.971752 | none |
| 8 | 140 | 140 | 0.114722 | 0.698575 | 0.511992 | none |
| 9 | 140 | 140 | 0.028226 | 0.12907 | 0.983341 | none |
| 10 | 140 | 140 | 0.00547463 | 0.111344 | 0.987603 | none |
| 11 | 90 | 90 | 0.0143109 | 0.0869525 | 0.992439 | none |
| 12 | 90 | 90 | 0.0064417 | 1.26253 | -0.593981 | none |
| 13 | 90 | 90 | 0.0530069 | 0.0975671 | 0.990481 | none |

Output errors on the validation data (pooled RMSE: 0.0847503 rad):

| trajectory | scored samples | completed | RMSE (rad) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| 1 | 449 | 449 | 0.113283 | 0.207187 | 0.957074 | none |
| 2 | 299 | 299 | 0.0644694 | 0.115305 | 0.986705 | none |
| 3 | 441 | 441 | 0.0590037 | 0.156984 | 0.975356 | none |

Sensitivity rank test (diagnostic; never excludes): targets domega on the train, val data (4714 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.44, 1.33, 1, 0.997, 0.819, 0.515, 0.475, 4.91e-17; rank 7 of 8.
- Locally indistinguishable combination: v (+1.000); relative singular value 3.42e-17.
- Parameter v has no influence on the targets.

![KarnoppBand train](plots/KarnoppBand_train.png)

*Candidate KarnoppBand, training data, trajectories 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13. Upper axes: measured output theta (rad) and model output of KarnoppBand; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 449; 3: 1 to 299; 4: 1 to 299; 5: 1 to 441; 6: 1 to 441; 7: 1 to 441; 8: 1 to 140; 9: 1 to 140; 10: 1 to 140; 11: 1 to 90; 12: 1 to 90; 13: 1 to 90 (0-based sample indices). No numerical failure occurred.*

![KarnoppBand val](plots/KarnoppBand_val.png)

*Candidate KarnoppBand, validation data, trajectories 1, 2, 3. Upper axes: measured output theta (rad) and model output of KarnoppBand; lower axes: residual (model output minus measured output, rad). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 0.01 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples 1: 1 to 449; 2: 1 to 299; 3: 1 to 441 (0-based sample indices). No numerical failure occurred.*
