"""Derivative-only structural identification; writes no candidate models.
Run: python helper_analysis.py
Uses only data/train.csv and data/val.csv. No trajectory simulation.
"""
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

train=pd.read_csv('data/train.csv'); val=pd.read_csv('data/val.csv')
out=[]
def emit(s=''): out.append(str(s))
def rmse(y,p): return np.sqrt(np.mean((y-p)**2)) if len(y) else np.nan

FEATURES={
'g':('-sin(theta)','rad/s^2'), 'b':('-omega','1/s'),
'c':('-sign(omega)','rad/s^2'),'k':('u','rad/(s^2 V)'),
'g2':('-sin(2*theta)','rad/s^2'),'g3':('-sin(3*theta)','rad/s^2'),
'asymC':('-Abs(sign(omega))','rad/s^2'),
'quadD':('-omega*Abs(omega)','1/rad'),
'cubicD':('-omega**3','s/rad^2'),
'quadU':('u*Abs(u)','rad/(s^2 V^2)'),
'cubicU':('u**3','rad/(s^2 V^3)'),
'asymU':('Abs(u)','rad/(s^2 V)'),
'asymD':('-Abs(omega)','1/s'),
'angleD':('-omega*(1-cos(theta))','1/s'),
'cosOffset':('cos(theta)*Abs(sign(omega))','rad/s^2'),
'cAngle':('-sign(omega)*(1-cos(theta))','rad/s^2'),
}
def feat(d,names):
 t=d.theta.to_numpy(); w=d.omega.to_numpy(); u=d.u.to_numpy();s=np.sign(w)
 allf={'g':-np.sin(t),'b':-w,'c':-s,'k':u,'g2':-np.sin(2*t),'g3':-np.sin(3*t),'asymC':-np.abs(s),'quadD':-w*np.abs(w),'cubicD':-w**3,'quadU':u*np.abs(u),'cubicU':u**3,'asymU':np.abs(u),'asymD':-np.abs(w),'angleD':-w*(1-np.cos(t)),'cosOffset':np.cos(t)*np.abs(s),'cAngle':-s*(1-np.cos(t))}
 return np.column_stack([allf[n] for n in names])
def fit(d,names):
 X=feat(d,names); scale=np.sqrt(np.mean(X*X,axis=0));scale[scale==0]=1
 lower=np.array([0 if n in ('g','b','c','k') else -np.inf for n in names])
 result=lsq_linear(X/scale,d.domega.to_numpy(),bounds=(lower,np.full(len(names),np.inf)),tol=1e-12,max_iter=500)
 return result.x/scale

def summary_fit(label,names,threshold=0.5,subset=None):
 mask=np.abs(train.omega)>threshold
 if subset=='free':mask &= train.u==0
 if subset=='driven':mask &= train.trajectory.isin([1,2,3,4])
 d=train[mask]; pars=fit(d,names)
 emit(f'\n{label}; fitting data=train, rows={len(d)} samples; moving threshold=Abs(omega) > {threshold:g} rad/s; subset={subset or "all trajectories"}.')
 emit('Expression: `domega = '+' + '.join(f'{n}*({FEATURES[n][0]})' for n in names)+'`.')
 for n,p in zip(names,pars):emit(f'  `{n} = {p:.9g}` {FEATURES[n][1]}; estimated jointly from the preceding training subset.')
 for source,df in [('train',train),('val',val)]:
  for typ,m in [('all-moving',np.abs(df.omega)>threshold),('driven-moving',(np.abs(df.omega)>threshold)&(df.u!=0)),('free-moving',(np.abs(df.omega)>threshold)&(df.u==0))]:
   y=df.loc[m,'domega'].to_numpy(); pred=feat(df[m],names)@pars
   emit(f'  {source}/{typ}: n={len(y)} samples; derivative RMSE={rmse(y,pred):.6g} rad/s^2; mean residual={np.mean(y-pred):.6g} rad/s^2.')
 # Audit smooth underlying force: not itself a final sticking law.
 theta=np.linspace(-np.pi,np.pi,2001);u=np.linspace(-10,10,2001);w=np.linspace(-23,23,2001)
 g=np.zeros_like(theta); dp=np.zeros_like(u); damping=np.zeros_like(w)
 pdict=dict(zip(names,pars))
 for n,p in pdict.items():
  if n=='g':g+=p*np.sin(theta)
  if n=='g2':g+=p*np.sin(2*theta)
  if n=='g3':g+=p*np.sin(3*theta)
  if n=='k':dp+=p
  if n=='quadU':dp+=2*p*np.abs(u)
  if n=='cubicU':dp+=3*p*u*u
  if n=='asymU':dp+=p*np.sign(u)
 emit(f'  Grid physical audit: min gravity(theta)*theta={np.min(g*theta):.6g} rad^2/s^2 on 2001 assumed grid points, theta in [-pi,pi] rad; min d(force)/du={np.min(dp):.6g} rad/(s^2 V) on 2001 assumed grid points, u in [-10,10] V. Sign-reversed gravity gives restoring force. Other friction asymmetry terms require separate final-model audit.')
 return names,pars

emit('DERIVATIVE STRUCTURE REPORT (no model files and no simulation)')
emit('Definitions: `theta` is angle in rad, `omega` angular velocity in rad/s, `u` voltage in V, `domega` measured acceleration in rad/s^2. `e = domega - prediction` is the derivative residual. Derivative RMSE is sqrt(mean(e**2)); means are arithmetic sample means. Counts are samples, identifiers dimensionless. Unless marked assumed, numbers below are computed on the named data/subset. Coefficient units are given at every initialization.')
emit('Methods: constrained linear least squares, scipy.optimize.lsq_linear, with positive gravity/viscous/Coulomb/linear-voltage coefficients; extension coefficients unrestricted. Features scaled by training root mean square. All parameters fitted jointly; no starting values and no random seed are required. Objective=sum((domega-prediction)**2) on selected moving samples, to avoid regressing an unmodeled stick constraint. Reference from memory, not web-checked: Lawson and Hanson, Solving Least Squares Problems (SIAM). Base family is pendulum gravity with viscous plus Coulomb friction. Derivative fits do not establish long-horizon simulation quality.')
for source,df in [('train',train),('val',val)]:
 emit(f'\n{source}: total={len(df)} samples; trajectories={df.trajectory.nunique()} dimensionless trajectory identifiers; sample period assumed from TASK.md=0.01 s.')
 for tr,d in df.groupby('trajectory'):
  emit(f'  trajectory identifier={tr}: n={len(d)} samples, voltage range=[{d.u.min():.6g},{d.u.max():.6g}] V; theta range=[{d.theta.min():.6g},{d.theta.max():.6g}] rad; omega range=[{d.omega.min():.6g},{d.omega.max():.6g}] rad/s; exact-zero speed={sum(d.omega==0)} samples.')
 for threshold in [0,0.157,0.5,1,2]:
  emit(f'  moving threshold={threshold:g} rad/s: {sum(np.abs(df.omega)>threshold)} samples.')
 z=df[np.abs(df.omega)<1e-10]
 emit(f'  Numerically resting threshold assumed=1e-10 rad/s: theta range=[{z.theta.min():.6g},{z.theta.max():.6g}] rad; acceleration RMS={np.sqrt(np.mean(z.domega**2)):.6g} rad/s^2; {len(z)} samples.')

base=['g','b','c','k']
fits={}
for threshold in [.157,.5,1,2]: fits[f'base{threshold}']=summary_fit(f'BASE sensitivity {threshold} rad/s',base,threshold)
for subset in ['free','driven']:summary_fit('BASE regime '+subset,base if subset=='driven' else ['g','b','c'],.5,subset)
variants={
'asymmetric Coulomb':base+['asymC'],
'asymmetric damping':base+['asymD'],
'asymmetric voltage':base+['asymU'],
'quadratic damping':base+['quadD'],
'cubic damping':base+['cubicD'],
'quadratic voltage':base+['quadU'],
'cubic voltage':base+['cubicU'],
'gravity harmonic 2':base+['g2'],
'gravity harmonics 2+3':base+['g2','g3'],
'angle-modulated viscous':base+['angleD'],
'angle-modulated Coulomb':base+['cAngle'],
'angle moving offset':base+['cosOffset'],
'combined quadratic voltage damping asymmetry':base+['quadU','quadD','asymC'],
'combined harmonics voltage damping':base+['g2','g3','quadU','quadD'],
}
for label,names in variants.items():fits[label]=summary_fit(label,names)

names,pars=fits['base0.5']
for source,df in [('train',train),('val',val)]:
 d=df[np.abs(df.omega)>.5].copy();d['resid']=d.domega.to_numpy()-feat(d,names)@pars
 emit(f'\nBASE residual stratification {source}; moving threshold=0.5 rad/s; coefficients fitted on train only.')
 for col,bins,unit in [('omega',[-30,-10,-5,-2,-.5,.5,2,5,10,30],'rad/s'),('theta',[-4,-1,-.5,-.2,0,.2,.5,1,4],'rad'),('u',[-10,-3,-1,-.1,.1,1,3,10],'V')]:
  d['bin']=pd.cut(d[col],bins,include_lowest=True)
  for name,q in d.groupby('bin',observed=True):
   emit(f'  `{col}` bin={name} {unit}: n={len(q)} samples; mean(e)={q.resid.mean():.6g} rad/s^2; RMSE={np.sqrt(np.mean(q.resid**2)):.6g} rad/s^2.')
 # residual correlations are descriptive, not independently conditioned effects
 for n in FEATURES:
  f=feat(d,[n])[:,0]
  if np.std(f)>1e-12:emit(f'  Pearson correlation e versus `{FEATURES[n][0]}`={np.corrcoef(d.resid,f)[0,1]:.6g} dimensionless on {source} moving subset.')

# Stribeck-shaped Coulomb decay, smooth saturation alternatives; fixed scales grid.
emit('\nLOW-SPEED FRICTION grid: speed scales are assumed alternatives, not independently fitted. Fits use training moving threshold=0.157 rad/s; no rest samples.')
for scale in [.05,.1,.2,.5,1,2,4]:
 for mode in ['tanh','stribeck']:
  def matrix(df):
   w=df.omega.to_numpy();x=feat(df,base)
   if mode=='tanh':x[:,2]=-np.tanh(w/scale)
   else:x=np.column_stack([x,-np.sign(w)*np.exp(-(w/scale)**2)])
   return x
  d=train[np.abs(train.omega)>.157]; X=matrix(d); p=lsq_linear(X,d.domega,bounds=(np.zeros(X.shape[1]),np.full(X.shape[1],np.inf))).x
  text='; '.join(f'`{n} = {x:.7g}` {unit}' for n,x,unit in zip(base+(['extraC'] if mode=='stribeck' else []),p,[FEATURES[n][1] for n in base]+(['rad/s^2'] if mode=='stribeck' else [])))
  emit(f'  {mode}; assumed speed scale={scale:g} rad/s; training initializations: {text}.')
  for source,df in [('train',train),('val',val)]:
   q=df[np.abs(df.omega)>.157];emit(f'    {source} moving n={len(q)} samples; derivative RMSE={rmse(q.domega,matrix(q)@p):.6g} rad/s^2.')

emit('\nDERIVATIVE TIMING / ENCODER DIAGNOSTICS: differences kept strictly inside each trajectory; period=0.01 s assumed from TASK.md.')
for source,df in [('train',train),('val',val)]:
 q=df.copy();grp=q.groupby('trajectory');q['forward']=(grp.omega.shift(-1)-q.omega)/.01;q['central']=(grp.omega.shift(-1)-grp.omega.shift(1))/.02;q['backward']=(q.omega-grp.omega.shift(1))/.01
 for col in ['forward','central','backward']:
  m=q[col].notna();emit(f'  {source}: domega versus `{col}` velocity difference: n={sum(m)} samples; disagreement RMSE={rmse(q.loc[m,"domega"],q.loc[m,col]):.7g} rad/s^2; correlation={np.corrcoef(q.loc[m,"domega"],q.loc[m,col])[0,1]:.7g} dimensionless.')
 # voltage timing diagnostic: not proposed as final model, since no lag argument is permitted.
 for lag in [-2,-1,0,1,2]:
  q['ushift']=q.groupby('trajectory').u.shift(lag);m=(np.abs(q.omega)>.5)&q.ushift.notna();r=q[m].copy();r['u']=r.ushift;p=fit(r,base)
  emit(f'  {source} moving diagnostic voltage shift={lag} samples ({lag*.01:.3g} s): same-source refit n={len(r)} samples, derivative RMSE={rmse(r.domega,feat(r,base)@p):.6g} rad/s^2; not validation evidence, because coefficients refitted in each source.')

emit('\nREST BAND from free-response rows: inferred force/gravity ratio is illustrative; exact zero velocity alone includes transient reversals.')
for source,df in [('train',train),('val',val)]:
 z=df[(df.u==0)&(np.abs(df.omega)<1e-10)&(np.abs(df.domega)<1e-8)]
 emit(f'  {source} free rows with assumed zero-speed tolerance=1e-10 rad/s and zero-acceleration tolerance=1e-8 rad/s^2: n={len(z)} samples, angle range=[{z.theta.min():.7g},{z.theta.max():.7g}] rad; max Abs(sin(theta))={np.abs(np.sin(z.theta)).max():.7g} dimensionless. Baseline moving friction ratio c/g={pars[2]/pars[0]:.7g} dimensionless from train moving threshold=0.5 rad/s.')
emit('\nINTERPRETATION: A sign-based derivative fit cannot represent static friction at rest; use a torque dead zone or carefully audited regularization in the simulator. Any gravity harmonic combination must preserve restoring sign across [-pi,pi] rad (assumed physical domain), not merely observed angles. Odd nonlinear voltage coefficients should preserve monotonicity across [-10,10] V (assumed physical domain), wider than observed training inputs. Negative quadratic damping can fit derivatives but extrapolate to antidamping; smooth saturating or positive-damping alternatives may be safer. Moving-only asymmetric friction must not create nonrestoring torque at zero speed. Timing diagnostics are not permission to introduce lagged input into the candidate expressions. Error reductions are derivative-only and do not establish final simulation performance.')
open('helper_report.txt','w',encoding='utf-8').write('\n'.join(out)+'\n')
print('Wrote helper_report.txt; no candidate model files written.')
