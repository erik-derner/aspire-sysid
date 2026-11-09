# Identification record

## Data and experimental design

Only `data/train.csv` was used: three separate trajectories, 150 samples each, with `Ts = 0.2` s supplied by TASK.md. No test files or evaluation results were accessed. `plan.md` records the families proposed before fitting. The initial independent diagnostic work is reproduced by `diagnostic_helper.py`, with results in `helper_report.md`.

The state columns are `x` and `y` in m and `phi` in rad; inputs are `v_f` in m/s and `v_a` in rad/s. Unwrap `phi` within each trajectory. The model does not require a wrapped heading, because position updates are periodic in heading. All transitions stay within their trajectory. Command phase is a diagnostic only, not an expression input.

Each fit uses all complete overlapping windows of 25 transitions, corresponding to 5 s, starting at sample indices 0 through 124 (dimensionless, within each training trajectory). Thus there are 375 windows across the three trajectories. Each rollout starts from the observed pose and then receives no state correction. These overlapping windows are not statistically independent. Validation leaves out an entire trajectory, refits on the other two, and evaluates all complete 5 s windows in the held-out trajectory. Only three experiments are available, so ranking differences are uncertain. Selection over multiple structures and objectives also introduces some validation selection bias.

## What was actually tried

`identify.py` compares forward Euler, exact constant-twist arc, affine angular bias, adjustable projection phase, symmetric angular dead zone, odd cubic angular response, smooth angular dead zone, forward/angular coupling, heading-harmonic angular drift, and body-frame lateral motion. Initial fits jointly minimize squared position errors for `x` and `y`, with a heading-error weight of 0.3 m/rad. Parameters and validation results are in `fit_results.json`.

`investigate.py` adds a virtual-wheel dead-zone model and compares the original position/heading criterion with two alternatives: `x` only, and `x` plus a heading-error weight of 0.15 m/rad. The `y` weight is zero in both alternatives. Results are in `investigate_results.json`. All nonlinear fits use deterministic trust-region reflective nonlinear least squares (`scipy.optimize.least_squares`), numerical Jacobians, linear loss, at most 400 function evaluations (dimensionless count), and dimensionless tolerances `ftol = xtol = gtol = 1e-10`. Starting values and bounds are given separately in each candidate and in the source. No stochastic optimization or genetic symbolic regression was run. No seed is needed.

`residual_analysis.py` additionally fits a diagnostic sparse angular-response library on settled command phases using `sklearn.linear_model.LassoCV`. Features are `v_a`, `v_a**3`, `sign(v_a)`, `v_a*v_f`, `sin(phi)`, `cos(phi)`, `v_f`, `v_a*sin(phi)` and `v_a*cos(phi)`, standardized by their training standard deviations. A fitted intercept is included. Regularization is selected from 40 logarithmically spaced penalty values between `1e-4` and `1e-1` using three leave-one-trajectory-out folds, with `max_iter = 20000` and `tol = 1e-9`, dimensionless algorithm settings. Because columns are standardized and the target is angular velocity, these penalty values have the numerical target scale of rad/s. This deterministic diagnostic retains `v_a`, `v_a**3` and `v_a*v_f`; heading harmonics are set to zero. It is not a submitted model. No memory-bearing feature is used in a delivered expression.

## Residual evidence and structural decisions

Using the final Euler coefficients, one-step `x` residual RMSE is 0.00508 m for first intervals after command changes and approximately 0.00160 to 0.00171 m for the other block phases, on the 447 within-trajectory training transitions. Its heading residual RMSE is 0.08735 rad at changes and approximately 0.01803 to 0.02106 rad at settled phases. These are predictions minus observations, not measurement-noise estimates. This concentration at switches suggests unresolved lag, rather than an independent additive disturbance. An independent regression including the previous angular command reduces all-transition angular-velocity residual RMSE from about 0.184 rad/s to about 0.091 rad/s. Previous commands and actuator states are not permitted model arguments, so that informative diagnostic was not delivered as a model.

Small angular commands exhibit suppressed settled angular response. This motivated the angular and wheel dead-zone candidates. A free projection phase addresses a portion of position/heading timing mismatch without pretending to recover actuator memory. The fitted near-zero, slightly negative phase in the angular dead-zone model is empirical quadrature, not a physical time delay.

Odd cubic and smooth dead-zone alternatives did not provide convincing held-out improvements over smaller alternatives. Heading harmonics and forward/angular coupling reduced some fitting residuals but worsened held-out trajectory results. Lateral velocity was small in the diagnostic data and did not yield a validation benefit. These structures were omitted rather than retained solely for training fit. The sparse angular diagnostic also did not support heading harmonics. Coherent residual trends within trajectories could reflect odometry errors or calibration drift, but elapsed time is not an allowed argument and position-dependent proxies were not defensible.

## Submitted models and validation

The table contains `x` RMSE in m, calculated from complete 5 s windows in `data/train.csv`. Training values use the final all-data fits. Validation pools equal numbers of predictions from all three held-out trajectories. These are not hidden-test scores.

| Candidate | Training `x` RMSE (m) | Leave-one-trajectory-out `x` RMSE (m) |
|---|---:|---:|
| Euler | 0.02889 | 0.02908 |
| WheelDeadZone | 0.02917 | 0.02964 |
| ExactArc | 0.02931 | 0.02946 |
| AngularDeadZone | 0.02919 | 0.03056 |

Recommend Euler because of its smallest parameter count and lowest held-out error for the scored output, not because its one-step heading calibration is best. The arc and nonlinear candidates offer distinct physically motivated discretization/calibration hypotheses. Their validation differences are small relative to the scarcity of trajectories.

As a stress diagnostic, each all-data fit was also rolled out once over all 149 transitions (29.8 s) of each training trajectory. Final Euler `x` RMSE values were 0.02401 m, 0.04855 m and 0.16054 m for trajectories 1, 2 and 3 respectively. These much longer rollouts illustrate accumulating errors and are not the fitting horizon. The nonlinear alternatives do not universally dominate on this diagnostic either.

## Reproduction and limitations

Run `python identify.py`, `python investigate.py` and `python residual_analysis.py` to reproduce exploration. `wheel_model.py` contains the wheel-response addition; `deliver.py` independently refits each submitted model on all training data from its declared starts and writes the candidate JSON files and pool. `python check_submission.py` validates the submission. All final coefficients are jointly fitted within their own candidates; no coefficient is transferred between candidates. `Ts` and the small-angle numerical cutoff `eps`, where used, are fixed, not fitted.

The three-state expressions cannot represent actuator carryover or infer true wheel geometry from pose alone. They should be viewed as reduced predictors over the given command ranges and horizon. Pose noise and physical drift are confounded, especially over longer trajectories. The family reference in candidate files is LaValle, Planning Algorithms (2006), cited from memory; no external numerical robot specification was used. Reproducibility depends on NumPy, SciPy and scikit-learn versions supplied in the environment.
