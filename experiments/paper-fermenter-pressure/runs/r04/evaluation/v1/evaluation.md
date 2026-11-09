# Evaluation report: task fermenter-pressure

Terms. The harness is the software of ASPIRE that checks and evaluates the candidate models; a candidate is one proposed model; the pool is the set of candidates of one round. Sealed data (test data, reference expression) are inaccessible to the agent. This report contains results on sealed data and is not shown to the agent.

Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])).
Error measures: for one trajectory with scoring interval I of N samples, measured output y[k] (p, bar) and model output ŷ[k], SSE = Σ_(k∈I) (ŷ[k] − y[k])²; RMSE = sqrt(SSE/N), in bar; NRMSE = RMSE/σ, with μ and σ the mean and the population standard deviation of y on I; R² = 1 − SSE / Σ_(k∈I) (y[k] − μ)²; NRMSE and R² are not applicable when σ = 0. The pooled RMSE over several trajectories is S = sqrt(ΣSSE / ΣN); on the test data it is the ranking score.
Numerical failure limits: p in [-100, 100] bar; evaluation time limit 60 s per candidate and data group; symbolic time limit 10 s per verification.
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

Distinct structures: 5 among 5 evaluated candidates; groups: GeneralizedDischarge; MixedResistance; TabulatedValve; CompressibleDischarge; RegularizedOrifice. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: GeneralizedDischarge. The agent's reason: The compact generalized gas-balance model achieved the lowest genuinely held-out validation RMSE among the final stable candidate structures: `0.0386073098819` bar from a train-only fit. Its final parameters are jointly refitted on the training and validation trajectories; their pressure RMSE values are `0.0245809178926` bar and `0.0372737413879` bar, respectively, and are therefore in-sample rather than held-out. The tabulated valve model has a slightly lower final joint-data error but had worse train-only validation performance and greater calibration flexibility. The recommendation preserves positive inlet response, monotone valve response, near-atmospheric recovery, and exact sealed-valve accumulation above the atmospheric reference. The square-root-nearby discharge exponent is an interpretable effective restriction law; systematic time-dependent residuals remain, so no test-performance claim is made.
- Harness note: requirement(s) stated in natural language (R1, R2, R3, R4, R5) are assessed by the human.
- Test score S of the recommended candidate (practical selection): 0.022708 bar; eligible: True; rank in the oracle-based selection: 1.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 5 eligible of 5 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (1209 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (bar) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | GeneralizedDischarge | 0.022708 | R1, R2, R3, R4, R5 | none |
| 2 | MixedResistance | 0.0228649 | R1, R2, R3, R4, R5 | none |
| 3 | TabulatedValve | 0.0231408 | R1, R2, R3, R4, R5 | none |
| 4 | CompressibleDischarge | 0.024907 | R1, R2, R3, R4, R5 | none |
| 5 | RegularizedOrifice | 0.0322471 | R1, R2, R3, R4, R5 | none |

## Candidates

### Candidate GeneralizedDischarge

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `dp = a*Max(flow,0)-b*Min(Max((vscale-valve)/vscale,0),1)**m/(1+c*Min(Max((vscale-valve)/vscale,0),1)**m)*(Max(p-pa,0)/pr)*((Max(p-pa,0)+s)/pr)**(n-1)+r*Max(pa-p,0)`
Complexity: 7 fitted, 2 fixed and 1 tied parameters; 0 non-integer numeric literals; 81 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `dp = P1*Max(0, flow) + P2*Max(0, P3 - p) - 1.0*P4*(1.0*(1.0*P4/(P2*(P5 + 1)))**(1/(1 - P7)) + 1.0*Max(0, -P3 + p))**(P7 - 1)*Max(0, -P3 + p)*Min(1, Max(0, 1.0 - 0.01*valve))**P6/(P5*Min(1, Max(0, 1.0 - 0.01*valve))**P6 + 1)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.022708 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.022708 | 0.162946 | 0.973449 | none |

Output errors on the training data (pooled RMSE: 0.0245809 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0245809 | 0.094268 | 0.991114 | none |

Output errors on the validation data (pooled RMSE: 0.0372737 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0372737 | 0.141977 | 0.979842 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.34, 0.998, 0.571, 0.37, 0.161, 0.132, 0.0399; rank 7 of 7.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![GeneralizedDischarge test](plots/GeneralizedDischarge_test.png)

*Candidate GeneralizedDischarge, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of GeneralizedDischarge; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![GeneralizedDischarge train](plots/GeneralizedDischarge_train.png)

*Candidate GeneralizedDischarge, training data, trajectories train. Upper axes: measured output p (bar) and model output of GeneralizedDischarge; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![GeneralizedDischarge val](plots/GeneralizedDischarge_val.png)

*Candidate GeneralizedDischarge, validation data, trajectories val. Upper axes: measured output p (bar) and model output of GeneralizedDischarge; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*

### Candidate MixedResistance

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `dp = a*Max(flow,0)-b*Min(Max((vscale-valve)/vscale,0),1)**m/(1+c*Min(Max((vscale-valve)/vscale,0),1)**m)*(sqrt((Max(p-pa,0)+s)/pr)-sqrt(s/pr))+r*Max(pa-p,0)`
Complexity: 6 fitted, 2 fixed and 1 tied parameters; 0 non-integer numeric literals; 79 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `dp = P1*Max(0, flow) + P2*Max(0, P3 - p) - P4*(-0.5*sqrt(1/(P2**2*(P5 + 1)**2))*Abs(P4) + sqrt(1.0*Max(0, -P3 + p) + 0.25*P4**2/(P2**2*(P5 + 1)**2)))*Min(1, Max(0, 1.0 - 0.01*valve))**P6/(P5*Min(1, Max(0, 1.0 - 0.01*valve))**P6 + 1)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.0228649 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.0228649 | 0.164072 | 0.97308 | none |

Output errors on the training data (pooled RMSE: 0.0249211 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0249211 | 0.0955727 | 0.990866 | none |

Output errors on the validation data (pooled RMSE: 0.0373748 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0373748 | 0.142362 | 0.979733 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.21, 0.883, 0.532, 0.21, 0.121, 0.0452; rank 6 of 6.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![MixedResistance test](plots/MixedResistance_test.png)

*Candidate MixedResistance, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of MixedResistance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![MixedResistance train](plots/MixedResistance_train.png)

*Candidate MixedResistance, training data, trajectories train. Upper axes: measured output p (bar) and model output of MixedResistance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![MixedResistance val](plots/MixedResistance_val.png)

*Candidate MixedResistance, validation data, trajectories val. Upper axes: measured output p (bar) and model output of MixedResistance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*

### Candidate TabulatedValve

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `dp = a*Max(flow,0)-(dA*Min(Max((Min(Max((vscale-valve)/vscale,0),1)-0)/(kA-0),0),1)+dB*Min(Max((Min(Max((vscale-valve)/vscale,0),1)-kA)/(kB-kA),0),1)+dC*Min(Max((Min(Max((vscale-valve)/vscale,0),1)-kB)/(kC-kB),0),1)+dD*Min(Max((Min(Max((vscale-valve)/vscale,0),1)-kC)/(kD-kC),0),1)+dE*Min(Max((Min(Max((vscale-valve)/vscale,0),1)-kD)/(kE-kD),0),1)+dF*Min(Max((Min(Max((vscale-valve)/vscale,0),1)-kE)/(1-kE),0),1))*(Max(p-pa,0)/pr)*((Max(p-pa,0)+s)/pr)**(n-1)+r*Max(pa-p,0)`
Complexity: 10 fitted, 7 fixed and 1 tied parameters; 0 non-integer numeric literals; 223 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `dp = P1*Max(0, flow) + P2*Max(0, P3 - p) - 1.0*(1.0*(1.0*(P4 + P5 + P6 + P7 + P8 + P9)/P2)**(1/(1 - P10)) + 1.0*Max(0, -P3 + p))**(P10 - 1)*(P4*Min(1, 9.9999999999999994*Min(1, Max(0, 1.0 - 0.01*valve))) + P5*Min(1, Max(0, 9.9999999999999994*Min(1, Max(0, 1.0 - 0.01*valve)) - 1.0)) + P6*Min(1, Max(0, 10.000000000000002*Min(1, Max(0, 1.0 - 0.01*valve)) - 2.0000000000000006)) + P7*Min(1, Max(0, 6.6666666666666657*Min(1, Max(0, 1.0 - 0.01*valve)) - 1.9999999999999996)) + P8*Min(1, Max(0, 4.9999999999999997*Min(1, Max(0, 1.0 - 0.01*valve)) - 2.2499999999999999)) + P9*Min(1, Max(0, 2.8571428571428573*Min(1, Max(0, 1.0 - 0.01*valve)) - 1.8571428571428573)))*Max(0, -P3 + p)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.0231408 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.0231408 | 0.166052 | 0.972427 | none |

Output errors on the training data (pooled RMSE: 0.0250987 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0250987 | 0.0962539 | 0.990735 | none |

Output errors on the validation data (pooled RMSE: 0.0369952 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0369952 | 0.140917 | 0.980143 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.52, 1.31, 0.832, 0.748, 0.5, 0.447, 0.388, 0.215, 0.125, 0.123; rank 10 of 10.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![TabulatedValve test](plots/TabulatedValve_test.png)

*Candidate TabulatedValve, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of TabulatedValve; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![TabulatedValve train](plots/TabulatedValve_train.png)

*Candidate TabulatedValve, training data, trajectories train. Upper axes: measured output p (bar) and model output of TabulatedValve; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![TabulatedValve val](plots/TabulatedValve_val.png)

*Candidate TabulatedValve, validation data, trajectories val. Upper axes: measured output p (bar) and model output of TabulatedValve; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*

### Candidate CompressibleDischarge

Position in the agent's order: 4. Status: evaluated.
File and expression checks: passed.
- `dp = a*Max(flow,0)-b*Min(Max((vscale-valve)/vscale,0),1)**m/(1+c*Min(Max((vscale-valve)/vscale,0),1)**m)*(Max(p-pa,0)/pr)*sqrt(Max(p+pa,0)/(2*pa))/sqrt((Max(p-pa,0)+s)/pr)+r*Max(pa-p,0)`
Complexity: 6 fitted, 2 fixed and 1 tied parameters; 0 non-integer numeric literals; 94 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 4: `dp = P1*Max(0, flow) + P2*Max(0, P3 - p) - 0.5*sqrt(2)*P4*sqrt(1/P3)*Max(0, -P3 + p)*sqrt(Max(0, P3 + p))*Min(1, Max(0, 1.0 - 0.01*valve))**P6/((P5*Min(1, Max(0, 1.0 - 0.01*valve))**P6 + 1)*sqrt(1.0*Max(0, -P3 + p) + 1.0*P4**2/(P2**2*(P5 + 1)**2)))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.024907 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.024907 | 0.178726 | 0.968057 | none |

Output errors on the training data (pooled RMSE: 0.0275591 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0275591 | 0.105689 | 0.98883 | none |

Output errors on the validation data (pooled RMSE: 0.0385439 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0385439 | 0.146816 | 0.978445 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.18, 0.96, 0.493, 0.225, 0.13, 0.0404; rank 6 of 6.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![CompressibleDischarge test](plots/CompressibleDischarge_test.png)

*Candidate CompressibleDischarge, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of CompressibleDischarge; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![CompressibleDischarge train](plots/CompressibleDischarge_train.png)

*Candidate CompressibleDischarge, training data, trajectories train. Upper axes: measured output p (bar) and model output of CompressibleDischarge; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![CompressibleDischarge val](plots/CompressibleDischarge_val.png)

*Candidate CompressibleDischarge, validation data, trajectories val. Upper axes: measured output p (bar) and model output of CompressibleDischarge; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*

### Candidate RegularizedOrifice

Position in the agent's order: 5. Status: evaluated.
File and expression checks: passed.
- `dp = a*Max(flow,0)-b*Min(Max((vscale-valve)/vscale,0),1)**m*(Max(p-pa,0)/pr)/sqrt((Max(p-pa,0)+s)/pr)+r*Max(pa-p,0)`
Complexity: 4 fitted, 3 fixed and 1 tied parameters; 0 non-integer numeric literals; 58 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 5: `dp = P1*Max(0, flow) + P2*Max(0, 1.0 - p) - 1.0*P3*Max(0, p - 1.0)*Min(1, Max(0, 1.0 - 0.01*valve))**P4/sqrt(1.0*Max(0, p - 1.0) + 1.0*P3**2/P2**2)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.0322471 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.0322471 | 0.231396 | 0.946456 | none |

Output errors on the training data (pooled RMSE: 0.0334003 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0334003 | 0.12809 | 0.983593 | none |

Output errors on the validation data (pooled RMSE: 0.0398432 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0398432 | 0.151765 | 0.976968 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 1.89, 0.609, 0.22, 0.116; rank 4 of 4.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![RegularizedOrifice test](plots/RegularizedOrifice_test.png)

*Candidate RegularizedOrifice, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of RegularizedOrifice; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![RegularizedOrifice train](plots/RegularizedOrifice_train.png)

*Candidate RegularizedOrifice, training data, trajectories train. Upper axes: measured output p (bar) and model output of RegularizedOrifice; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![RegularizedOrifice val](plots/RegularizedOrifice_val.png)

*Candidate RegularizedOrifice, validation data, trajectories val. Upper axes: measured output p (bar) and model output of RegularizedOrifice; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*
