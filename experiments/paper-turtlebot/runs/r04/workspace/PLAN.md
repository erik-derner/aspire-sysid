# Identification plan (written before fitting)

Use only data/train.csv. Inspect trajectory continuity, command ranges, pose noise and wrapped heading first. The sample period is `Ts = 0.2` s from TASK.md.

Planned families:
1. Differential-drive/unicycle kinematics with commanded velocities, and calibrated linear gains/biases. Compare Euler and finite-turn (midpoint or exact arc) discretizations.
2. Body-frame slip/generalized planar kinematics: permit lateral motion or a velocity-direction offset if residuals support it.
3. Nonlinear static command response: low-order polynomial or saturating forward/angular maps, supported by residual trends and held-out trajectory performance.
4. Sparse regression on physically selected trigonometric/input features, if simpler models leave systematic residuals. No unrestricted dependence on absolute position unless data provide strong evidence.

Compare one-step least squares against output-error nonlinear least squares over multiple-step rollouts (principally 25 steps = 5 s), because logged state noise makes differentiation unreliable. Use trajectory holdout and rolling-window validation, without accessing test data. Examine heading and body-frame displacement residuals for command dependence, bias, lateral motion, and temporal correlation. Keep only stable, defensible, structurally different candidates; do not fill the pool with near-duplicate parameter sets. Document exact methods, starts, data and settings in each candidate and reproducible scripts.
