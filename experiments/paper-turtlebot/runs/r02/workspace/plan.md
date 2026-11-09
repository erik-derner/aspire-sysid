# Identification plan (recorded before fitting)

Use only data/train.csv. Inspect command timing, wrapped heading increments, measurement noise and trajectories before fitting.

Families to try:
1. Forward-Euler unicycle with fitted forward/angular command scales.
2. Midpoint and exact constant-command unicycle integration with fitted scales and possible angular bias.
3. Static nonlinear command calibration (odd polynomial or smooth saturation) within the constant-command unicycle.
4. Planar body-frame lateral drift and/or heading-harmonic angular correction, only if residuals support these terms.
5. Sparse regression of physically constructed command/heading features as a diagnostic; retain a closed-form candidate only if stable and interpretable.

Start with one-step diagnostics, then nonlinear least squares on overlapping approximately 5 s open-loop windows, and compare leave-one-trajectory-out predictions and complete-trajectory rollouts. Examine residual dependence on commands, heading, and command-block position. Use no unseen data. Prefer small stable structures over high-degree unconstrained expressions. Deliver structurally different defensible candidates, not a sweep of one parameterization. Record actual settings and rejected ideas in the reproduction script/report.
