# Identification record

## Data and interpretation

Only data/train.csv and data/val.csv were used. There are 13 training trajectories and 3 validation trajectories; identically numbered trajectories in the two files are distinct experiments. Sampling is `T_s = 0.01` s. Define U_y, U_x1 and U_x2 as the unspecified units of the logged columns `y`, `x1` and `x2`. Acceleration has unit U_x1/s. Physical apparatus and intended use are unknown.

Inspection in inspect_data.py found that `x1` is almost exactly the centered finite difference of `y`, and `dx1` is almost exactly the centered finite difference of `x1`. Some trajectory endpoints differ. The logged coordinates are quantized. This supports the kinematic assumption `dy = x1` but makes differentiation-based acceleration fitting noisy. An initial Savitzky-Golay check used a window of 11 samples, polynomial degree 4, first derivative and `delta = 0.01` s, omitting 5 samples at each end. This was diagnostic only, not the final fitting target. The affine acceleration screening residual `RMSE = 15.67026` U_x1/s was computed on these interior training rows.

## Families tried and changes

The initial plan, announced before fitting, included affine state-space, polynomial, and nonlinear restoring/damping families. No gplearn, PySINDy, symbolic-regression search or sparse-regression algorithm was ultimately run. Low-dimensional explicit structures were sufficient to expose the main restoring and friction effects.

The helper performed derivative ordinary least-squares screening with `numpy.linalg.lstsq`, then training-only free-running nonlinear least-squares fitting. It tested sinusoidal restoring, smooth sign friction, fitted coordinate frequency, a cosine term, cubic and signed-quadratic input, and quadratic velocity damping. Derivative fitting gave starts and comparisons only. Input nonlinearities did not improve held-out rollout sufficiently; positive quadratic velocity feedback was not retained because of extrapolation concerns. Fitted coordinate frequency improved training but not validation. The numerical scale in the trigonometric argument was therefore left at its supplied coordinate scale.

Subsequent tests in explore_models.py compared odd fifth-order polynomial restoring, rational restoring, speed-dependent friction, a second restoring harmonic, input-shifted friction, position-modulated friction and input-modulated friction. The rational and second-harmonic alternatives had worse validation rollouts than the position-modulated friction candidate. The speed-dependent friction extension had little benefit relative to its additional parameters.

Residuals and the different nearly constant resting coordinates motivated the clipped-force alternative in stick_models.py. Two cancellation structures and two starting fading-speed scales were tested. This was not the best validation model, but represents static resting equilibria that the other families cannot represent exactly.

## Selection and final estimation

All rollouts initialize from each logged first state, use classical fourth-order Runge-Kutta with held-constant input, and never reset to later measurements. The fitting criterion is unweighted squared error in simulated `y`, excluding initial samples; it matches the announced output metric. Final fits do not minimize `dx1` error.

width_check.py fitted the polynomial and position-modulated friction families with `w = 0.15`, `w = 0.2` and `w = 0.3` U_x1. The largest of these widths gave the lowest validation error in both grids; the differences for the polynomial were small. Narrower freely fitted widths improved training error but worsened validation and increased RK4 stiffness. The selected width is reported as fitted, since validation data selected it, even though it was held constant in the final coefficient optimization.

Prior training-only rollout errors, all in U_y:

| Submitted family | Training RMSE | Validation RMSE |
|---|---:|---:|
| Position-modulated sinusoidal friction | 0.05317072 | 0.07491741 |
| Fifth-order polynomial restoring | 0.05580873 | 0.08002477 |
| Static-force cancellation | 0.05467235 | 0.08321687 |

Validation selected structures and widths, so even these comparisons are selection results, not untouched-test estimates. The final stage in fit_final.py refitted remaining coefficients on all supplied training and validation trajectories. It used `scipy.optimize.least_squares` with the trust-region reflective algorithm, bounds, `max_nfev = 350`, `diff_step = 0.0001`, and `ftol = xtol = gtol = 2e-8`; numerical settings are dimensionless. Numerical starts, bounds and parameter units are in each candidate and final_fit_results.json. There are no random seeds because fitting is deterministic. Numba 0.68.0 accelerated RK4. write_models.py writes the candidate documentation and pool.

Final in-sample rollout RMSE, in U_y, is respectively 0.05368892 / 0.07220022, 0.05636768 / 0.07661207, and 0.05611577 / 0.07536960 on training / validation. These are calibration results, not independent validation. The position-modulated sinusoidal model is recommended from its earlier comparison and moderate complexity.

## Residual audit and limitations

For the recommended final fit, acceleration residual RMSE is 10.02185 U_x1/s on training and 16.41910 U_x1/s on validation. On validation, the intermediate-speed band `1 <= Abs(x1) < 5` U_x1 has acceleration residual `RMSE = 27.08129` U_x1/s. The zero/low-speed band `0 <= Abs(x1) < 0.2` U_x1 has `RMSE = 7.45888` U_x1/s. The static-force cancellation alternative reduces this latter residual to `RMSE = 4.05603` U_x1/s but does not win the prior held-out output comparison. These results support the alternate static-friction structure while also demonstrating unresolved transients and differentiation effects.

The final recommended acceleration residual correlations with `y`, `x1` and `x2` on training are -0.1513, -0.0614 and 0.1980, respectively (dimensionless); corresponding validation correlations are -0.1018, -0.0361 and 0.0689. Thus residuals are not white or fully explained. No physical mechanism, missing-input delay or extra hidden state can be established from the brief. Polynomial extrapolation may introduce extra equilibria outside the calibration range; periodicity of the trigonometric candidates is also an assumption. No test trajectories or evaluation results were accessed.

## Reproduction

The original exploratory scripts and their result files are retained. Starting from the supplied intermediate starting-value files, run `python fit_final.py`, `python write_models.py`, then `python check_submission.py`. For the full earlier screening history run inspect_data.py, helper_explore.py, helper_rollout.py, explore_models.py, stick_models.py and width_check.py before the final stage. NumPy, pandas, SciPy and Numba are required. The external bibliographic friction reference in the model descriptions is explicitly from memory and was not verified online; the formulas are manually proposed structures, not copied constitutive laws.
