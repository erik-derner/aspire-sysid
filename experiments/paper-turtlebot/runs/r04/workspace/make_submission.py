import json,os
import fit_models as fm
import refine_models as rm
import theta_models as tm
BASE=json.load(open('fit_results.json'));REF=json.load(open('refine_results.json'));THETA=json.load(open('theta_results.json'))
units={'gf':'-','ga':'-','bf':'m/s','ba':'rad/s','df':'m/s','da':'rad/s','ca':'s^2/rad^2','gw':'-','ell':'m','dw':'m/s'}
descriptions={
 'gf':'Forward-command gain; estimated jointly by the rollout fit described below.',
 'ga':'Angular-command gain; estimated jointly by the rollout fit described below.',
 'bf':'Constant forward-speed offset; this is an empirical offset, not an independently established actuator bias.',
 'ba':'Constant angular-rate offset; this is an empirical offset, not an independently established actuator bias.',
 'df':'Nonnegative forward-command threshold in `Max(v_f-df,0)`; estimated jointly, not an independently measured motor dead band.',
 'da':'Nonnegative angular-command threshold in `sign(v_a)*Max(Abs(v_a)-da,0)`; estimated jointly, not an independently measured motor dead band.',
 'ca':'Cubic angular-response coefficient in `ca*v_a**3`; estimated jointly as a static nonlinear correction.',
 'gw':'Shared wheel-command gain in the symmetric wheel-response hypothesis; estimated jointly.',
 'ell':'Effective wheel separation used in constructing and differencing wheel commands; estimated jointly, not a measured geometric dimension. Radians are dimensionless in this wheel conversion.',
 'dw':'Symmetric wheel-speed threshold; estimated jointly, not an independently measured motor dead band.'}
models=[
 ('RectifiedEuler',THETA['rectified_euler'],'theta_models.py','rectified_euler',(1,0,0)),
 ('AffineArc',REF['linear_midpoint_x'],'refine_models.py','linear_midpoint',(1,0,0)),
 ('TurnDeadzone',BASE['deadzone_turn'],'fit_models.py','deadzone_turn',(1,1,.15)),
 ('CubicArc',REF['cubic_turn_weighted'],'refine_models.py','cubic_turn',(1,.35,.05)),
 ('WheelDeadzone',BASE['wheel_deadzone'],'fit_models.py','wheel_deadzone',(1,1,.15)),
]
ref='Standard planar unicycle/nonholonomic kinematics; reference recalled from memory, not checked online: R. M. Murray, Z. Li and S. S. Sastry, A Mathematical Introduction to Robotic Manipulation (1994).'
base_origin='The geometry came from differential-drive physical reasoning, preserving translation invariance and omitting absolute-position terms. PLAN.md records the families before fitting. Helper block regressions found little transferable forward nonlinearity, near-zero lateral slip and strong switching transients. I compared affine Euler and exact-arc kinematics, cubic and dead-zone angular maps, smooth tanh turning, wheel dead zones, lateral slip, command coupling, forward saturation and fitted integration angle. The latter alternatives did not consistently improve trajectory-held-out `x` error and were not retained.'
base_limit='Only three training trajectories and nonnegative `v_f` commands are available; reverse driving is not identified. The observed ranges are `0.0000343124 <= v_f <= 0.2981556034` m/s and `-0.9481475363 <= v_a <= 0.9411606268` rad/s in data/train.csv. Restrict use to similar commands and approximately `5` s rollouts. No actuator velocity or previous input is available as state; all candidates omit the observed switching lag. Parameters therefore describe effective input-to-odometry motion rather than independently established physical constants. Logged pose noise and slowly correlated residuals remain unresolved. `phi_next` is intentionally unwrapped; sine and cosine preserve heading periodicity. Accurate long-duration or high-speed motion is not established.'
os.makedirs('models',exist_ok=True)
for label,r,script,fam,weights in models:
 if fam=='rectified_euler':F='gf*Max(v_f-df,0)';W='ga*v_a+ba'
 elif fam=='deadzone_turn':F='gf*v_f+bf';W='ga*sign(v_a)*Max(Abs(v_a)-da,0)+ba'
 elif fam=='cubic_turn':F='gf*v_f+bf';W='ga*v_a+ba+ca*v_a**3'
 elif fam=='wheel_deadzone':
  right='gw*sign(v_f+ell*v_a/2)*Max(Abs(v_f+ell*v_a/2)-dw,0)'
  left='gw*sign(v_f-ell*v_a/2)*Max(Abs(v_f-ell*v_a/2)-dw,0)'
  F=f'(({right})+({left}))/2+bf';W=f'(({right})-({left}))/ell+ba'
 else:F='gf*v_f+bf';W='ga*v_a+ba'
 if fam=='rectified_euler':ex={'x_next':f'x+Ts*({F})*cos(phi)','y_next':f'y+Ts*({F})*sin(phi)','phi_next':f'phi+Ts*({W})'}
 else:ex={'x_next':f'x+Piecewise((Ts*({F})*cos(phi), Eq(({W}),0)), (({F})*(sin(phi+Ts*({W}))-sin(phi))/({W}), True))','y_next':f'y+Piecewise((Ts*({F})*sin(phi), Eq(({W}),0)), (({F})*(cos(phi)-cos(phi+Ts*({W})))/({W}), True))','phi_next':f'phi+Ts*({W})'}
 params=[{'name':n,'value':float(v),'unit':units[n],'type':'fitted','description':descriptions[n]} for n,v in zip(r['names'],r['parameters'])]
 params.append({'name':'Ts','value':.2,'unit':'s','type':'fixed','description':'Sampling period `Ts = 0.2` s specified in TASK.md; fixed, not estimated.'})
 names,start,lo,hi=fm.SPECS[fam]
 starts='; '.join(f'`{n} = {v}`'+(' '+units[n] if units[n]!='-' else '') for n,v in zip(names,start))
 bounds='; '.join(f'`{l} <= {n} <= {h}`'+(' '+units[n] if units[n]!='-' else '') for n,l,h in zip(names,lo,hi))
 if weights==(1,0,0):criterion='Sum of squared `x` rollout errors, because `x` is the scored output; `y` and `phi` are simulated freely but their errors are not included in fitting.'
 else:criterion=f'Sum of squared `x` rollout errors plus squared weighted `y` and unwrapped `phi` errors. The multiplier on `y` error is `{weights[1]}`; the multiplier on `phi` error is `{weights[2]}` m/rad. These fixed weights were chosen to retain orientation and planar-motion information while '+('emphasizing the scored `x` output.' if weights[1]<1 else 'putting a heading error onto an approximate displacement scale. This is a sensitivity scaling, not a measured noise variance.')
 criterion+=' Every rollout starts at a logged pose, then uses only commands for `25` steps (`5` s); errors at all steps have equal weight. The optimization is an output-error criterion, not a regression on noisy pose derivatives.'
 method='Bound-constrained nonlinear least squares with scipy.optimize.least_squares, using its trust-region reflective algorithm and finite-difference Jacobian. It is suitable for the small nonlinear rollout parameter vector; ordinary least squares would not minimize the free-run criterion. All fitted parameters were estimated together in one optimization using all training trajectories. Numerical starts: '+starts+'. Starts encode approximately unity speed gains with small offsets and modest nonlinearities, based on exploratory block motion and physically plausible response. Bounds: '+bounds+'. Bounds prevent implausible gains and poorly conditioned searches; they are regularizing assumptions, not independent measurements. Settings: `max_nfev = '+str(350 if script=='fit_models.py' else 400)+'`, `ftol = 1e-10`, `xtol = 1e-10`, `gtol = 1e-10`, and `x_scale = "jac"`. All these solver settings are dimensionless. No random numbers are used and no seed applies. For validation only, I repeated fitting on each pair of trajectories from the same starts and rolled out the omitted trajectory; these validation fits are not the submitted values. Running the named script from the working directory reproduces this candidate in its result JSON; imported local modules are dependencies.'
 cv=r['cv_x'];train=r['training']['x']
 common=f' Training rolling-window `x` RMSE is `{train:.8f}` m on all three training trajectories; pooled leave-one-trajectory-out rolling-window `x` RMSE is `{cv:.8f}` m. These are local diagnostics, not test scores.'
 if fam=='rectified_euler':
  family='Rectified static-command unicycle with forward-Euler discretization. '+ref
  interp='The states `x` and `y` are planar positions in m, and `phi` is heading in rad. Inputs `v_f` and `v_a` are forward and angular commands in m/s and rad/s. `Ts` is the sample period in s. `gf*Max(v_f-df,0)` is a nonnegative effective forward speed; `gf` scales the command and `df` suppresses small commands. `ga*v_a+ba` is effective angular rate. `cos(phi)` and `sin(phi)` project forward displacement onto the world axes. Euler integration uses the beginning-of-step heading.'
  origin=base_origin+' The forward threshold was tried after affine fits produced a small negative low-command speed. Rectification prevents artificial reverse motion and gave the lowest pooled held-out `x` RMSE among the explored candidates. Euler discretization outperformed anticipatory arc integration for this short-horizon approximation, plausibly because it partly offsets missing switching lag; that explanation is not an identified delay mechanism.'+common
  limit=base_limit+' The forward threshold is weakly identifiable near the small-command boundary. Euler integration neglects within-step rotation and is not expected to remain accurate for large angular increments. Its fitted angular gain compromises between steady response and omitted transient response.'
 elif fam=='linear_midpoint':
  family='Affine static-command unicycle with exact zero-order-hold circular-arc integration. '+ref
  interp=f'`x`, `y`, `phi`, `v_f`, `v_a` and `Ts` have the meanings and units in TASK.md. The effective forward speed is `{F}` m/s and the effective angular rate is `{W}` rad/s. The gains `gf` and `ga` scale commands; `bf` and `ba` are empirical constant speed offsets. The sine/cosine differences integrate constant-speed circular motion exactly over `Ts`; `Piecewise` uses the straight-line limit when `{W} = 0`. No lateral velocity is modeled.'
  origin=base_origin+' This keeps the most conservative command map and tests whether exact finite-turn geometry helps. The fitting script calls this family `linear_midpoint`, but uses the midpoint projection multiplied by sinc, which is mathematically identical to the submitted exact arc.'+common
  limit=base_limit+' A negative effective speed can occur at very low forward command because of the fitted offset; it represents an approximation and is not evidence of reverse actuation. Exact arc integration assumes instantaneous constant effective velocities during each sample, which the switching residuals contradict.'
 elif fam=='deadzone_turn':
  family='Dead-zone static angular-response unicycle with exact circular-arc integration. '+ref
  interp=f'`x`, `y`, `phi`, `v_f`, `v_a` and `Ts` have the meanings and units in TASK.md. Forward speed is `{F}` m/s. Angular rate is `{W}` rad/s: `da` removes a symmetric command dead band, `sign(v_a)` restores turn direction, `ga` scales the excess, and `ba` is an empirical angular bias. `bf` is an empirical forward bias and `gf` a forward gain. The sine/cosine differences integrate constant rates; `Piecewise` supplies the straight-line limit at zero angular rate.'
  origin=base_origin+' Angular block residuals suggested a sign-dependent deficit at small commands, motivating the dead-zone operator by physical reasoning rather than symbolic search. Joint planar/heading fitting retains the effect more strongly than `x`-only fitting; this candidate is a physically distinct alternative if orientation accuracy or longer free runs matters.'+common
  limit=base_limit+' The sharp threshold is a model hypothesis, not proven stiction. A smooth threshold and omitted actuator lag could explain similar observations. Small commands still permit the fitted bias to turn the robot; extrapolation of that bias is unsafe.'
 elif fam=='cubic_turn':
  family='Low-order polynomial static angular-response unicycle with exact circular-arc integration. '+ref
  interp=f'`x`, `y`, `phi`, `v_f`, `v_a` and `Ts` have the meanings and units in TASK.md. Forward speed is `{F}` m/s. Angular rate is `{W}` rad/s. `gf` and `ga` are command gains, `bf` and `ba` empirical biases, and `ca*v_a**3` is a smooth odd correction that changes gain with angular-command magnitude; it has no separately established physical mechanism. The exact sine/cosine arc expressions integrate these rates and `Piecewise` handles the zero-rate limit.'
  origin=base_origin+' The cubic angular basis came from a physically selected odd-polynomial library after angular residuals showed command dependence. Block diagnostic cubic regression modestly improved held-out angular fit, but unconstrained forward cubic maps and command coupling did not transfer well. I retained only the angular cubic term, using a scored-output-weighted fit. This was parametric nonlinear regression, not gplearn or PySINDy search.'+common
  limit=base_limit+' The polynomial is a local response approximation only; the fitted negative cubic correction can eventually reverse the response at commands outside the observed range. Its held-out `x` advantage over affine kinematics is not established, so it is not recommended.'
 else:
  family='Symmetric wheel-level dead-zone differential-drive kinematics with exact circular-arc integration. '+ref
  interp='`x`, `y`, `phi`, `v_f`, `v_a` and `Ts` have the meanings and units in TASK.md. The right and left wheel commands are `v_f+ell*v_a/2` and `v_f-ell*v_a/2` in m/s, taking radians dimensionless. Each wheel follows `gw*sign(q)*Max(Abs(q)-dw,0)`, where `q` denotes its wheel command, `gw` is the common gain and `dw` the symmetric speed threshold. The mean of the two responses plus `bf` gives forward speed; their difference divided by `ell` plus `ba` gives angular rate. `ell` is an effective wheel separation, not a measured width. The exact arc integration and its zero-rate branch project motion onto the world axes.'
  origin=base_origin+' Wheel command inversion and response averaging came from differential-drive mechanics. A shared wheel threshold was a guessed physical explanation for nonlinear turning, offered instead of unrestricted forward/angular coupling. The hypothesis was retained as a distinct interpretable mechanism despite modestly worse held-out `x` error; it is not claimed to be established by these data.'+common
  limit=base_limit+' Wheel radius, actual wheel separation and individual-wheel behavior cannot be independently established from the logged pose alone. In particular `ell` and `dw` can trade off and validation estimates were unstable. This family assumes identical wheel responses; asymmetric friction, slip and wheel dynamics are absent. It is not recommended over the simpler calibrated model.'
 obj={'expressions':ex,'parameters':params,'estimation':{'criterion':criterion,'data':'data/train.csv, all three trajectories, all rows. Heading was unwrapped independently per trajectory. Each trajectory has `150` samples. Starts are rows `0` through `124` inclusive in each trajectory (zero-based), giving `375` overlapping training windows with `25` within-trajectory transitions each. No window crosses a trajectory boundary. Later rows contribute targets; the final input has no successor and is not used. Every window uses its logged initial state without smoothing or later pose correction. No data were discarded for fitting beyond the need for a complete window.','method':method,'script':script},'discussion':{'family':family,'interpretation':interp,'origin':origin,'limitations':limit}}
 with open('models/'+label+'.json','w') as f:json.dump(obj,f,indent=2)
order=[q[0] for q in models]
reason='Recommend `RectifiedEuler`: its pooled leave-one-trajectory-out `25`-step (`5` s) rolling-window `x` RMSE was `0.02906545` m, the lowest among explored model families, while retaining four interpretable parameters and preventing artificial negative forward speed at tiny nonnegative commands. The simpler proportional Euler fit was almost tied (`0.02908078` m), so the threshold benefit is small, not statistically established. Exact arcs, nonlinear angular response, and wheel thresholds did not improve this held-out scored-output metric. Actual test trajectories and test scores were not available; overlapping-window and three-trajectory validation limits confidence.'
json.dump({'order':order,'recommended':order[0],'reason':reason},open('models/pool.json','w'),indent=2)
