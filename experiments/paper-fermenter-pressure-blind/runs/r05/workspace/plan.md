Identification plan (before fitting)

1. Inspect ranges, input excitation, time evolution and consistency of `dy` with differences of `y`. Units are unknown throughout.
2. Fit an affine continuous-time state-space baseline by ordinary least squares.
3. Fit sparse low-degree polynomial vector fields, including state-input interactions, by scaled least squares and sparse term selection.
4. Try nonlinear relaxation structures: input-dependent equilibrium and damping, with polynomial, rational or saturating input effects. Consider power-law state dependence if data support it; no physical interpretation is assumed.
5. Use derivative residual correlations and full-trajectory classical RK4 rollouts (5 s, inputs held at the left endpoint) to discriminate structures and guide revisions. Consider trajectory-error parameter refinement where derivative fitting and rollout disagree.
6. Use data/train.csv for initial fitting and data/val.csv for comparisons. Any final combined-data fit will be explicitly reported. Deliver only defensible structurally distinct candidates, not a sweep of coefficient settings. No test data are accessed.
