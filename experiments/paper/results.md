# Results of the experiments of the manuscript

Written by `experiments/paper/collect_results.py`; do not edit. Entries are mean ± sample standard deviation over the runs with a finite value (k of N); S is the pooled RMSE of the simulated output on the test data.

## Runs

| Experiment | Task | Attempted | Delivered | Eligible | Outcomes | Leak-scan findings | Dates (UTC) |
|---|---|---|---|---|---|---|---|
| paper-turtlebot | turtlebot | 5 of 5 | 5 | 5 | completed 5 | 4 | 2026-10-07 |
| paper-turtlebot-blind | task-kt5o | 5 of 5 | 5 | 5 | completed 5 | 4 | 2026-10-07 |
| paper-friction-driven | friction-driven | 5 of 5 | 5 | 5 | completed 5 | 5 | 2026-10-09 |
| paper-friction-driven-blind | task-jdhj | 5 of 5 | 5 | 5 | completed 5 | 3 | 2026-10-08 |
| paper-fermenter-pressure | fermenter-pressure | 5 of 5 | 5 | 5 | completed 5 | 0 | 2026-10-08 |
| paper-fermenter-pressure-blind | task-qtqm | 5 of 5 | 5 | 5 | completed 5 | 0 | 2026-10-08 |

## Errors

| Experiment | Unit | Training error (recommended) | S (recommended, practical selection) | Lowest S in the pool (oracle-based selection on test data) | Pool sizes | Median run |
|---|---|---|---|---|---|---|
| paper-turtlebot | m | 0.03974 ± 0.00066 (5 of 5) | 0.0430 ± 0.0010 (5 of 5) | 0.0382 ± 0.0016 (5 of 5) | 6, 4, 6, 5, 4 | r03 |
| paper-turtlebot-blind | m | 0.0394 ± 0.0014 (5 of 5) | 0.0401 ± 0.0015 (5 of 5) | 0.0365 ± 0.0019 (5 of 5) | 3, 3, 4, 4, 6 | r05 |
| paper-friction-driven | rad | 0.0511 ± 0.0085 (5 of 5) | 0.0417 ± 0.0070 (5 of 5) | 0.0279 ± 0.0075 (5 of 5) | 6, 3, 6, 4, 3 | r02 |
| paper-friction-driven-blind | rad | 0.0459 ± 0.0096 (5 of 5) | 0.0408 ± 0.0079 (5 of 5) | 0.0387 ± 0.0067 (5 of 5) | 3, 3, 3, 4, 3 | r03 |
| paper-fermenter-pressure | bar | 0.02530 ± 0.00078 (5 of 5) | 0.02324 ± 0.00059 (5 of 5) | 0.02306 ± 0.00046 (5 of 5) | 4, 3, 4, 5, 3 | r05 |
| paper-fermenter-pressure-blind | bar | 0.0250 ± 0.0024 (5 of 5) | 0.02247 ± 0.00098 (5 of 5) | 0.02228 ± 0.00072 (5 of 5) | 4, 6, 5, 5, 4 | r04 |

## Compared methods (PySINDy and PySR)

| Task | Model | Eligible | Fitted parameters | Training error | Test score S |
|---|---|---|---|---|---|
| turtlebot | ReferenceSindy | True | 3 | 0.2217 | 0.214 |
| turtlebot | ReferenceSindyThreshold | True | 55 | 0.04459 | 0.153 |
| turtlebot | PySR, default setting (5 seeds) | 5 of 5 | 8, 8, 6, 7, 7 | 0.065 ± 0.024 (5 of 5) | 0.0504 ± 0.0068 (5 of 5) |
| turtlebot | PySR, matched setting (5 seeds) | 5 of 5 | 11, 12, 14, 8, 11 | 0.0263 ± 0.0033 (5 of 5) | 0.056 ± 0.013 (5 of 5) |
| friction-driven | ReferenceSindy | False | 8 | 0.1957 | 0.2668 |
| friction-driven | ReferenceSindyThreshold | False | 10 | 0.1934 | 0.2692 |
| friction-driven | PySR, default setting (5 seeds) | 0 of 5 | 4, 4, 4, 4, 4 | 0.13909 ± 0.00017 (5 of 5) | 0.14404 ± 0.00098 (5 of 5) |
| friction-driven | PySR, matched setting (5 seeds) | 0 of 5 | 5, 6, 6, 5, 6 | 0.0666 ± 0.0070 (5 of 5) | 0.0363 ± 0.0039 (5 of 5) |
| fermenter-pressure | ReferenceSindy | True | 0 | 0.402 | 0.2631 |
| fermenter-pressure | ReferenceSindyThreshold | True | 10 | 0.0309 | 0.02836 |
| fermenter-pressure | PySR, default setting (5 seeds) | 5 of 5 | 3, 5, 4, 4, 3 | 0.0489 ± 0.0056 (5 of 5) | 0.0418 ± 0.0054 (5 of 5) |
| fermenter-pressure | PySR, matched setting (5 seeds) | 5 of 5 | 5, 1, 5, 4, 5 | 0.10 ± 0.11 (5 of 5) | 0.075 ± 0.063 (5 of 5) |

## Formal requirements

Outcomes of the harness's verification: proof (satisfied), counterexample (demonstrated violation, excludes the candidate), inconclusive or unavailable (unresolved). Requirements stated in natural language are not listed; a human assesses them.

| Experiment | Candidates evaluated | Excluded by requirements | Eligible | Runs with an excluded candidate | Runs with an excluded recommended model |
|---|---|---|---|---|---|
| paper-turtlebot | 25 | 0 | 25 | 0 | 0 |
| paper-turtlebot-blind | 20 | 0 | 20 | 0 | 0 |
| paper-friction-driven | 22 | 0 | 22 | 0 | 0 |
| paper-friction-driven-blind | 16 | 0 | 16 | 0 | 0 |
| paper-fermenter-pressure | 19 | 0 | 19 | 0 | 0 |
| paper-fermenter-pressure-blind | 24 | 0 | 24 | 0 | 0 |

| Experiment | Requirement | All evaluated candidates | Recommended candidates |
|---|---|---|---|
| paper-friction-driven | R1 | proof 22 | proof 5 |
| paper-friction-driven | R2 | inconclusive 17, proof 5 | inconclusive 5 |
| paper-friction-driven | R3 | inconclusive 19, proof 3 | inconclusive 5 |
| paper-fermenter-pressure | R1 | assessed by the human 19 | assessed by the human 5 |
| paper-fermenter-pressure | R2 | assessed by the human 19 | assessed by the human 5 |
| paper-fermenter-pressure | R3 | assessed by the human 19 | assessed by the human 5 |
| paper-fermenter-pressure | R4 | assessed by the human 19 | assessed by the human 5 |
| paper-fermenter-pressure | R5 | assessed by the human 19 | assessed by the human 5 |

| Experiment | Run | Excluded candidates (violated requirements) | Recommended model excluded |
|---|---|---|---|

| Task | Models of the tool | Models with a demonstrated violation | Violated requirements |
|---|---|---|---|
| turtlebot | PySINDy (2) | 0 | - |
| turtlebot | PySR, default setting (5) | 0 | - |
| turtlebot | PySR, matched setting (5) | 0 | - |
| friction-driven | PySINDy (2) | 2 | R2 |
| friction-driven | PySR, default setting (5) | 5 | R2 |
| friction-driven | PySR, matched setting (5) | 5 | R2 |
| fermenter-pressure | PySINDy (2) | 0 | - |
| fermenter-pressure | PySR, default setting (5) | 0 | - |
| fermenter-pressure | PySR, matched setting (5) | 0 | - |

## Pools

| Experiment | Pool size | Evaluated | Distinct structures | Rank-deficient | Fitted parameters (recommended) |
|---|---|---|---|---|---|
| paper-turtlebot | 5.0 ± 1.0 | 5.0 ± 1.0 | 5.0 ± 1.0 | 0 ± 0 | 2.40 ± 0.89 |
| paper-turtlebot-blind | 4.0 ± 1.2 | 4.0 ± 1.2 | 4.0 ± 1.2 | 0.20 ± 0.45 | 9.6 ± 5.9 |
| paper-friction-driven | 4.4 ± 1.5 | 4.4 ± 1.5 | 4.4 ± 1.5 | 0.20 ± 0.45 | 7.6 ± 1.7 |
| paper-friction-driven-blind | 3.20 ± 0.45 | 3.20 ± 0.45 | 3.20 ± 0.45 | 0.20 ± 0.45 | 8.4 ± 1.5 |
| paper-fermenter-pressure | 3.80 ± 0.84 | 3.80 ± 0.84 | 3.80 ± 0.84 | 0 ± 0 | 5.6 ± 1.1 |
| paper-fermenter-pressure-blind | 4.80 ± 0.84 | 4.80 ± 0.84 | 4.80 ± 0.84 | 0.40 ± 0.55 | 19.0 ± 2.2 |

## Tools (runs of the experiment in which the event occurred)

| Experiment | SR package executed | Web search | Web fetch | Package installed | Helper started |
|---|---|---|---|---|---|
| paper-turtlebot | 0 | 3 | 2 | 0 | 5 |
| paper-turtlebot-blind | 0 | 5 | 1 | 0 | 5 |
| paper-friction-driven | 0 | 5 | 0 | 5 | 4 |
| paper-friction-driven-blind | 0 | 5 | 0 | 3 | 4 |
| paper-fermenter-pressure | 0 | 5 | 3 | 4 | 4 |
| paper-fermenter-pressure-blind | 0 | 4 | 1 | 2 | 5 |

## Cost

| Experiment | Turns | Input tokens | Output tokens | Elapsed time (s) | Cost (USD) | Total cost (USD) |
|---|---|---|---|---|---|---|
| paper-turtlebot | 28.8 ± 3.8 | 561195 ± 118107 | 17770 ± 2469 | 531 ± 158 | 1.31 ± 0.25 | 6.55 |
| paper-turtlebot-blind | 37.0 ± 4.6 | 854380 ± 231041 | 18598 ± 1877 | 685 ± 320 | 1.91 ± 0.47 | 9.55 |
| paper-friction-driven | 36.2 ± 5.5 | 981616 ± 231029 | 21614 ± 3870 | 665 ± 119 | 2.20 ± 0.50 | 11.00 |
| paper-friction-driven-blind | 36.2 ± 5.4 | 928992 ± 216071 | 20189 ± 4252 | 1085 ± 702 | 2.09 ± 0.45 | 10.43 |
| paper-fermenter-pressure | 33.2 ± 4.0 | 882876 ± 210458 | 23066 ± 5308 | 795 ± 126 | 2.01 ± 0.45 | 10.07 |
| paper-fermenter-pressure-blind | 45.4 ± 4.8 | 1217199 ± 209799 | 24506 ± 4861 | 1260 ± 249 | 2.70 ± 0.44 | 13.50 |

Total cost of all runs: 61.10 USD.

## Runs in detail

| Experiment | Run | Outcome | Recommended | Training error | S | Lowest S (oracle) | Pool | Turns | Cost | SR executed | Web searches | Helpers |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| paper-turtlebot | r01 | completed | CalibratedMidpoint | 0.04022 | 0.04172 | 0.03642 (AngularDeadzone) | 6 | 33 | 1.65 | - | 0 | 1 |
| paper-turtlebot | r02 | completed | Euler | 0.03965 | 0.04369 | 0.03746 (AngularDeadZone) | 4 | 29 | 1.33 | - | 2 | 1 |
| paper-turtlebot | r03 | completed | CalibratedEuler | 0.04059 | 0.04275 | 0.03791 (TurnDeadband) | 6 | 28 | 1.23 | - | 1 | 1 |
| paper-turtlebot | r04 | completed | RectifiedEuler | 0.03917 | 0.04431 | 0.04076 (TurnDeadzone) | 5 | 23 | 0.96 | - | 0 | 1 |
| paper-turtlebot | r05 | completed | calibrated_unicycle | 0.03905 | 0.04236 | 0.03821 (angular_deadzone) | 4 | 31 | 1.38 | - | 2 | 1 |
| paper-turtlebot-blind | r01 | completed | FourierMap | 0.0379 | 0.03794 | 0.03664 (RigidPower) | 3 | 36 | 1.97 | - | 2 | 1 |
| paper-turtlebot-blind | r02 | completed | K_deadzone | 0.03849 | 0.0394 | 0.03394 (K_smooth) | 3 | 31 | 1.16 | - | 1 | 1 |
| paper-turtlebot-blind | r03 | completed | FourierRidge | 0.04067 | 0.04154 | 0.03765 (Rational) | 4 | 40 | 2.36 | - | 1 | 1 |
| paper-turtlebot-blind | r04 | completed | CoupledDeadzone | 0.04118 | 0.04153 | 0.03542 (SmoothAngular) | 4 | 35 | 1.83 | - | 2 | 1 |
| paper-turtlebot-blind | r05 | completed | Deadzone | 0.03882 | 0.0399 | 0.03891 (Rational) | 6 | 43 | 2.24 | - | 2 | 1 |
| paper-friction-driven | r01 | completed | HarmonicStiction | 0.05655 | 0.04531 | 0.02604 (AngleDamping) | 6 | 42 | 2.61 | - | 3 | 1 |
| paper-friction-driven | r02 | completed | TwoScaleStick | 0.06156 | 0.04418 | 0.02278 (PeriodicContact) | 3 | 40 | 2.55 | - | 1 | 1 |
| paper-friction-driven | r03 | completed | HarmonicMotorAsymmetric | 0.05203 | 0.04595 | 0.03018 (AngleFriction) | 6 | 28 | 1.37 | - | 2 | 1 |
| paper-friction-driven | r04 | completed | AngleClip | 0.04009 | 0.02924 | 0.0208 (SmoothAngle) | 4 | 34 | 2.35 | - | 2 | 0 |
| paper-friction-driven | r05 | completed | BlendedStiction | 0.04552 | 0.04371 | 0.0397 (ProjectedFriction) | 3 | 37 | 2.12 | - | 2 | 1 |
| paper-friction-driven-blind | r01 | completed | QuinticDamping | 0.04296 | 0.04527 | 0.04527 (QuinticDamping) | 3 | 41 | 2.48 | - | 2 | 1 |
| paper-friction-driven-blind | r02 | completed | HarmonicFriction | 0.0345 | 0.0322 | 0.0322 (HarmonicFriction) | 3 | 41 | 2.59 | - | 2 | 1 |
| paper-friction-driven-blind | r03 | completed | angle_friction | 0.05369 | 0.04491 | 0.04491 (angle_friction) | 3 | 36 | 1.54 | - | 4 | 1 |
| paper-friction-driven-blind | r04 | completed | ShiftedSine | 0.05784 | 0.0492 | 0.03991 (Duffing) | 4 | 28 | 1.76 | - | 2 | 0 |
| paper-friction-driven-blind | r05 | completed | TrigSmooth | 0.04057 | 0.03247 | 0.03139 (Polynomial) | 3 | 35 | 2.06 | - | 3 | 1 |
| paper-fermenter-pressure | r01 | completed | SeriesPipe | 0.02612 | 0.02391 | 0.02301 (ValvePower) | 4 | 39 | 2.58 | - | 1 | 1 |
| paper-fermenter-pressure | r02 | completed | mixed | 0.02617 | 0.02386 | 0.02386 (mixed) | 3 | 34 | 2.34 | - | 2 | 1 |
| paper-fermenter-pressure | r03 | completed | PowerOutlet | 0.02479 | 0.02285 | 0.02285 (PowerOutlet) | 4 | 28 | 1.53 | - | 3 | 0 |
| paper-fermenter-pressure | r04 | completed | GeneralizedDischarge | 0.02458 | 0.02271 | 0.02271 (GeneralizedDischarge) | 5 | 32 | 1.61 | - | 2 | 1 |
| paper-fermenter-pressure | r05 | completed | power_balance | 0.02482 | 0.02287 | 0.02287 (power_balance) | 3 | 33 | 2.01 | - | 1 | 1 |
| paper-fermenter-pressure-blind | r01 | completed | Cubic | 0.02684 | 0.02323 | 0.02286 (LogInteraction) | 4 | 52 | 2.64 | - | 0 | 2 |
| paper-fermenter-pressure-blind | r02 | completed | CubicSparse | 0.02829 | 0.02381 | 0.02324 (HingeSpline) | 6 | 41 | 2.78 | - | 3 | 1 |
| paper-fermenter-pressure-blind | r03 | completed | Cubic | 0.02333 | 0.02177 | 0.02177 (Cubic) | 5 | 49 | 3.38 | - | 2 | 1 |
| paper-fermenter-pressure-blind | r04 | completed | CubicPolynomial | 0.02333 | 0.02177 | 0.02177 (CubicPolynomial) | 5 | 42 | 2.19 | - | 3 | 1 |
| paper-fermenter-pressure-blind | r05 | completed | poly3 | 0.02332 | 0.02177 | 0.02177 (poly3) | 4 | 43 | 2.52 | - | 2 | 1 |

## Numbers of the text

- Runs: 30; with a recommendation 30; with a finite test score of the recommended model 30; termination reasons: the agent sent the completion message DONE and at least one candidate within the pool limit passed the file and expression checks.
- Largest consumption of a run: 52 turns, 2242 s, 3.38 USD.
- Candidates: 126 evaluated, 0 excluded by requirements, 126 eligible; pool sizes 3 to 6; rank-deficient candidates 5.
- Leak-scan findings: 16 in 7 runs.
- Recommended model has the lowest test score of its pool: 10 of 30 runs (turtlebot: 0 of 10; friction-driven: 3 of 10; fermenter-pressure: 7 of 10).
- Mean loss of the recommendation against the lowest test score of the pool: paper-turtlebot: 0.0048 (11 %, 5 runs); paper-turtlebot-blind: 0.0036 (9 %, 5 runs); paper-friction-driven: 0.0138 (33 %, 5 runs); paper-friction-driven-blind: 0.0021 (5 %, 5 runs); paper-fermenter-pressure: 0.0002 (1 %, 5 runs); paper-fermenter-pressure-blind: 0.0002 (1 %, 5 runs).
- Range of the test score of the recommended models: turtlebot: 0.0379 to 0.0443; friction-driven: 0.0292 to 0.0492; fermenter-pressure: 0.0218 to 0.0239.
- Tool use (runs): sr_package_executed 0, sr_package_imported 0, web_search 27, web_fetch 7, install_package 14, helper 27.
- Mean turns per run by experiment: 28.8 to 45.4; mean elapsed time: 8.9 to 21.0 min.
- Total cost 61.10 USD; per eligible candidate 0.48 USD. Dates of the runs (UTC): 2026-10-07, 2026-10-08, 2026-10-09.

## Model families of the recommended candidates

- **paper-turtlebot r01 (CalibratedMidpoint)**: Discrete-time unicycle/differential-drive kinematics with calibrated command response. A general reference for unicycle kinematics is Siciliano, Sciavicco, Villani and Oriolo, Robotics: Modelling, Planning and Control (Springer, 2009), cited from memory without consulting the book during this round. The supplied task, rather than that reference, defines the robot and sampling period. The translation uses the explicit midpoint (second-order Runge-Kutta) direction for a constant command within a sample.
- **paper-turtlebot r02 (Euler)**: Unicycle/differential-drive kinematic model; see Steven M. LaValle, Planning Algorithms (2006), cited from memory without checking the book. Forward-Euler discretization.
- **paper-turtlebot r03 (CalibratedEuler)**: Calibrated unicycle kinematics with forward Euler discretization. Kinematic reference: Steven M. LaValle, Planning Algorithms (2006), section 13.1.2.3, A simple unicycle, and section 13.1.2.2, A differential drive; author-hosted chapter 13 consulted online. Static nonlinear calibration extensions are empirical hypotheses, not claims that this reference specifies the fitted maps.
- **paper-turtlebot r04 (RectifiedEuler)**: Rectified static-command unicycle with forward-Euler discretization. Standard planar unicycle/nonholonomic kinematics; reference recalled from memory, not checked online: R. M. Murray, Z. Li and S. S. Sastry, A Mathematical Introduction to Robotic Manipulation (1994).
- **paper-turtlebot r05 (calibrated_unicycle)**: Calibrated nonholonomic unicycle / differential-drive kinematic model with explicit midpoint translation integration. Frank Dellaert and Seth Hutchinson, Introduction to Robotics and Perception, section 5.2, Motion Model for the Differential Drive Robot (online text; consulted during this round).
- **paper-turtlebot-blind r01 (FourierMap)**: Additive first-harmonic Fourier state map with bilinear input features, integrator state updates, and a separate static dead-zone angle-response map. Unlike the rigid kinematic map, its two coordinate increments have independent fitted coefficients and are not constrained to a shared forward step or midpoint angle. This candidate is defined by its explicit regression library rather than attributed to a particular published system equation.
- **paper-turtlebot-blind r02 (K_deadzone)**: Nonsmooth discrete-time planar kinematics with static dead-zone input nonlinearity (a Hammerstein-type input map followed by geometric integration). The planar geometric part is the unicycle/differential-drive kinematic model discretized with midpoint heading; reference checked: Frank Dellaert and Seth Hutchinson, Introduction to Robotics and Perception, section 5.2, Motion Model for the Differential Drive Robot (roboticsbook.org). This is an analogy for the data, not an assertion of the unknown system identity.
- **paper-turtlebot-blind r03 (FourierRidge)**: Discrete-time nonlinear state-space map with Fourier/polynomial features and regularized nonlinear output-error estimation. The position updates are linear combinations of specified features, not neural-network predictions. The penalty is a centered ridge/Tikhonov penalty; see A. E. Hoerl and R. W. Kennard, Ridge Regression: Biased Estimation for Nonorthogonal Problems, Technometrics (1970), cited from memory without online verification.
- **paper-turtlebot-blind r04 (CoupledDeadzone)**: Discrete-time unicycle-like kinematic model. A relevant general reference is Murray, Li and Sastry, A Mathematical Introduction to Robotic Manipulation (1994), cited from memory, not verified online. Its static response is a coupled dead-zone Hammerstein-type nonlinearity followed by kinematic integration, not a full Hammerstein model with additional dynamic states.
- **paper-turtlebot-blind r05 (Deadzone)**: Unicycle kinematics with a static dead-zone turn nonlinearity. The kinematic backbone is consistent with S. M. LaValle, Planning Algorithms, Cambridge University Press (2006), discussion of differential-drive and nonholonomic vehicle models; bibliographic reference recalled from memory, not independently verified. This reference supports the kinematics, not these empirical input nonlinearities.
- **paper-friction-driven r01 (HarmonicStiction)**: Two-harmonic nonlinear restoring torque with Coulomb-plus-viscous friction and analytic static-friction cancellation. These are physically motivated grey-box ordinary differential equations, not an exact implementation of a named hysteretic friction model. General context, cited from memory without a successfully fetched source: B. Armstrong-Helouvry, P. Dupont and C. Canudas de Wit, 'A survey of models, analysis tools and compensation methods for the control of machines with friction', Automatica 30(7), 1083-1138 (1994). The particular cancellation or clipping expression here was constructed for this task and is not attributed to that survey.
- **paper-friction-driven r02 (TwoScaleStick)**: Regularized Coulomb-viscous friction with a static dead zone and independent sliding/static speed scales. Related friction-model background: B. Armstrong-Helouvry, P. Dupont and C. Canudas de Wit, A survey of models, analysis tools and compensation methods for the control of machines with friction, Automatica 30 (1994), 1083-1138; bibliographic reference recalled from memory, not source-checked. These expressions are phenomenological reductions, not the LuGre model.
- **paper-friction-driven r03 (HarmonicMotorAsymmetric)**: Continuous clipped-force static/Coulomb-friction model with velocity relaxation, harmonic restoring torque, asymmetric friction, and a monotone saturating motor characteristic. Physical dry-friction modeling follows the Coulomb/viscous and static-friction distinctions in B. Armstrong-Helouvry, Control of Machines with Friction (1991), cited from memory, not source-checked. The algebraic regularizations below are proposed approximations, not the exact algorithm of that reference.
- **paper-friction-driven r04 (AngleClip)**: Second-order nonlinear pendulum torque balance with an algebraic projected Coulomb/stiction closure and a trigonometric friction envelope. Background: B. Armstrong-Helouvry, P. Dupont and C. Canudas de Wit, 'A survey of models, analysis tools and compensation methods for the control of machines with friction', Automatica (1994). This bibliographic reference is recalled from memory; the attempted web retrieval did not return usable source text. The custom algebraic closures here are not claimed to be the exact models in that survey.
- **paper-friction-driven r05 (BlendedStiction)**: Memoryless blended static/Coulomb friction with smooth sliding regularization and a pendulum restoring law. This is an empirical continuous blend, not the dynamic LuGre or Dahl model; no friction state is present. References cited from memory, not verified against a retrieved source: D. Karnopp, Computer Simulation of Stick-Slip Friction in Mechanical Dynamic Systems, Journal of Dynamic Systems, Measurement, and Control (1985); B. Armstrong-Helouvry, P. Dupont and C. Canudas de Wit, A survey of models, analysis tools and compensation methods for the control of machines with friction, Automatica (1994).
- **paper-friction-driven-blind r01 (QuinticDamping)**: Continuous-time generalized Duffing-type polynomial oscillator, with restoring acceleration through degree five and smooth velocity damping. The fifth-degree inward term extends a cubic softening oscillator rather than assuming an exact spring law. References: the SciPy reference documentation for `scipy.optimize.least_squares` describes the trust-region reflective method; Steven H. Strogatz, Nonlinear Dynamics and Chaos, is a general oscillator reference. These bibliographic references are cited from memory; attempted web checking returned no usable content, so neither source was verified online in this round. Neither reference establishes the identity or physics of this undisclosed system.
- **paper-friction-driven-blind r02 (HarmonicFriction)**: Nonlinear Fourier oscillator with state-dependent smooth Coulomb-like friction. Related dry-friction simulation reference cited from memory, not independently verified: D. Karnopp, Computer Simulation of Stick-Slip Friction in Mechanical Dynamic Systems, ASME Journal of Dynamic Systems, Measurement, and Control (1985). This is a family-level reference, not a claim that the expression is Karnopp's exact algorithm. SciPy documentation retrieval was attempted but returned no usable text; software settings below report the actual calls, not an externally verified quotation. 
- **paper-friction-driven-blind r03 (angle_friction)**: Trigonometric nonlinear state-space oscillator with position-modulated, regularized Coulomb friction. Friction background: B. Armstrong-Helouvry, P. Dupont and C. Canudas de Wit, A survey of models, analysis tools and compensation methods for the control of machines with friction, Automatica 30(7), 1083-1138 (1994). This bibliographic reference is cited from memory, not verified online; none of the formulas here is asserted to be its exact model.
- **paper-friction-driven-blind r04 (ShiftedSine)**: Continuous-time nonlinear state-space oscillator with sinusoidal restoration and smooth regularized Coulomb-like friction. The combined empirical structure is not attributed to a specific physical apparatus.
- **paper-friction-driven-blind r05 (TrigSmooth)**: Nonlinear trigonometric state-space oscillator with a regularized Coulomb-type velocity resistance. The arctangent is a bounded odd regularization, not an asserted microscopic friction law. This structure was chosen empirically; no particular physical mechanism is supplied by the task.
- **paper-fermenter-pressure r01 (SeriesPipe)**: Lumped gas-storage model with a series combination of fixed viscous line resistance and valve-dependent inertial resistance. This is a mixed linear-quadratic pressure-drop model, solved explicitly for the signed outlet flow. The ideal-gas storage basis is the NASA Glenn Beginner's Guide to Aeronautics, "Equation of State" (page last updated May 13, 2021), read during this round. The isentropic/choked-flow reference is the same guide's "Mass Flow Choking" (page last updated May 13, 2021), also read during this round. Neither source determines the rig's fitted valve characteristic or the empirical smoothing.
- **paper-fermenter-pressure r02 (mixed)**: Lumped isothermal ideal-gas inventory balance with a linear-plus-quadratic (Darcy–Forchheimer-type) series outlet resistance. The linear-plus-quadratic loss analogy, not a literal porous medium, motivates the resistance law; no particular publication was used for this structure.
- **paper-fermenter-pressure r03 (PowerOutlet)**: A one-state grey-box isothermal gas mass-balance model: the inlet term increases stored gas mass and the outlet term removes it. Only effective gains, rather than temperature and volume separately, are identifiable. The ideal-gas storage balance is assumed, not inferred from these data. Grey-box identification reference: Ljung, System Identification: Theory for the User, second edition (1999), cited from memory and not source-checked. The outlet is a regularized signed power-law pressure-flow constitutive relation. It is an empirical interpolation between sublinear orifice-like and linear resistance behavior, rather than an exact compressible-flow formula.
- **paper-fermenter-pressure r04 (GeneralizedDischarge)**: Grey-box lumped isothermal gas-inventory balance with a generalized regularized pressure-power discharge and a monotone rational-power valve characteristic. The common gas-inventory motivation is the ideal-gas equation of state at fixed effective volume and temperature; reference: NASA Glenn Research Center, Equation of State, cited from memory and not source-checked; attempted web retrieval returned no usable page content. The particular valve map and regularization are assumptions of this identification, not formulas supplied by that reference.
- **paper-fermenter-pressure r05 (power_balance)**: Grey-box nonlinear lumped isothermal gas-inventory model with regularized signed power-law outlet flow and an empirical rational valve characteristic. Mass-balance/ideal-gas basis: Bird, Stewart and Lightfoot, Transport Phenomena, second edition (2002), cited from memory without checking; the empirical fractional-power and rational valve laws are modeling choices, not quoted constitutive laws.
- **paper-fermenter-pressure-blind r01 (Cubic)**: Continuous-time polynomial nonlinear state-space regression. Ordinary least squares and prediction-error identification are standard; reference: Ljung, System Identification: Theory for the User, second edition, 1999 (cited from memory, not checked).
- **paper-fermenter-pressure-blind r02 (CubicSparse)**: Sparse polynomial continuous-time state-space vector field, estimated by backward subset selection rather than genetic programming or SINDy. General identification reference: L. Ljung, System Identification: Theory for the User, second edition, Prentice Hall, 1999 (bibliographic reference recalled from memory, not externally checked). 
- **paper-fermenter-pressure-blind r03 (Cubic)**: Continuous-time multivariate polynomial regression, total degree three, used as a nonlinear state equation. Prediction-error identification reference: L. Ljung, System Identification: Theory for the User, second edition, 1999; cited from memory, bibliographic source not checked.
- **paper-fermenter-pressure-blind r04 (CubicPolynomial)**: Continuous-time cubic polynomial state-space vector field. Reference for polynomial right-hand-side libraries: Brunton, Proctor and Kutz, Discovering governing equations from data by sparse identification of nonlinear dynamical systems, arXiv:1509.03580 (2015), related journal DOI 10.1073/pnas.1517384113 (title, authors and DOI checked on the official arXiv abstract page). This run used dense ordinary least squares and manually restricted structures, not the SINDy sparse algorithm.
- **paper-fermenter-pressure-blind r05 (poly3)**: Degree-three polynomial continuous-time nonlinear state-space model, using a complete monomial feature library. Polynomial feature libraries are also used in S. L. Brunton, J. L. Proctor and J. N. Kutz, Discovering governing equations from data by sparse identification of nonlinear dynamical systems, PNAS 113, 3932–3937, 2016, DOI 10.1073/pnas.1517384113 (publisher record checked). This candidate does not use that paper's sparse estimator. 
