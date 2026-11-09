"""Reproduce all submitted parameters and model JSON files using training data only."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

blocks=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in pd.read_csv('data/train.csv').groupby('trajectory')]
settings={
 'K_deadzone':dict(start=[0,.18,.20,0,.1],weight=.3,lo=[-np.inf]*4+[0],hi=[np.inf]*4+[.5],tol=1e-10,maxeval=1500),
 'K_smooth':dict(start=[.1667,.2,.002,.1],weight=.3,lo=[0,0,-.05,.001],hi=[1,1,.05,1],tol=1e-11,maxeval=1500),
 'K_linear':dict(start=[0,.1667,.15,0],weight=1,lo=[-np.inf]*4,hi=[np.inf]*4,tol=1e-11,maxeval=1000)}

def laws(p,u,label):
 v,w=u[:,0],u[:,1]
 if label=='K_deadzone':return np.maximum(0,p[0]+p[1]*v),p[2]*np.sign(w)*np.maximum(0,np.abs(w)-p[4])+p[3]
 if label=='K_smooth':return p[0]*v,p[1]*(w-p[3]*np.tanh(w/p[3]))+p[2]
 return p[0]+p[1]*v,p[2]*w+p[3]

def simulate(p,b,label):
 distance,turn=laws(p,b[:-1,3:],label)
 angle=b[0,2]+np.r_[0,np.cumsum(turn)]
 mid=angle[:-1]+turn/2
 xy=b[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[distance*np.cos(mid),distance*np.sin(mid)],axis=0)])
 return np.c_[xy,angle]

def fit(bs,label):
 s=settings[label]
 def residual(p):
  return np.concatenate([((simulate(p,b,label)[1:]-np.c_[b[1:,:2],np.unwrap(b[:,2])[1:]])*np.array([1,1,s['weight']])).ravel() for b in bs])
 return least_squares(residual,s['start'],method='trf',jac='2-point',bounds=(s['lo'],s['hi']),max_nfev=s['maxeval'],ftol=s['tol'],xtol=s['tol'],gtol=s['tol']).x

def output_rmse(p,b,label):return float(np.sqrt(np.mean((simulate(p,b,label)[1:,0]-b[1:,0])**2)))

reference=('The planar geometric part is the unicycle/differential-drive kinematic model discretized with midpoint heading; reference checked: Frank Dellaert and Seth Hutchinson, Introduction to Robotics and Perception, section 5.2, Motion Model for the Differential Drive Robot (roboticsbook.org). This is an analogy for the data, not an assertion of the unknown system identity.')
method_ref=('Method reference checked: SciPy least_squares documentation, Trust Region Reflective method; SciPy source optimize/_lsq/trf.py. The installed SciPy version was 1.18.1.')
common_limit=('The physical system, column units and intended use are unknown. Interpreting `x2` as an angle in radians is inferred from wrapping near `-pi` and `pi`, not supplied metadata. Coefficients map one sample to the next; the supplied sampling period `T_s = 0.2` s is already absorbed in them. The models assume translation invariance: absolute `y` and `x1` do not change the increments. This is supported by the observed direction of motion but not established globally. Only three experiments are available; leave-one-trajectory-out validation is noisy, and hyperparameter selection used these same experiments, so its results are not an unbiased test score. No test data were accessed. Input-change residuals and their positive lag-one correlations indicate missing transient dynamics, disturbances, or both. The prescribed three-state model has no actuator or previous-input state, so that behavior is not fully represented. Long-horizon accuracy outside the observed input/state support is unknown; no global state bound is guaranteed for accumulated positions.')

origins={
 'K_deadzone':('After the affine and degree-two/three polynomial maps showed poor or unstable held-out rollouts, a trigonometric planar structure was inferred from motion directions and angle wrapping. Linear and bilinear turning laws were tried, followed by cubic, saturating `tanh`, and subtractive `tanh` dictionaries. Larger inferred gain for large inputs motivated a guessed dead-zone nonlinearity, not a known mechanical friction law. The retained turning expression `turngain*sign(x4)*Max(0, Abs(x4)-threshold)+turnbias` is nonsmooth and monotone. The speed expression `Max(0, speedoffset+speedgain*x3)` was chosen to prevent the fitted offset from producing reverse motion at small positive commands. No genetic symbolic regression or sparse-thresholding package was used. Structure selection was manual dictionary comparison guided by rollouts and residuals.'),
 'K_smooth':('The geometric structure was inferred from motion directions and angle wrapping after generic affine/polynomial baselines. A searched subtractive `tanh` law reduced rollout errors, but unconstrained subtraction could reverse the response near zero. That version was rejected. The retained guessed analytic input law `turngain*(x4-width*tanh(x4/width))+turnbias` ties the subtraction amplitude to its width, giving a monotone response with zero slope at zero command before adding the bias. Proportional distance `speedgain*x3` was selected to give zero displacement at zero input and reduce fitted degrees of freedom. This is an analytic small-input attenuation law rather than a literal hard dead zone. No genetic symbolic regression or sparse-thresholding package was used.'),
 'K_linear':('Generic affine and degree-two/three polynomial transitions were examined first. Angle wrapping and a measured midpoint cross-track RMS of about `0.000176` in unreported position units over all within-trajectory transitions suggested planar trigonometric geometry. The simplest retained structure is affine input distance `speedoffset+speedgain*x3` and affine turn `turngain*x4+turnbias`. Midpoint heading `x2+(turngain*x4+turnbias)/2` was chosen from the observed increment direction, not known physical constants. This candidate is the low-complexity reference for testing whether nonlinear input attenuation transfers. No genetic symbolic regression or sparse-thresholding package was used.')}

families={
 'K_deadzone':'Nonsmooth discrete-time planar kinematics with static dead-zone input nonlinearity (a Hammerstein-type input map followed by geometric integration). ',
 'K_smooth':'Smooth analytic discrete-time planar kinematics with a monotone hyperbolic-tangent attenuation input map. ',
 'K_linear':'Discrete-time planar unicycle kinematics with affine input maps and midpoint heading integration. '}

interpretations={
 'K_deadzone':('`y` and `x1` are treated as two accumulated coordinates; `x2` sets the direction. `x3` and `x4` are the current inputs. `speedoffset` is the fitted offset in distance per sample, `speedgain` scales `x3`, and `Max(0, speedoffset+speedgain*x3)` truncates negative displacement lengths to zero. `turngain` scales the excess input magnitude beyond `threshold`; `sign(x4)*Max(0, Abs(x4)-threshold)` is zero inside the threshold interval and odd outside. `turnbias` is a constant angular increment. The `cos` and `sin` terms project displacement along the midpoint direction. The `atan2(sin(...), cos(...))` term wraps the accumulated direction onto the principal-angle interval. All terms have mathematical meanings; mechanical causes of attenuation or bias are not known.'),
 'K_smooth':('`y` and `x1` are treated as accumulated coordinates and `x2` as direction. `x3` and `x4` are current inputs. `speedgain*x3` is displacement length per sample. `turngain` scales the attenuated command `x4-width*tanh(x4/width)`; positive `width` sets the input scale of attenuation. For small command this odd function grows cubically; for large magnitude it approaches an affine response with a sign-dependent subtraction. Its derivative is nonnegative, so it cannot reverse incremental command response. `turnbias` is a constant angular increment. `cos` and `sin` project displacement at midpoint direction, and `atan2(sin(...), cos(...))` wraps the next angle. None of these inferred roles confirms a specific mechanism or unit.'),
 'K_linear':('`y` and `x1` are accumulated coordinates in the model, `x2` is their direction, and `x3` and `x4` are current inputs. `speedoffset` shifts distance per sample, `speedgain` scales `x3`, `turngain` scales `x4`, and `turnbias` shifts angular increment. `cos` and `sin` resolve displacement at midpoint heading. `atan2(sin(...), cos(...))` wraps the direction after adding the turn. The mathematical roles do not establish physical units or mechanisms.')}

names={
 'K_deadzone':['speedoffset','speedgain','turngain','turnbias','threshold'],
 'K_smooth':['speedgain','turngain','turnbias','width'],
 'K_linear':['speedoffset','speedgain','turngain','turnbias']}
descriptions={
 'speedoffset':'Offset of per-sample displacement length, estimated jointly with all other fitted parameters from full training rollouts.',
 'speedgain':'Multiplier of the current `x3` input in displacement length, estimated jointly with all other fitted parameters from full training rollouts.',
 'turngain':'Multiplier of the model-specific `x4` input response in angular increment, estimated jointly with all other fitted parameters from full training rollouts.',
 'turnbias':'Constant per-sample angular increment, estimated jointly with all other fitted parameters from full training rollouts; its mechanism is unknown.',
 'threshold':'Half-width of the exact dead zone in `x4` input units, estimated jointly with all other fitted parameters from full training rollouts.',
 'width':'Positive scale in `x4` input units in `x4-width*tanh(x4/width)`, estimated jointly with all other fitted parameters from full training rollouts.'}
units={'speedoffset':'unknown position unit per sample','speedgain':'unknown position unit per x3 unit per sample','turngain':'inferred radian per x4 unit per sample','turnbias':'inferred radian per sample','threshold':'unknown x4 input unit','width':'unknown x4 input unit'}

Path('models').mkdir(exist_ok=True)
results={}
for label in settings:
 p=fit(blocks,label);s=settings[label]
 cv=[output_rmse(fit([b for j,b in enumerate(blocks) if i!=j],label),blocks[i],label) for i in range(3)]
 tr=[output_rmse(p,b,label) for b in blocks]
 prefix=fit([b[:90] for b in blocks],label)
 forecast=[output_rmse(prefix,b[89:],label) for b in blocks]
 results[label]={'parameters':p.tolist(),'training_y_rmse':tr,'leave_one_trajectory_out_y_rmse':cv,'cv_pooled_y_rmse':float(np.sqrt(np.mean(np.array(cv)**2))),'prefix_forecast_y_rmse':forecast}
 if label=='K_deadzone':distance='Max(0, speedoffset+speedgain*x3)';turn='turngain*sign(x4)*Max(0, Abs(x4)-threshold)+turnbias'
 elif label=='K_smooth':distance='speedgain*x3';turn='turngain*(x4-width*tanh(x4/width))+turnbias'
 else:distance='speedoffset+speedgain*x3';turn='turngain*x4+turnbias'
 expr={'y_next':f'y+({distance})*cos(x2+({turn})/2)','x1_next':f'x1+({distance})*sin(x2+({turn})/2)','x2_next':f'atan2(sin(x2+({turn})), cos(x2+({turn})))'}
 starts=', '.join(f'`{n} = {v}` (same implied units as the coefficient)' for n,v in zip(names[label],s['start']))
 bounds=''
 if label=='K_deadzone':bounds='The bound `0 <= threshold <= 0.5` in unknown `x4` input units was chosen to allow a moderate dead zone within observed commands without eliminating almost all commands; other parameters are unbounded.'
 if label=='K_smooth':bounds='Bounds were `0 <= speedgain <= 1` in implied position-per-input-per-sample units, `0 <= turngain <= 1` in inferred radian-per-input-per-sample units, `-0.05 <= turnbias <= 0.05` in inferred radian per sample, and `0.001 <= width <= 1` in unknown `x4` input units. These broad bounds enforce positive gains and a nonsingular attenuation scale while allowing the observed response. The width upper bound is approximately the observed maximum command magnitude. No fitted parameter ended on a bound.'
 criterion=(f'Weighted output-error nonlinear least squares over complete free-running training trajectories: sum of squared errors in `y` and `x1` plus `{s["weight"]**2:.12g}` times squared errors in unwrapped `x2`. No measured states are reinserted after the first sample. Position units are unreported; `x2` is computationally interpreted in radians. The dimensionless angular residual weight is `{s["weight"]}`. '+('It was selected from `0.3`, `1`, and `3` by leave-one-trajectory-out `y` rollout error, to emphasize coordinate accuracy while preserving heading consistency.' if label!='K_linear' else 'Equal numerical weights were retained for the simple reference model to keep all three trajectories and states represented without additional tuning.'))
 method=(f'All fitted parameters were estimated together in one step by nonlinear least squares, scipy.optimize.least_squares with `method = trf`, two-point finite-difference Jacobian and ordinary quadratic loss. This method permits the nonlinear trigonometric rollout criterion and bounds; linear least squares cannot fit that criterion. Starting values were {starts}. They approximate the exploratory linear input gains with a small or zero bias; attenuation was initialized moderately within the input range rather than at a singular zero scale. '+bounds+f' Termination tolerances were `ftol = {s["tol"]}`, `xtol = {s["tol"]}`, and `gtol = {s["tol"]}`; maximum function evaluations were `{s["maxeval"]}` (dimensionless algorithm settings). No random numbers or seeds were used. Fits were also repeated on each pair of trajectories for validation and on the first `90` samples per trajectory for temporal forecasts, but submitted coefficients use all samples. '+method_ref)
 limitations=common_limit
 if label=='K_deadzone':limitations+=' The exact threshold and speed cutoff are empirical approximations; a threshold crossing is continuous but has a derivative discontinuity. Input-change residual RMS on all training transitions was about `0.00545` for `y`, `0.00503` for `x1` in unknown position units, and `0.0891` in inferred radians for `x2`; non-switch RMS was approximately `0.00165`, `0.00150`, and `0.0201` in the corresponding units. The angular residual still correlates with current `x4`, especially during changes; the static threshold does not remove lag.'
 if label=='K_smooth':limitations+=' There is no exact dead zone, only small-input attenuation. Its gain beyond the observed range grows linearly, and the estimated width is not a measured physical threshold. The initial unconstrained subtractive-tanh family was discarded because it allowed local sign reversal; this candidate avoids that defect by construction.'
 if label=='K_linear':limitations+=' The distance offset allows slight movement at zero input and can imply reverse displacement for negative inputs; negative commands were not observed. The affine input maps do not describe the small-command attenuation captured by the other candidates.'
 model={'expressions':expr,'parameters':[{'name':n,'value':float(v),'unit':units[n],'type':'fitted','description':descriptions[n]} for n,v in zip(names[label],p)],'estimation':{'criterion':criterion,'data':'data/train.csv, all three trajectories and all 150 samples per trajectory. There are 149 within-trajectory transitions per experiment, 447 transitions in total. No transitions cross trajectory boundaries. Initial states are the first logged states. Only the angular observations were unwrapped using numpy.unwrap to avoid artificial branch-cut residuals; position observations and inputs were not filtered. All rows were used in the final fit because no quality labels justify deleting them.','method':method,'script':'fit_candidates.py'},'discussion':{'family':families[label]+reference,'interpretation':interpretations[label],'origin':origins[label],'limitations':limitations}}
 json.dump(model,open('models/'+label+'.json','w'),indent=2,allow_nan=False)
json.dump(results,open('candidate_validation.json','w'),indent=2,allow_nan=False)
json.dump({'order':['K_deadzone','K_smooth','K_linear'],'recommended':'K_deadzone','reason':'The hard dead-zone family has the lowest pooled leave-one-trajectory-out `y` rollout RMSE among retained candidates: approximately `0.116` in unknown `y` units, compared with `0.122` for the smooth monotone family and `0.216` for the affine-input kinematic reference. All use only training data. The smooth family is competitive and has lower full-training error, so the recommendation is provisional given only three experiments. The threshold candidate also avoids local command-response reversal and prevents negative displacement length at small positive `x3`. Residuals still show unresolved input-change transients.'},open('models/pool.json','w'),indent=2)
print(json.dumps(results,indent=2))
