import json
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear
from fit_models import accel,simulate,load

# Train only. No validation reading, submission creation, or input-file writes.
df,rows,lens=load('data/train.csv')
y=df.domega.to_numpy(); t=df.theta.to_numpy(); w=df.omega.to_numpy(); u=df.u.to_numpy(); ids=df.trajectory.to_numpy(); n=len(y)
runs=list(df.groupby('trajectory',sort=False))
interior=np.zeros(n,bool); switch=np.zeros(n,bool); switch_near=np.zeros(n,bool)
lag_u={k:u.copy() for k in [-2,-1,0,1,2]}
kin={}; off=0
for gid,g in runs:
 L=len(g); sl=slice(off,off+L); interior[off+2:off+L-2]=True
 changes=np.where(np.abs(np.diff(u[sl]))>0.5)[0]+off+1; switch[changes]=True
 for d in range(-2,3):
  ix=changes+d;ix=ix[(ix>=off)&(ix<off+L)];switch_near[ix]=True
  lag_u[d][sl]=np.roll(u[sl],-d)
 off+=L
move=interior&(np.abs(w)>1)&(~switch_near)
free=move&(u==0); driven=move&(u!=0)
lines=[]
def out(s=''): lines.append(s)
def rmse(z):return float(np.sqrt(np.mean(z*z)))
def metrics(res,mask):return f'n = {mask.sum()} samples; acceleration residual mean = {np.mean(res[mask]):.6g} rad/s^2; acceleration RMSE = {rmse(res[mask]):.6g} rad/s^2'
out('TRAIN-ONLY DERIVATIVE AND STRUCTURE DIAGNOSTICS')
out('Source: data/train.csv only. fit_models.py was imported without executing its main program; only the parameter and training fields of fit_results.json were analyzed. No validation metrics are used. No submission files are created. All reported acceleration residuals are prediction minus logged `domega`; RMSE is sqrt(mean(residual**2)). Angle residuals are simulated `theta` minus logged `theta`.')
out(f'All training: {n} samples across {len(runs)} trajectories; sample period = 0.01 s. Moving-clean subset: `Abs(omega)>1` rad/s, two endpoint samples per trajectory removed and samples within 0.02 s of an input increment exceeding 0.5 V excluded (the logged input is continuously varying, so exact inequality would incorrectly discard nearly all driven samples); {move.sum()} samples. This subset limits numerical sticking and input-transition derivative contamination, not a claim that excluded data are invalid.')
out('TRAJECTORIES: sample count, voltage range (V), unique voltage count, moving count at `Abs(omega)>1` rad/s')
for gid,g in runs: out(f'{gid}: {len(g)} samples; voltage range [{g.u.min():.6g}, {g.u.max():.6g}] V; {g.u.nunique()} unique values; {sum(abs(g.omega)>1)} moving samples')
results=json.load(open('fit_results.json'))
out('\nEXISTING SIMULATION-FITTED FAMILY DERIVATIVE RESIDUALS')
for fam,r in results.items():
 p=np.array(r['p']);pred=np.array([accel(a,b,c,p,int(fam)) for a,b,c in rows]);res=pred-y
 sim=simulate(p,int(fam),rows,lens);keep=np.ones(n,bool);off=0
 for L in lens:keep[off]=False;off+=L
 out(f'Family {fam}: all training derivative '+metrics(res,np.ones(n,bool))+'; moving-clean '+metrics(res,move)+f'; train angle simulation RMSE excluding every trajectory initial sample = {rmse((sim-t)[keep]):.6g} rad.')
 if fam in ['1','5','6']:
  for label,m in [('positive motion',move&(w>0)),('negative motion',move&(w<0)),('free moving',free),('driven moving',driven),('input-transition neighborhood',switch_near)]:out(f'  {label}: '+metrics(res,m))

out('\nENCODER DERIVATIVE TIMING CHECKS')
# Compare central, forward and backward finite differences within trajectory only.
for target,name in [(w,'omega'),(y,'domega')]:
 source=t if name=='omega' else w
 unit='rad/s' if name=='omega' else 'rad/s^2'
 for scheme in ['backward','central','forward']:
  derivative=np.zeros(n);off=0
  for gid,g in runs:
   L=len(g);z=source[off:off+L]
   if scheme=='central': derivative[off+1:off+L-1]=(z[2:]-z[:-2])/.02
   elif scheme=='backward': derivative[off+1:off+L]=(z[1:]-z[:-1])/.01
   else:derivative[off:off+L-1]=(z[1:]-z[:-1])/.01
   off+=L
  out(f'Logged `{name}` versus {scheme} finite difference: interior training RMSE = {rmse((derivative-target)[interior]):.6g} {unit}; moving-clean RMSE = {rmse((derivative-target)[move]):.6g} {unit}.')

# Fixed-basis ordinary least squares. Scale inputs so column coefficients have stated units.
v=.5
base=np.column_stack([u,-np.sin(t),-w,-np.tanh(w/v)])
base_names=['u','-sin(theta)','-omega','-tanh(omega/v)'];base_units=['rad/(s^2 V)','rad/s^2','1/s','rad/s^2']
extras={
 'base':([],[],[]),
 'cubic_input':([u**3],['u**3'],['rad/(s^2 V^3)']),
 'directional_input':([u*np.abs(u)],['u*Abs(u)'],['rad/(s^2 V^2)']),
 'harmonic_restore':([-np.sin(t)*np.cos(t)],['-sin(theta)*cos(theta)'],['rad/s^2']),
 'directional_friction':([-np.tanh(w/v)**2],['-tanh(omega/v)**2'],['rad/s^2']),
 'quadratic_drag':([-w*np.abs(w)],['-omega*Abs(omega)'],['1/rad']),
 'combined':([u**3,-np.sin(t)*np.cos(t),-np.tanh(w/v)**2],['u**3','-sin(theta)*cos(theta)','-tanh(omega/v)**2'],['rad/(s^2 V^3)','rad/s^2','rad/s^2']),
}
out('\nMOVING-CLEAN DERIVATIVE LEAST SQUARES')
out('Fixed `v = 0.5` rad/s is an analyst-chosen smoothing scale, not fitted; on this subset tanh is already near saturated. Simultaneous ordinary least squares uses numpy.linalg.lstsq; no starts or random seed needed. The criterion is sum of squared acceleration residuals on the moving-clean subset. These derivative fits are diagnostics, not selected simulation models.')
fits={}
for name,(columns,names,units) in extras.items():
 X=np.column_stack([base]+columns);coef=np.linalg.lstsq(X[move],y[move],rcond=None)[0];res=X@coef-y
 cv=[]
 for gid,g in runs:
  test=move&(ids==gid);train=move&(ids!=gid)
  if not test.any():continue
  c=np.linalg.lstsq(X[train],y[train],rcond=None)[0];cv.extend((X[test]@c-y[test]).tolist())
 out(f'{name}: training moving-clean derivative RMSE = {rmse(res[move]):.6g} rad/s^2; leave-one-trajectory-out pooled derivative RMSE = {rmse(np.array(cv)):.6g} rad/s^2.')
 for nm,c,un in zip(base_names+names,coef,base_units+units):out(f'  coefficient of `{nm}` = {c:.9g} {un}.')
 fits[name]=(X,coef,res)

out('\nINPUT TIMING LEAST SQUARES')
for shift in [-2,-1,0,1,2]:
 X=base.copy();X[:,0]=lag_u[shift];coef=np.linalg.lstsq(X[interior],y[interior],rcond=None)[0];res=X@coef-y
 out(f'Input index shift = {shift} samples ({shift*.01:.2f} s; positive uses future input): all interior acceleration RMSE = {rmse(res[interior]):.6g} rad/s^2; input-transition interior acceleration RMSE = {rmse(res[interior&switch_near]):.6g} rad/s^2; coefficient of shifted `u` = {coef[0]:.6g} rad/(s^2 V).')
# A mixture at transitions only is identifiable from switches, but unavailable in allowed expression.
X=np.column_stack([base,lag_u[-1]-u,lag_u[1]-u]);coef=np.linalg.lstsq(X[interior],y[interior],rcond=None)[0];res=X@coef-y
out(f'Contemporaneous plus neighboring input differences diagnostic: interior RMSE = {rmse(res[interior]):.6g} rad/s^2; transition RMSE = {rmse(res[interior&switch_near]):.6g} rad/s^2; coefficients: current `u` {coef[0]:.6g} rad/(s^2 V), previous-minus-current `u` {coef[4]:.6g} rad/(s^2 V), next-minus-current `u` {coef[5]:.6g} rad/(s^2 V). This is noncausal/off-contract and must not be submitted; it tests derivative filtering/timing.')

out('\nCONDITIONAL RESIDUAL SUMMARIES FOR BASIC DERIVATIVE FIT')
res=fits['base'][2]
for lo,hi in [(-10,-5),(-5,-2),(-2,-.5),(-.5,.5),(.5,2),(2,5),(5,10.01)]:
 m=move&(u>=lo)&(u<hi)
 if m.sum():out(f'`{lo} <= u < {hi}` V: '+metrics(res,m))
for lo,hi in [(-3.15,-2),(-2,-1),(-1,-.3),(-.3,.3),(.3,1),(1,2),(2,3.15)]:
 m=move&(t>=lo)&(t<hi)
 if m.sum():out(f'`{lo} <= theta < {hi}` rad: '+metrics(res,m))
for lo,hi in [(-30,-10),(-10,-3),(-3,-1),(1,3),(3,10),(10,30)]:
 m=move&(w>=lo)&(w<hi)
 if m.sum():out(f'`{lo} <= omega < {hi}` rad/s: '+metrics(res,m))

out('\nFREE-RESPONSE REST AND CONSTRAINTS')
m=(u==0)&(abs(w)<.01)&(abs(y)<.01)
out(f'Near-rest free-response subset (`Abs(omega)<0.01` rad/s and `Abs(domega)<0.01` rad/s^2): {m.sum()} training samples; angle range = [{t[m].min():.6g}, {t[m].max():.6g}] rad. A smooth Coulomb-only model predicts return toward exact equilibrium except at zeros of restoring torque; a static threshold can sustain this observed interval.')
out('For existing families let `D` denote input acceleration minus restoring acceleration, `h = exp(-(omega/v)**2)` and `clip(D) = Min(Max(D,-fs),fs)`. The core `D-h*clip(D)` has derivative with respect to `D` between `1-h` and 1; hence increasing input maps imply R3 (nondecreasing, flat within a static band at rest). At `omega=0` and `u=0`, its sign equals the sign of `D` or it is zero, so R2 follows if restoring torque opposes angle. These arguments are analytic and do not rely on fitted-domain sampling.')
out('Family 5 uses `-g*sin(theta)*(1+q*cos(theta))`; `g>=0` and `Abs(q)<=1` suffice for R2 on the stated angle domain. Family 6 changes friction to `-(c+d*tanh(omega/v))*tanh(omega/v)`; `c>=Abs(d)` keeps friction opposing velocity, and this term vanishes at rest so does not change R2. Family 4 input `a*u+k*u**3` has slope `a+3*k*u**2`; positive cubic coefficient enforces hardening only. A negative cubic coefficient is also R3-valid if `a+300*k>=0` rad/(s^2 V) for the task input range, with the numeric factor carrying V^2. Saturating monotone maps avoid this global restriction.')
# Supplemental input restoring split fits
out('\nFREE VERSUS DRIVEN MOVING-CLEAN BASIC FITS')
for name,m in [('free',free),('driven',driven)]:
 X=base if name=='driven' else base[:,1:]
 coef=np.linalg.lstsq(X[m],y[m],rcond=None)[0]
 out(f'{name}: {m.sum()} samples; training derivative RMSE = {rmse((X@coef-y)[m]):.6g} rad/s^2.')
 for nm,c,un in zip(base_names if name=='driven' else base_names[1:],coef,base_units if name=='driven' else base_units[1:]):out(f'  coefficient `{nm}` = {c:.9g} {un}.')

open('diagnostic_notes.txt','w').write('\n'.join(lines)+'\n')
print('\n'.join(lines))
