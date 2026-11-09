# Identification record

`PLAN.md` records the model families proposed before fitting. The delivered pool contains four different friction closures, not coefficient perturbations of one equation. No test data or evaluation results were available or accessed.

## Data and methods actually used

The initial torque-balance diagnostic used ordinary least squares, `numpy.linalg.lstsq`, on `data/train.csv`. On moving samples selected by `Abs(omega) > 0.8` rad/s, sinusoidal and linear restoring laws had acceleration RMSEs of `10.6392` rad/s^2 and `23.0613` rad/s^2 respectively. These are derivative-fit diagnostics, not simulation scores. The detailed outputs and residual bins are reproduced by `initial_fit.py`.

`diagnostics.py` compared an expanded linear feature library on training samples with `Abs(omega) > 0.8` rad/s, excluding the first five samples of every trajectory to avoid initialization differentiation artifacts. Adding angle modulation of sliding friction reduced acceleration RMSE from `10.5898` rad/s^2 to `9.5993` rad/s^2 on that same subset. This motivated an empirical positive angular friction envelope. Directional residual means then motivated separate positive and negative friction limits. No genetic programming or neural network was used. Cubic motor gain, quadratic drag, additional restoring harmonics and a separate static-friction excess were tested but not retained in the final pool: they either gave little useful improvement, produced poorly identified coefficients, or did not improve validation/cross-validation sufficiently to justify their complexity. Intermediate values and comparisons are in `fit_results.json` and `cv_results.json`.

Final values were fitted jointly by bounded nonlinear least squares on open-loop angle residuals, using the task's classical RK4 step of `0.01` s and zero-order-held voltage. There were six deterministic starts per loss, and both ordinary squared loss and soft-L1 loss were compared. The random seed for generating starts was `271828`. `fit_final.py` reproduces these fits, using the supplied intermediate `cv_results.json` for the first starts. Its simulator and bounds are in `fit_models.py`; shared fitting and trajectory packing functions are in `crossvalidate.py`. Numba `0.68.0` was installed to compile the RK4 loops. All other numerical software was already supplied by the environment.

The three validation trajectories were initially held out for structure comparison, then included with all thirteen training trajectories for final parameter estimation. Leave-one-trajectory-out refits use only the other fifteen trajectories in their objective, but are warm-started from full-data coefficients. Loss selection and family selection use these known data, so these checks are not an untouched test set or a fully nested model-selection estimate.

| Candidate | Selected output-error loss | Full-data angle RMSE (rad) | Leave-one-trajectory-out angle RMSE (rad) |
|---|---|---:|---:|
| AngleClip | squared | `0.05323582` | `0.06048971` |
| StaticBlend | soft-L1 | `0.05810928` | `0.06320398` |
| SmoothAngle | soft-L1 | `0.05740852` | `0.06128174` |
| SpeedWeakening | soft-L1 | `0.07078063` | `0.07691553` |

Both columns aggregate all samples after trajectory initialization, with equal weight per sample. `final_results.json` contains the complete starts, bounds, alternative-loss results and per-trajectory errors.

## Residuals and recommendation

`audit_final.py` examines the delivered fits. On the combined training/validation moving subset selected by `Abs(omega) > 0.8` rad/s and excluding each trajectory's first five samples, AngleClip has acceleration-residual RMSE `14.0922` rad/s^2 and mean measured-minus-predicted acceleration residual `0.6702` rad/s^2. Its coefficients were selected by angle simulation, not by minimizing these acceleration residuals. The full-data endpoint angle error is still `-0.08734` rad on training free trajectory 8 and `-0.11859` rad on validation driven trajectory 1. Thus the angular/directional friction terms improve but do not explain all run-dependent stops and differentiated-signal discrepancies. These residuals support reporting uncertainty rather than adding increasingly elaborate terms.

AngleClip is recommended for the combination of the lowest aggregate cross-validated angle error and exact static equilibria. The small numerical difference from SmoothAngle is not itself decisive. SmoothAngle and SpeedWeakening cannot hold a permanent nonzero free resting angle; StaticBlend and AngleClip can. The delivered models and limitations explain this distinction explicitly.

## Physical checks

All candidates have `dtheta = omega` identically, meeting R1. For the smooth models at `omega = 0` rad/s and `u = 0` V, acceleration is `-g*sin(theta)`, with positive `g`, so R2 follows throughout the requested angular interval. For AngleClip, its positive friction limits cause clipping of `-g*sin(theta)` toward zero without reversing its sign. For StaticBlend, the force dead zone also maps that restoring acceleration toward zero without reversing its sign. Therefore the same R2 sign condition holds for the sticking families.

The angular friction envelopes are strictly positive because the fitted base scale is positive and the sine/cosine modulation norm is below one; the independent coefficient bounds also guarantee this. All motor gains are positive. For the smooth families, input dependence is affine with positive slope. For AngleClip, increasing voltage increases the external torque minus its clipping by a nonnegative amount. For StaticBlend, the weighted dead-zone and kinetic branches are each nondecreasing in voltage, and the velocity weights do not depend on voltage. These establish R3 as nondecreasing input dependence, with zero input slope allowed inside a supported static band.

As supplementary numerical checks, `audit_final.py` used `30000` random domain points with seed `314159`, plus angular boundary points for R2. No nonfinite acceleration, positive R2 product or negative input increment was found. This sampling is not the proof; the sign and monotonicity arguments above are the reason the structures were constrained. Detailed numerical checks are in `final_audit.json`.

`python check_submission.py` passed all four candidate files and the pool file. Bibliographic friction-model background is given in each candidate; the references are explicitly marked as recalled from memory because attempted online retrieval returned no usable text. No empirical claim here relies on those references.
