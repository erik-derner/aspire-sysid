# Identification record

## Scope and reproducibility

The permitted state is `y`; the forcing inputs are `x1` and `x2`; the fitting-target derivative is `dy`. Their physical meanings and units are unknown. The sample period is 5 s. All experiments use only data/train.csv and data/val.csv. Neither hidden test trajectories nor evaluation results were accessed.

The pre-fit plan is in plan.md. Run reproduce.cmd to recreate exploratory results, final estimates, candidate JSON files, and the submission check. Candidate-specific estimation records contain the numerical starting vectors and bounds. fit_final.py can also be rerun using the saved exploratory result files. fit_final.py writes final_results.json; make_submission.py writes the pool and candidates.

Software used: Python 3.12.10, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1, SymPy 1.14.0, and scikit-learn 1.9.1. No stochastic search was used; no seed applies. Installed gplearn and PySINDy were not used. One helper performed derivative-library exploration, including orthogonal matching pursuit; its scripts and output files have the helper_ prefix. The main agent ran helper_structure.py after the helper stopped, and did all main simulation fits and final selection.

## Exploration actually performed

1. Descriptive statistics and the comparison of `dy` with `diff(y)/5` were computed separately for each trajectory. The forward-increment mismatch RMSE was approximately `0.000221` on training and `0.000336` on validation, in the unspecified derivative units. Thus the target is close to a forward increment but not perfectly identical to it; no assumption of a noiseless continuous derivative was made.
2. Polynomial libraries of total degree one through five were fitted by ordinary least squares. The helper standardized using training means and population standard deviations. The main simulation fits used fixed round normalizations recorded in the candidate files. The helper also ran scikit-learn OrthogonalMatchingPursuit with normalized library columns, no intercept, and requested support sizes of three, five, eight, twelve and sixteen where those sizes were smaller than the library size. This did not beat the full cubic derivative baseline.
3. Additive transformed-input and transformed-state libraries included linear, logarithmic, square-root, squared, cubed, reciprocal, saturating, exponential and power-law terms. Bilinear feedback, restricted polynomials and state-input interactions were explored. Nonlinear least-squares initial values, bounds and settings are in the corresponding scripts. Several fitted shapes reached bounds, so none was interpreted as a discovered physical law.
4. Each promising model was tested as an uninterrupted RK4 simulation, with a step of 5 s, inputs held constant per step, and a measured initial state for each independent trajectory. Subsequent observations never reset simulation. State and parameter sensitivities were propagated through RK4 to fit simulation error.
5. Residual diagnostics considered state/input bins, bias, extremes, lag-one correlation, and correlations with adjacent input changes. Adding the next `x2` change to a cubic derivative regression was diagnostic only: derivative RMSE fell to about `0.001009` on training and `0.001251` on validation, in the unspecified derivative units. This is evidence of unrepresented temporal structure, not permission to use a future-input argument. Shifted-input diagnostics were never delivered.
6. Residuals motivated rational denominators, shifted state transforms, positive-rate and sigmoid relaxation, and fixed-knot continuous state hinges. Higher-degree polynomial fits were rejected: degree four did not improve held-out simulation and degree five had a training simulation failure. Affine dynamics were also rejected as inadequate. The submitted pool has global polynomial, local hinge, rational, logarithmic and positive-rate relaxation families rather than coefficient variants of one expression.

## Quantitative selection

All state RMSE values below are in the unspecified units of `y`. They exclude each trajectory's first sample. The training-only derivative initialization gives an actual separate-trajectory check before final joint estimation:

| Candidate family | Training-only derivative fit: validation simulation RMSE | Final joint refit: training RMSE | Final joint refit: validation RMSE |
|---|---:|---:|---:|
| Cubic | `0.036525` | `0.023325` | `0.033375` |
| Hinge | `0.036836` | `0.024597` | `0.035035` |
| Pade | `0.039083` | `0.024865` | `0.037114` |
| LogShift | `0.038606` | `0.024507` | `0.037152` |
| Sigmoid | `0.050201` | `0.038009` | `0.041943` |

The pre-refit rational and logarithmic results concern the unfloored expressions; the submitted floors are explicit numerical continuations. Final diagnostics apply to the actual floored candidates. The final fit minimizes equal-weight squared state errors on both experiments, with their separate initial states; all fitted parameters are refitted jointly within each family. Therefore the final validation column is in-sample, not an unbiased test estimate. The cubic is recommended on both its early separate-trajectory performance and final joint fit. Twenty coefficients are a substantial complexity cost, acknowledged in its limitations.

## Remaining uncertainty

Final derivative residuals remain autocorrelated and correlated with the next `x2` change. Omitted dynamics, input/output timing, measurement effects and scalar-state inadequacy cannot be separated by these data. The guarded rational and logarithmic models have negative state slopes at every observed data row, whereas cubic and hinge models have small positive slopes at a few rows. The sigmoid has a positive damping schedule by construction, but is less accurate locally. Those alternatives represent explicit accuracy-versus-shape tradeoffs. There is no claim of global stability, exact mechanisms, or validity beyond the observed operating envelope.

The files in models/ contain the full candidate-specific interpretation and limitations. References to Ljung, Friedman, and Baker/Graves-Morris are explicitly cited from memory; no claim is made that those bibliography entries were checked. The official SciPy least_squares API documentation was fetched to verify the trust-region reflective method. Only a few algorithm facts were used from that documentation; the fitted values and performance numbers come entirely from supplied data and the recorded scripts.
