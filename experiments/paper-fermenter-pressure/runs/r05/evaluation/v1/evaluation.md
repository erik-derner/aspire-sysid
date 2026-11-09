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
| candidates proposed | 3 |
| accepted by the file and expression checks | 3 |
| outside the pool limit of 10 (not evaluated) | 0 |
| evaluated | 3 |
| excluded by physical requirements | 0 |
| failed numerically on training or validation data | 0 |
| failed numerically on test data | 0 |
| eligible for ranking | 3 |

Note: the categories overlap: the candidates accepted by the checks include those outside the pool limit, and a candidate can be both excluded by requirements and failed numerically; the counts need not sum to the pool size.

Distinct structures: 3 among 3 evaluated candidates; groups: power_balance; mixed_resistance; compressible_nozzle. Convention: ties resolved, fixed values kept, given constants kept, fitted parameters renamed P1..Pn in order of first occurrence; equal when a one-to-one renaming of the fitted parameters makes every expression identical in SymPy's canonical form.

### Recommendation of the agent

Recommended candidate: power_balance. The agent's reason: The regularized power-law gas balance had the best validation free-running error among these numerically conditioned families before the final refit (0.038653 bar), and has the lowest combined pressure RMSE after fitting both available trajectories (0.031752 bar). Its positive inlet gain, shutoff aperture law, finite atmospheric relaxation and overpressure valve monotonicity are physically interpretable. The residual timing correlation and sub-atmospheric R2 exception are disclosed; no unseen-test performance is claimed.
- Harness note: requirement(s) stated in natural language (R1, R2, R3, R4, R5) are assessed by the human.
- Test score S of the recommended candidate (practical selection): 0.0228708 bar; eligible: True; rank in the oracle-based selection: 1.

## Oracle-based selection on test data

Label: oracle-based selection on test data. Candidates considered: 3 eligible of 3 evaluated. Criterion: pooled test RMSE S, increasing, the pooled RMSE over the test trajectories test-1 (1209 scored samples). Tie rule: |S_a - S_b| <= 1e-12 * max(S_a, S_b) for consecutive candidates; tied candidates share a rank. This ranking selects on the test data. It measures whether the pool contains an accurate model, not whether the agent can recognize that model without test data. A rank is not evidence of physical admissibility: each entry carries its unresolved requirements and any violation allowed by the user.

| rank | candidate | S (bar) | unresolved requirements | violations allowed by the user |
|---|---|---|---|---|
| 1 | power_balance | 0.0228708 | R1, R2, R3, R4, R5 | none |
| 2 | mixed_resistance | 0.0249101 | R1, R2, R3, R4, R5 | none |
| 3 | compressible_nozzle | 0.0309098 | R1, R2, R3, R4, R5 | none |

## Candidates

### Candidate power_balance

Position in the agent's order: 1. Status: evaluated.
File and expression checks: passed.
- `dp = ain*flow - (cf*(1+shape)*Min(1, Max(0, 1-valve/vmax))**expo/(1+shape*Min(1, Max(0, 1-valve/vmax))**expo))*(((p-patm)/patm)/(((p-patm)/patm)**2+delta**2)**((1-power)/2))`
Complexity: 6 fitted, 2 fixed and 1 tied parameters; 0 non-integer numeric literals; 73 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 1: `dp = P1*flow - 1.0*P2*(P3 + 1)*(p - 1.0)*((1.0*P2/P5)**(2/(1 - P6)) + 1.0*(p - 1.0)**2)**(P6/2 - 1/2)*Min(1, Max(0, 1 - 0.01*valve))**P4/(P3*Min(1, Max(0, 1 - 0.01*valve))**P4 + 1)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.0228708 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.0228708 | 0.164114 | 0.973067 | none |

Output errors on the training data (pooled RMSE: 0.0248248 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0248248 | 0.0952031 | 0.990936 | none |

Output errors on the validation data (pooled RMSE: 0.0374107 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0374107 | 0.142499 | 0.979694 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.15, 1.01, 0.528, 0.182, 0.16, 0.054; rank 6 of 6.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![power_balance test](plots/power_balance_test.png)

*Candidate power_balance, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of power_balance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![power_balance train](plots/power_balance_train.png)

*Candidate power_balance, training data, trajectories train. Upper axes: measured output p (bar) and model output of power_balance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![power_balance val](plots/power_balance_val.png)

*Candidate power_balance, validation data, trajectories val. Upper axes: measured output p (bar) and model output of power_balance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*

### Candidate mixed_resistance

Position in the agent's order: 2. Status: evaluated.
File and expression checks: passed.
- `dp = ain*flow - (cf*(1+shape)*Min(1, Max(0, 1-valve/vmax))**expo/(1+shape*Min(1, Max(0, 1-valve/vmax))**expo))*(2*((p-patm)/patm)/(delta+sqrt(delta**2+4*Abs(((p-patm)/patm)))))`
Complexity: 5 fitted, 2 fixed and 1 tied parameters; 0 non-integer numeric literals; 74 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 2: `dp = P1*flow - 2.0*P2*(P3 + 1)*(p - 1.0)*Min(1, Max(0, 1 - 0.01*valve))**P4/((1.0*P2/P5 + sqrt(1.0*P2**2/P5**2 + 4*Abs(1.0*p - 1.0)))*(P3*Min(1, Max(0, 1 - 0.01*valve))**P4 + 1))`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.0249101 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.0249101 | 0.178747 | 0.968049 | none |

Output errors on the training data (pooled RMSE: 0.0276399 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0276399 | 0.105999 | 0.988764 | none |

Output errors on the validation data (pooled RMSE: 0.0386856 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0386856 | 0.147355 | 0.978286 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.14, 0.608, 0.219, 0.144, 0.055; rank 5 of 5.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![mixed_resistance test](plots/mixed_resistance_test.png)

*Candidate mixed_resistance, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of mixed_resistance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![mixed_resistance train](plots/mixed_resistance_train.png)

*Candidate mixed_resistance, training data, trajectories train. Upper axes: measured output p (bar) and model output of mixed_resistance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![mixed_resistance val](plots/mixed_resistance_val.png)

*Candidate mixed_resistance, validation data, trajectories val. Upper axes: measured output p (bar) and model output of mixed_resistance; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*

### Candidate compressible_nozzle

Position in the agent's order: 3. Status: evaluated.
File and expression checks: passed.
- `dp = ain*flow - (cf*(1+shape)*Min(1, Max(0, 1-valve/vmax))**expo/(1+shape*Min(1, Max(0, 1-valve/vmax))**expo))*(sign(((p-patm)/patm))*Max(p, patm)/patm*sqrt(Max(0, Max(rcrit, Min(p, patm)/Max(p, patm))**(2/gam)-Max(rcrit, Min(p, patm)/Max(p, patm))**((gam+1)/gam)))*sqrt(Abs(((p-patm)/patm))/(Abs(((p-patm)/patm))+delta)))`
Complexity: 5 fitted, 3 fixed and 2 tied parameters; 0 non-integer numeric literals; 131 expression-tree nodes (SymPy tree, every operator, function, symbol and number counted once).
Structure group 3: `dp = P1*flow - 1.0*P2*(P4 + 1)*sqrt(1/(1.4285714285714287*P2**2/P3**2 + Abs(1.0*p - 1.0)))*sqrt(Abs(1.0*p - 1.0))*sign(1.0*p - 1.0)*sqrt(Max(0, Max(0.52828178771717412, Min(1.0, p)/Max(1.0, p))**1.4285714285714287 - Max(0.52828178771717412, Min(1.0, p)/Max(1.0, p))**1.7142857142857143))*Max(1.0, p)*Min(1, Max(0, 1 - 0.01*valve))**P5/(P4*Min(1, Max(0, 1 - 0.01*valve))**P5 + 1)`

Requirements:

| id | type | outcome | status | method | detail |
|---|---|---|---|---|---|
| R1 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R2 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R3 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R4 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |
| R5 | natural_language | unavailable | unresolved | not applicable | stated in natural language: the harness does not assess it; the human assesses it, and the agent's assertion alone does not count as verification |

Output errors on the test data (sealed) (pooled RMSE: 0.0309098 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| test-1 | 1209 | 1209 | 0.0309098 | 0.2218 | 0.950805 | none |

Output errors on the training data (pooled RMSE: 0.0372824 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| train | 1451 | 1451 | 0.0372824 | 0.142978 | 0.979557 | none |

Output errors on the validation data (pooled RMSE: 0.0453489 bar):

| trajectory | scored samples | completed | RMSE (bar) | NRMSE | R² | failure |
|---|---|---|---|---|---|---|
| val | 1453 | 1453 | 0.0453489 | 0.172736 | 0.970162 | none |

Sensitivity rank test (diagnostic; never excludes): targets dp on the train, val data (2906 rows, 0 dropped); analytic derivatives (SymPy), ties differentiated through their equations; scaling: rows of each target divided by the standard deviation of its measured column; columns divided by their Euclidean norm; rank threshold s_i / s_1 > 1e-08; singular values 2.11, 0.673, 0.268, 0.156, 0.0504; rank 5 of 5.
Reference comparison: not applicable (the task has no reference expression).
Eligible for ranking: True.

![compressible_nozzle test](plots/compressible_nozzle_test.png)

*Candidate compressible_nozzle, test data (sealed), trajectories test-1. Upper axes: measured output p (bar) and model output of compressible_nozzle; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples test-1: 1 to 1209 (0-based sample indices). No numerical failure occurred.*

![compressible_nozzle train](plots/compressible_nozzle_train.png)

*Candidate compressible_nozzle, training data, trajectories train. Upper axes: measured output p (bar) and model output of compressible_nozzle; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples train: 1 to 1451 (0-based sample indices). No numerical failure occurred.*

![compressible_nozzle val](plots/compressible_nozzle_val.png)

*Candidate compressible_nozzle, validation data, trajectories val. Upper axes: measured output p (bar) and model output of compressible_nozzle; lower axes: residual (model output minus measured output, bar). Evaluation mode: simulation (initialized once per trajectory from the measured state at sample 0; classical fourth-order Runge-Kutta integration with 1 step(s) per sampling period T_s = 5 s and zero-order hold of the input; the model output is h(x[k], u[k])). Initialization: the first 1 sample(s) of each trajectory initialize the model and are excluded from the errors. Errors are computed on the samples val: 1 to 1453 (0-based sample indices). No numerical failure occurred.*
