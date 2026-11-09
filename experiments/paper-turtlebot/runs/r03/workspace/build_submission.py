"""Re-fit each submitted candidate and write the required JSON files.
Run after fit_models.py, fit_extensions.py, fit_rectified.py to refresh validation reports.
"""
import fit_rectified as fr
fm=fr.fm
import numpy as np,json
from pathlib import Path
OUT=Path('models');OUT.mkdir(exist_ok=True)
base=json.loads(Path('fit_results.json').read_text());base.update(json.loads(Path('extension_results.json').read_text()));base['rectified']=json.loads(Path('rectified_results.json').read_text())
labels={'euler':'CalibratedEuler','saturating':'SaturatedTurn','arc':'CircularArc','rectified':'RectifiedCalibration','deadzone':'TurnDeadband','bilinear':'SpeedTurnCoupling'}
meta={
 'gf':('-', 'Forward command gain; coefficient of `v_f` in effective forward velocity.'),
 'ga':('-', 'Angular command gain; coefficient of `v_a` in effective angular velocity.'),
 'offset':('rad', 'Constant rotation of the displacement direction; an empirical alignment correction, not independently established sensor misalignment.'),
 'phase':('s', 'Coefficient of `v_a` in the displacement-direction correction `phase*v_a`; a local approximation to integration/alignment and unrepresented command transients.'),
 'vbias':('m/s', 'Additive forward-velocity offset before nonnegative rectification.'),
 'wbias':('rad/s', 'Additive angular-velocity offset; its cause is not identified.'),
 'dead':('rad/s', 'Symmetric angular command deadband threshold.'),
 'amp':('rad/s', 'Magnitude approached by effective angular velocity at large positive command.'),
 'slope':('s/rad', 'Inverse angular-command scale of the hyperbolic tangent; the near-zero angular gain is `amp*slope`.'),
 'coupling':('s/m', 'Coefficient of `v_f*v_a` in effective angular velocity; changes angular gain with forward command.')}
paramnames={'euler':['gf','ga'],'arc':['gf','ga','offset'],'rectified':['gf','ga','offset','phase','vbias','wbias'],'deadzone':['gf','ga','offset','phase','dead'],'saturating':['gf','amp','slope'],'bilinear':['gf','ga','coupling']}
family={
 'euler':'Calibrated unicycle kinematics with forward Euler discretization.',
 'arc':'Calibrated unicycle kinematics with exact constant-command circular-arc integration.',
 'rectified':'Piecewise-affine static command calibration followed by a unicycle kinematic update.',
 'deadzone':'Symmetric dead-zone static angular actuator map followed by a unicycle kinematic update.',
 'saturating':'Hyperbolic-tangent saturation static angular actuator map followed by a unicycle kinematic update.',
 'bilinear':'Bilinear command-response grey-box model followed by a unicycle kinematic update.'}
origin={
 'euler':'Physical reasoning supplied translation invariance and the directional factors `cos(phi)` and `sin(phi)`, with angular increment proportional to `v_a`. Two gains permit command-to-odometry scale differences. This was the first compact fitted baseline; no structure search supplied its terms.',
 'arc':'Physical reasoning supplied the unicycle structure; analytically integrating a constant angular rate supplied the midpoint angle and sine-over-angle chord factor. Commands are held for several samples, making this a defensible discretization alternative. A fitted constant direction correction was retained after examining small lateral residuals. Euler and midpoint updates were tried first; the arc model is not claimed to win validation.',
 'rectified':'After Euler, a static affine command map was tried to represent observed command-scale and low-speed residuals. Its negative forward predictions near zero motivated the guessed nonnegative rectifier `Max(gf*v_f+vbias,0)`. Physical reasoning supplied translation invariance and trigonometric projection. The guessed corrections `offset+phase*v_a` permit alignment and local timing effects; they cannot implement actual delay. All choices were manual, not symbolic regression.',
 'deadzone':'Residual diagnostics on command blocks suggested reduced turning at small angular commands, so a symmetric dead zone was tried as an actuator-map hypothesis after Euler and polynomial maps. `sign(v_a)` preserves odd symmetry and `Max(Abs(v_a)-dead,0)` subtracts a threshold. Projection comes from kinematics; `offset+phase*v_a` is a manually proposed direction correction. This is not a proven mechanism.',
 'saturating':'After the fitted cubic angular map had a negative cubic coefficient, the bounded odd function `amp*tanh(slope*v_a)` was tried as a lower-risk alternative to polynomial extrapolation. Trigonometric projection and additive pose updates came from physical reasoning; the choice of hyperbolic tangent was a manually proposed smooth saturation map, not a symbolic-regression result.',
 'bilinear':'Within-command-block residual diagnostics considered a small polynomial library including `v_a`, `v_a**3` and `v_f*v_a`. Forward speed was well described by a proportional map. The three-parameter structure keeps only the angular interaction `v_f*v_a` beyond the baseline; this is manual compact-library comparison, not a claim that an automated sparse-regression algorithm was run. It tests speed-dependent angular command response while preserving zero turning for `v_a = 0`.'}
extra={
 'euler':'The gains also absorb some unrepresented timing effects, so they are not wheel-geometry estimates.',
 'arc':'The exact integration assumption is violated during command-change transients; exact geometry alone did not improve validation over Euler.',
 'rectified':'The angular offset predicts rotation at zero angular command; near-zero angular-command experiments do not determine whether this extrapolation is real. The rectifier avoids reverse motion from the fitted forward offset, but its threshold is weakly resolved.',
 'deadzone':'The threshold may be a surrogate for delay or odometry response. There are few small-angular-command blocks, so a true mechanical dead zone is not established.',
 'saturating':'Only mild curvature is identified in the observed command range. The large-command saturation magnitude and slope can trade off, so extrapolated saturation is poorly determined.',
 'bilinear':'The interaction varies across trajectory-held-out fits and improves full training-trajectory simulation but not 25-step held-out error. It is included as a parsimonious coupled-response alternative, not the recommendation.'}
criterion='Sum of squared multi-step errors `dx**2 + dy**2 + (L*dphi)**2`, where `dx`, `dy` and `dphi` are simulated-minus-logged position and unwrapped-heading errors at each horizon step and `L = 0.2` m/rad is a chosen fixed heading-to-distance weight. It gives position priority while retaining heading supervision for downstream displacement. Each window contains `25` transitions, or `5` s, and simulation is not corrected within a window. This output-error criterion avoids treating noisy pose differences as exact velocities.'
data='`data/train.csv`, all three trajectories and all `450` logged rows. Within each trajectory, zero-based window starts `0, 2, ..., 124` give `63` windows of `25` transitions; thus `189` overlapping windows contribute to fitting. Each window starts from its logged pose; heading is unwrapped separately per trajectory. No transition crosses trajectories. No outliers or trajectories were excluded. Stride `2` samples was chosen to reduce redundant computational work while retaining starts in every command-block phase. All reported validation uses only these training trajectories.'
for f,label in labels.items():
 p=fm.fit(f,[0,1,2]);names=paramnames[f]
 parameters=[{'name':'Ts','value':.2,'unit':'s','type':'fixed','description':'Sampling period `Ts = 0.2` s supplied in TASK.md; used to convert velocity to a one-sample increment.'}]
 for n,val in zip(names,p):
  unit,desc=meta[n];parameters.append({'name':n,'value':float(val),'unit':unit,'type':'fitted','description':desc+' Estimated jointly with the other fitted parameters of this candidate by the stated multi-step criterion.'})
 F='gf*v_f';W='ga*v_a';theta='phi';dist='Ts*'+F
 if f=='saturating':W='amp*tanh(slope*v_a)'
 if f=='bilinear':W='(ga+coupling*v_f)*v_a'
 if f=='rectified':F='Max(gf*v_f+vbias,0)';W='ga*v_a+wbias';theta='phi+offset+phase*v_a';dist='Ts*'+F
 if f=='deadzone':W='ga*sign(v_a)*Max(Abs(v_a)-dead,0)';theta='phi+offset+phase*v_a'
 if f=='arc':
  theta='phi+Ts*ga*v_a/2+offset'
  dist='Piecewise((Ts*gf*v_f*sin(Ts*ga*v_a/2)/(Ts*ga*v_a/2), (Abs(v_a)>wa_eps)), (Ts*gf*v_f, True))'
  parameters.append({'name':'wa_eps','value':1e-8,'unit':'rad/s','type':'fixed','description':'Numerical straight-line cutoff `wa_eps = 1e-8` rad/s, chosen far below observed angular-command magnitudes; avoids division by zero and approximates the analytic sine-over-angle limit.'})
 expr={'x_next':f'x+({dist})*cos({theta})','y_next':f'y+({dist})*sin({theta})','phi_next':f'phi+Ts*({W})'}
 init,bounds=fm.spec[f]
 start=', '.join('`'+n+' = '+str(v)+'`'+(' '+meta[n][0] if meta[n][0]!='-' else '') for n,v in zip(names,init))
 boundsstr=', '.join('`'+str(lo)+' <= '+n+' <= '+str(hi)+'`'+(' '+meta[n][0] if meta[n][0]!='-' else '') for n,lo,hi in zip(names,*bounds))
 method='All fitted parameters were estimated jointly in one bounded nonlinear least-squares step using `scipy.optimize.least_squares`, Trust Region Reflective algorithm (`method = trf`), linear loss and a two-point finite-difference Jacobian. This handles nonlinear rollout dependence directly, unlike ordinary least squares on noisy one-step differences. Starting values: '+start+'. Positive gains near the exploratory observed response were chosen; offsets and extra corrections start at zero or small values so the starting rollout is near kinematics. Constraints: '+boundsstr+'. Broad gain and correction bounds guard against sign reversals and extreme extrapolation; they are modeling assumptions, not confidence intervals. Settings: `max_nfev = 400`; `ftol = 1e-10`, `xtol = 1e-10`, `gtol = 1e-10`. No random numbers or seed were used. The coefficient-selection criterion remained fixed after checking sensitivity to other heading weights. Reference: SciPy documentation, least_squares, Trust Region Reflective method (consulted online); installed SciPy version recorded by the environment is `1.18.1`.'
 interp=f'The states `x` and `y` are planar positions in m and `phi` is heading in rad; `v_f` and `v_a` are forward and angular commands in m/s and rad/s. The update expressions are `{expr["x_next"]}`, `{expr["y_next"]}` and `{expr["phi_next"]}`. They retain the old pose and add a command-driven displacement projected along the indicated heading; the angular expression adds an effective command-driven heading increment. Parameter rows define each coefficient and correction. '+('The sine-over-angle factor shortens the midpoint-directed chord during a turn; its straight-line limit is one. ' if f=='arc' else '')+'`phi` is intentionally not wrapped: sine and cosine make position propagation periodic, and continuous heading avoids wrap discontinuities.'
 cv=float(np.sqrt(np.mean(np.array(base[f]['cv25'])[:,0]**2)));train=base[f]['train25'][0];full=base[f]['full'][0]
 lim='Only nonnegative forward commands were observed: `0.000034312445203 <= v_f <= 0.298155603426382` m/s; angular commands cover `-0.948147536344217 <= v_a <= 0.941160626754347` rad/s, computed on all training rows. Reverse motion and larger commands are not identified. Logged odometry is not independent ground truth, so actuator response cannot be separated uniquely from odometry calibration. The required state has no velocity or command-history memory. Euler residuals at command changes strongly correlate with the missing previous angular command; none of these structures can exactly represent that transient. Three trajectories give limited independent validation; overlapping windows are dependent. '+extra[f]+f' On training-data leave-one-trajectory-out 25-step validation, pooled `x` RMSE is `{cv:.8f}` m; all-data fitted window `x` RMSE is `{train:.8f}` m; full 149-transition training-rollout `x` RMSE is `{full:.8f}` m. These are development diagnostics, not test scores.'
 obj={'expressions':expr,'parameters':parameters,'estimation':{'criterion':criterion,'data':data,'method':method,'script':'build_submission.py'},'discussion':{'family':family[f]+' Kinematic reference: Steven M. LaValle, Planning Algorithms (2006), section 13.1.2.3, A simple unicycle, and section 13.1.2.2, A differential drive; author-hosted chapter 13 consulted online. Static nonlinear calibration extensions are empirical hypotheses, not claims that this reference specifies the fitted maps.','interpretation':interp,'origin':origin[f],'limitations':lim}}
 (OUT/(label+'.json')).write_text(json.dumps(obj,indent=2))
order=list(labels.values())
reason='Recommend `CalibratedEuler`: its two-parameter model has the lowest pooled trajectory-held-out 25-step `x` RMSE among the submitted candidates, approximately `0.02970` m on `data/train.csv`, and little coefficient instability. The bounded saturation alternative is close, but its extra curvature is weakly identified. More complicated command maps improve some full-training-rollout errors, not the intended held-out 5 s prediction. No test score was accessed.'
(OUT/'pool.json').write_text(json.dumps({'order':order,'recommended':'CalibratedEuler','reason':reason},indent=2))
print('Wrote',len(order),'candidates')
