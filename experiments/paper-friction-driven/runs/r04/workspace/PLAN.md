# Identification plan (written before parameter fitting)

1. Fit a physically motivated torque balance: voltage gain, viscous drag, sinusoidal gravitational torque, and Coulomb friction regularized with `tanh(omega/vs)`. Compare a linear restoring torque and a sine restoring torque. Use ordinary least squares on moving samples for initialization, then nonlinear least squares on open-loop angle trajectories.
2. Fit a Stribeck extension with speed-dependent friction; retain it only if residuals or simulation improvement justify its added flexibility.
3. Fit an explicit sticking/dead-zone family. Use a continuous force dead zone near zero speed, blended into kinetic friction away from zero, to retain static equilibria without a discontinuous sign switch that chatters under the required RK4 integrator.
4. Examine moving-sample derivative and trajectory residuals for nonlinear motor gain, angle dependence, asymmetric friction and nonlinear drag. Try constrained extra terms only when physically defensible or with an explicit mathematical interpretation. Sparse linear library regression is an alternative diagnostic to unconstrained symbolic regression; unconstrained search is not necessary if torque-balance families explain the residuals.

Use training trajectories for fitting and validation trajectories for structural comparison. The final pool will contain structurally distinct, defensible families, not multiple parameter perturbations. All reported trajectory errors use the task's zero-order-held inputs and one classical RK4 step per 0.01 s sample. No test data are accessed.
