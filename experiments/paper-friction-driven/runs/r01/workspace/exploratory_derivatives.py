"""Derivative-only exploration. Reads only data/train.csv and data/val.csv.
No candidate/final model files are generated. Reproduce with python exploratory_derivatives.py.
"""
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear, least_squares

TS=0.01 # s, specified in TASK.md
FILES={'train':'data/train.csv','val':'data/val.csv'}
D={k:pd.read_csv(v) for k,v in FILES.items()}
OUT=[]
def emit(s=''): OUT.append(str(s))
def rmse(x): return float(np.sqrt(np.mean(np.asarray(x)**2)))
def features(d, family='base', shift=0):
    t=d.theta.to_numpy(); w=d.omega.to_numpy(); u=d.groupby('trajectory').u.shift(shift).to_numpy()
    X=[u,-np.sin(t),-w,-np.sign(w)]; names=['motor','gravity','viscous','coulomb']; units=['rad/(s^2 V)','rad/s^2','1/s','rad/s^2']; lower=[0]*4; upper=[np.inf]*4
    if family=='quadratic_drag': X += [-w*np.abs(w)]; names+=['quadratic']; units+=['1/rad']; lower+=[0]; upper+=[np.inf]
    if family=='angle_drag': X += [-np.cos(t)*w]; names+=['angle_viscous']; units+=['1/s']; lower+=[-np.inf];upper+=[np.inf]
    if family=='angle_friction': X += [-np.cos(t)*np.sign(w)]; names+=['angle_coulomb'];units+=['rad/s^2'];lower+=[-np.inf];upper+=[np.inf]
    if family=='harmonic_gravity': X += [-np.sin(2*t)]; names+=['gravity2'];units+=['rad/s^2'];lower+=[-np.inf];upper+=[np.inf]
    if family=='nonlinear_motor': X += [u**3];names+=['motor3'];units+=['rad/(s^2 V^3)'];lower+=[-np.inf];upper+=[np.inf]
    if family=='asymmetric_friction': X += [-np.ones(len(w))];names+=['moving_bias'];units+=['rad/s^2'];lower+=[-np.inf];upper+=[np.inf]
    return np.column_stack(X), names, units, (lower,upper)
def mask(d,X): return (np.abs(d.omega.to_numpy())>0.5)&np.isfinite(X).all(axis=1)
def describe_parameters(names,units,p): return ', '.join(f'`{n} = {v:.8g}` {u}' for n,u,v in zip(names,units,p))
def fit(family='base',shift=0,target='domega',robust=False):
    X,names,units,bounds=features(D['train'],family,shift); y=D['train'][target].to_numpy();m=mask(D['train'],X)&np.isfinite(y)
    p=lsq_linear(X[m],y[m],bounds=bounds,tol=1e-12).x
    if robust:p=least_squares(lambda p:X[m]@p-y[m],p,bounds=bounds,loss='soft_l1',f_scale=10).x
    return p,names,units

def derivative(d,col):
    vals=np.full(len(d),np.nan)
    for _,g in d.groupby('trajectory',sort=False):
        z=g[col].to_numpy()
        if col=='theta': z=np.unwrap(z)
        vals[g.index]=np.gradient(z,TS,edge_order=1)
    return vals
for d in D.values():
    d['numeric_accel']=derivative(d,'omega'); d['numeric_velocity']=derivative(d,'theta')
    for col in ['u','domega','numeric_accel']:
        for sh in range(-4,5):d[f'{col}_shift{sh}']=d.groupby('trajectory')[col].shift(sh)

emit('DERIVATIVE EXPLORATION; no final model files generated.')
emit('Data: only data/train.csv and data/val.csv. `theta` rad, `omega` rad/s, `u` V, `domega` rad/s^2. Sample period `TS = 0.01` s (TASK.md).')
emit('Moving subset: `Abs(omega) > 0.5` rad/s, selected to exclude near-stick samples, not to characterize static friction.')
emit('Methods: bounded linear least squares (scipy.optimize.lsq_linear), no starting values; all coefficients together; nonnegative basic coefficients. Robust comparison: scipy.optimize.least_squares, soft-L1 residual loss, scale 10 rad/s^2, initialized from bounded least squares. No random seeds apply.')
emit('Error definition throughout: residual `r = domega - prediction` rad/s^2; RMSE = square root of mean squared residual on named subset; mean residual = arithmetic mean of residual. Diagnostic numerical differentiation uses numpy.gradient independently per trajectory; angle unwrapped before differentiation. No reference claims needed: interpretations below are data-based.')
for key,d in D.items():
    m=np.abs(d.omega)>0.5
    emit(f'{key}: {len(d)} samples, {d.trajectory.nunique()} trajectories, {m.sum()} moving samples.')
    for source,target,unit in [('numeric_accel','domega','rad/s^2'),('numeric_velocity','omega','rad/s')]:
        interior=d.groupby('trajectory').cumcount().gt(0)&d.groupby('trajectory').cumcount(ascending=False).gt(0)
        e=d.loc[interior,source]-d.loc[interior,target]
        emit(f'{key} interior derivative identity {source} minus {target}: n={len(e)} samples, RMSE={rmse(e):.9g} {unit}, max absolute error={np.max(np.abs(e)):.9g} {unit}.')
    emit(f'{key} omega grid increment: sorted unique positive differences median={np.median(np.diff(np.unique(np.round(d.omega,9)))):.9g} rad/s; acceleration unique positive differences median={np.median(np.diff(np.unique(np.round(d.domega,8)))):.9g} rad/s^2 (values rounded to 9 decimals for velocity and 8 decimals for acceleration to remove floating roundoff).')

emit('\nBASE AND STRUCTURALLY DISTINCT LINEAR EXTENSIONS (fit train moving rows only; evaluate both files moving rows):')
FAMILIES=['base','quadratic_drag','angle_drag','angle_friction','harmonic_gravity','nonlinear_motor','asymmetric_friction']
RESULT={}
for family in FAMILIES:
    p,names,units=fit(family);RESULT[family]=p
    emit(f'{family}: '+describe_parameters(names,units,p))
    for key,d in D.items():
        X,*_=features(d,family);m=mask(d,X);r=d.domega.to_numpy()-X@p
        emit(f'  {key} moving n={m.sum()} samples RMSE={rmse(r[m]):.7g} rad/s^2; mean residual={np.mean(r[m]):.7g} rad/s^2.')
p,names,units=fit(robust=True)
emit('base robust soft-L1: '+describe_parameters(names,units,p))
for key,d in D.items():
    X,*_=features(d);m=mask(d,X);emit(f'  {key} moving RMSE={rmse(d.domega.to_numpy()[m]-X[m]@p):.7g} rad/s^2.')

emit('\nINPUT ALIGNMENT: u shifted by integer samples separately per trajectory; shift +1 means previous logged u, delay 0.01 s. Current theta/omega retained. Each shift refits train moving rows.')
for shift in range(-4,5):
    p,names,units=fit(shift=shift)
    emit(f'shift={shift} samples ({shift*TS:.3g} s): '+describe_parameters(names,units,p))
    for key,d in D.items():
        X,*_=features(d,shift=shift);m=mask(d,X);emit(f'  {key} moving valid n={m.sum()} samples RMSE={rmse(d.domega.to_numpy()[m]-X[m]@p):.7g} rad/s^2.')

emit('\nTIME-AVERAGED REGRESSORS: supplied acceleration equals central velocity derivative on interiors. If velocity is also central angle derivative, acceleration is a second-difference spanning four sample intervals; physical acceleration then has an approximate triangular smoothing kernel rather than an instantaneous target.')
for width in [1,2,3]:
    matrices={}
    for key,d in D.items():
        X,*_=features(d);sm=np.full_like(X,np.nan)
        # Discrete triangle [1,2,...,width+1,...,2,1], normalized.
        weights=np.r_[np.arange(1,width+2),np.arange(width,0,-1)];weights=weights/weights.sum()
        for _,g in d.groupby('trajectory',sort=False):
            inds=g.index.to_numpy()
            for j in range(4):sm[inds[width:-width],j]=np.convolve(X[inds,j],weights,mode='valid')
        matrices[key]=sm
    X=matrices['train'];m=mask(D['train'],X);p=lsq_linear(X[m],D['train'].domega.to_numpy()[m],bounds=(0,np.inf)).x
    emit(f'Triangular halfwidth={width} samples ({width*TS:.3g} s): '+describe_parameters(['motor','gravity','viscous','coulomb'],['rad/(s^2 V)','rad/s^2','1/s','rad/s^2'],p))
    for key,d in D.items():
        X=matrices[key];m=mask(d,X);emit(f'  {key} moving valid n={m.sum()} samples RMSE={rmse(d.domega.to_numpy()[m]-X[m]@p):.7g} rad/s^2.')

emit('\nBASE RESIDUALS: correlation and equal-frequency bins; each bin reports mean residual, not prediction error magnitude.')
p=RESULT['base']
for key,d in D.items():
    X,*_=features(d);m=mask(d,X);dd=d.loc[m].copy();dd['residual']=d.domega.to_numpy()[m]-X[m]@p
    emit(f'{key}:')
    for col,unit in [('theta','rad'),('omega','rad/s'),('u','V')]:
        corr=np.corrcoef(dd[col],dd.residual)[0,1];emit(f'  Pearson correlation r with {col}={corr:.7g} (dimensionless).')
        cats=pd.qcut(dd[col],6,duplicates='drop')
        for _,g in dd.groupby(cats,observed=True):
            emit(f'  {col} range [{g[col].min():.5g},{g[col].max():.5g}] {unit}, n={len(g)} samples, residual mean={g.residual.mean():.6g} rad/s^2, residual RMSE={rmse(g.residual):.6g} rad/s^2.')
    for tr,g in dd.groupby('trajectory'):
        emit(f'  trajectory {tr}: n={len(g)} moving samples; input kind={"free" if np.all(g.u==0) else "driven"}; residual mean={g.residual.mean():.6g} rad/s^2; RMSE={rmse(g.residual):.6g} rad/s^2.')
    for col,z in [('cos(theta)*omega',np.cos(dd.theta)*dd.omega),('cos(theta)*sign(omega)',np.cos(dd.theta)*np.sign(dd.omega)),('sin(2*theta)',np.sin(2*dd.theta)),('omega*Abs(omega)',dd.omega*np.abs(dd.omega)),('u**3',dd.u**3)]:
        emit(f'  residual Pearson correlation with `{col}`={np.corrcoef(z,dd.residual)[0,1]:.6g} (dimensionless).')

# A coupled nonlinear dissipative drag model with globally positive angle multiplier.
emit('\nPOSITIVE ANGLE-DEPENDENT DAMPING: `motor*u - gravity*sin(theta) - viscous*exp(angle_rate*cos(theta))*omega - coulomb*sign(omega)`. Nonlinear least squares fits all five coefficients, initialized from basic fit and angle_rate=0; positivity bounds on four physical magnitudes; angle_rate bounds [-3,3] dimensionless avoid extreme extrapolation.')
def pred_nonlin(d,p):
    a,g,b,c,h=p;return a*d.u.to_numpy()-g*np.sin(d.theta.to_numpy())-b*np.exp(h*np.cos(d.theta.to_numpy()))*d.omega.to_numpy()-c*np.sign(d.omega.to_numpy())
m=np.abs(D['train'].omega.to_numpy())>0.5
p0=np.r_[RESULT['base'],0.0]
res=least_squares(lambda p:(pred_nonlin(D['train'],p)-D['train'].domega.to_numpy())[m],p0,bounds=([0,0,0,0,-3],[np.inf,np.inf,np.inf,np.inf,3]),max_nfev=1000)
emit(describe_parameters(['motor','gravity','viscous','coulomb','angle_rate'],['rad/(s^2 V)','rad/s^2','1/s','rad/s^2','dimensionless'],res.x))
for key,d in D.items():
    m=np.abs(d.omega.to_numpy())>0.5;emit(f'  {key} moving n={m.sum()} samples RMSE={rmse((d.domega.to_numpy()-pred_nonlin(d,res.x))[m]):.7g} rad/s^2.')
emit('\nINTERPRETATION AND DEFENSIBLE INITIALIZATIONS:')
emit('1. Basic moving balance `motor*u - gravity*sin(theta) - viscous*omega - coulomb*sign(omega)` gives physical starting coefficients above. Moving data do not identify static breakaway torque. Never equate a discontinuous sign friction law with a complete sticking model.')
emit('2. Positive angle-dependent damping above is structurally distinct and globally dissipative. exp multiplier is mathematical modulation, not an established mechanical explanation. The derivative evidence must be checked with open-loop trajectory simulation before accepting.')
emit('3. Angle-dependent Coulomb friction `-(coulomb + angle_coulomb*cos(theta))*sign(omega)` is defensible only if `coulomb >= Abs(angle_coulomb)`; unconstrained extension values above are screening estimates, not final coefficients. Fits that violate this must be projected or refitted. May represent changing friction load, but data alone do not establish that mechanism.')
emit('4. Non-sinusoidal restoring torque `-gravity*sin(theta) - gravity2*sin(2*theta)` is globally restoring on the specified interval when `gravity >= 2*Abs(gravity2)`; screening values above supply starts, not a proof of final validity.')
emit('5. Nonlinear motor `motor*u + motor3*u**3` must satisfy `motor + 3*motor3*u**2 >= 0` throughout required input domain [-10,10] V. Negative unconstrained cubic slopes cannot automatically be submitted; a monotone saturation `gain*voltage_scale*tanh(u/voltage_scale)` is safer, initialized with basic motor gain and voltage_scale=10 V (chosen domain scale, not estimated).')
emit('6. Quadratic dissipative drag `-quadratic*omega*Abs(omega)` has globally correct sign for nonnegative quadratic coefficient. A coefficient hitting zero means these train derivative residuals do not support that extension.')
emit('7. Near-rest sticking extension requires a deadband of net driving torque and a low-speed transition, fitted by simulation rather than extrapolated from selected moving data. Initialize dynamic friction magnitude from basic coulomb, static threshold at the same magnitude, and speed scale 0.2 rad/s (chosen close to encoder velocity grid). Validate carefully: a discontinuity or very steep regularization may be unstable with fixed-step integration.')
emit('Time alignment cannot be resolved solely from a small derivative RMSE advantage: centrally differentiated encoder targets are smoothed and highly quantized; input waveform is also smooth at the sample scale. A delayed or averaged regressor is a diagnostic, not an admissible additional state or a claim of a true physical delay.')
open('exploratory_results.txt','w',encoding='utf-8').write('\n'.join(OUT)+'\n')
print('\n'.join(OUT[:45]))
print('Full results written to exploratory_results.txt')
