import numpy as np
import pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); rows=[]
for tr,g in D.groupby('trajectory'):
 g=g.reset_index(drop=True); n=len(g)-1
 ph=g.phi.to_numpy(); dp=np.angle(np.exp(1j*np.diff(ph))); dx=np.diff(g.x); dy=np.diff(g.y)
 mid=ph[:-1]+dp/2
 speed=(dx*np.cos(mid)+dy*np.sin(mid))/.2
 lateral=(-dx*np.sin(mid)+dy*np.cos(mid))/.2
 for k in range(n):
  rows.append([tr,k,k%5,g.v_f[k],g.v_a[k],g.v_f[max(0,k-1)],g.v_a[max(0,k-1)],dp[k]/.2,speed[k],lateral[k],np.angle(np.exp(1j*(np.arctan2(dy[k],dx[k])-ph[k]))),ph[k]])
A=pd.DataFrame(rows,columns=['tr','k','phase','vf','va','pvf','pva','omega','speed','lateral','chord_angle','phi'])
out=[]
def p(s):out.append(s);print(s)
def fit(y,X):
 b=np.linalg.lstsq(X,y,rcond=None)[0]; r=y-X@b
 return b,np.sqrt(np.mean(r*r)),r
p('# Independent diagnostics of `data/train.csv`')
p('All diagnostics use training data only. The sample period is `Ts = 0.2` s, as supplied in TASK.md. `omega = atan2(sin(phi_next-phi),cos(phi_next-phi))/Ts` rad/s. `speed = (dx*cos(phi+Ts*omega/2)+dy*sin(phi+Ts*omega/2))/Ts` m/s is signed midpoint-projected speed. `lateral` m/s is its orthogonal component. Fits use ordinary least squares (`numpy.linalg.lstsq`) unless stated otherwise, with no starting values or random seed. Errors are root mean square residuals on the stated rows, not rollout errors. All coefficient lists are ordered as the named design-matrix columns; coefficient units are target units divided by column units. Sample indices and counts are dimensionless. Phase indices denote elapsed samples since a command change.')
p(f'Rows: {len(D)} samples; {len(A)} within-trajectory transitions; {sum(A.phase==0)} command-change transitions (includes initial transitions).')
p(f'Command ranges on all training rows: `v_f` [{D.v_f.min():.9f}, {D.v_f.max():.9f}] m/s; `v_a` [{D.v_a.min():.9f}, {D.v_a.max():.9f}] rad/s.')
p(f'On all transitions lateral RMS = {np.sqrt(np.mean(A.lateral**2)):.9g} m/s; speed median = {A.speed.median():.9g} m/s.')
for var,cmd,prev,unit in [('omega','va','pva','rad/s'),('speed','vf','pvf','m/s')]:
 p('\n## '+var)
 for name,mask in [('all',np.ones(len(A),bool)),('settled phases 1-4',A.phase>0),('late phases 2-4',A.phase>1),('change phase 0',A.phase==0)]:
  B=A[mask]; y=B[var].to_numpy(); u=B[cmd].to_numpy(); pu=B[prev].to_numpy()
  for fam,X in [('gain',u[:,None]),('affine',np.c_[u,np.ones(len(B))]),('cubic',np.c_[u,u**2,u**3,np.ones(len(B))]),('current+previous',np.c_[u,pu,np.ones(len(B))])]:
   b,e,r=fit(y,X); p(f'{name}; {fam}; n={len(B)} transitions; coefficients={b.tolist()}; residual RMS={e:.9g} {unit}.')
 for phase in range(5):
  B=A[A.phase==phase]; b,e,r=fit(B[var].to_numpy(),np.c_[B[cmd],B[prev],np.ones(len(B))]); p(f'phase={phase} samples after command change; current/previous/offset coefficients={b.tolist()}; residual RMS={e:.9g} {unit}; n={len(B)} transitions. For phases greater than zero, current and previous commands coincide; their separate coefficients are unidentifiable and only their sum is meaningful.')
 B=A[A.phase>0]; y=B[var].to_numpy(); u=B[cmd].to_numpy()
 b,e,r=fit(y,np.c_[u,np.ones(len(B))]);
 for tr in [1,2,3]:
  C=B[B.tr==tr]; bt,et,rt=fit(C[var].to_numpy(),np.c_[C[cmd],np.ones(len(C))]); p(f'trajectory={tr}; settled affine coefficients={bt.tolist()}; RMS={et:.9g} {unit}; n={len(C)} transitions.')
 p('Settled block affine residual summaries, gain estimated globally on phases 1-4:')
 B=B.copy();B['r']=r
 for lo,hi in [(0,50),(50,100),(100,150)]:
  C=B[(B.k>=lo)&(B.k<hi)];p(f'k in [{lo},{hi}) samples; mean={C.r.mean():.9g} {unit}; RMS={np.sqrt(np.mean(C.r**2)):.9g} {unit}; n={len(C)} transitions.')
 for lag in [1,2,5]:
  aa=[];bb=[]
  for _,C in B.groupby('tr'):
   R=dict(zip(C.k,C.r));
   for k,v in R.items():
    if k+lag in R:aa.append(v);bb.append(R[k+lag])
  p(f'Settled residual correlation at lag {lag} samples ({lag*.2:.1f} s) = {np.corrcoef(aa,bb)[0,1]:.6f}, dimensionless; n={len(aa)} pairs.')
 if var=='omega':
  def pred(z,u):return z[0]*np.sign(u)*np.maximum(np.abs(u)-z[1],0)+z[2]
  z=least_squares(lambda z:pred(z,u)-y,[.8,.1,0],bounds=([0,0,-1],[3,.5,1])).x
  p(f'Settled asymmetric-bias dead-zone fit `gain*sign(v_a)*Max(Abs(v_a)-threshold,0)+bias`: gain={z[0]:.9g} dimensionless; threshold={z[1]:.9g} rad/s; bias={z[2]:.9g} rad/s; RMS={np.sqrt(np.mean((pred(z,u)-y)**2)):.9g} rad/s. Nonlinear least squares (`scipy.optimize.least_squares`), starting gain 0.8 dimensionless, threshold 0.1 rad/s, bias 0 rad/s; bounded to gain [0,3], threshold [0,0.5] rad/s, bias [-1,1] rad/s.')
  for lo,hi in [(0,.1),(.1,.2),(.2,.4),(.4,.6),(.6,1)]:
   C=B[(abs(B.va)>=lo)&(abs(B.va)<hi)];p(f'Angular command magnitude [{lo},{hi}) rad/s; n={len(C)}; mean abs omega={abs(C.omega).mean():.9g} rad/s; mean abs command={abs(C.va).mean():.9g} rad/s.')
M=A[(abs(A.speed)>.005)]
dp=M.omega.to_numpy()*.2
b,e,r=fit(M.chord_angle.to_numpy(),np.c_[dp,np.ones(len(M))])
p(f'\nChord-angle relation on {len(M)} transitions with abs speed > 0.005 m/s: `angle(displacement)-phi = a*(phi_next-phi)+b`; a={b[0]:.9g} dimensionless, b={b[1]:.9g} rad; RMS={e:.9g} rad.')
B=A[A.phase>0]; w=B.omega.to_numpy();u=B.va.to_numpy();v=B.vf.to_numpy();t=B.k.to_numpy()*.2;ph=B.phi.to_numpy()
for label,X in [('odd quadratic (v_a,v_a*Abs(v_a),sign(v_a),1)',np.c_[u,u*abs(u),np.sign(u),np.ones(len(B))]),('forward-speed coupling (v_a,v_a*Abs(v_a),v_f,v_a*v_f,1)',np.c_[u,u*abs(u),v,u*v,np.ones(len(B))]),('time-varying gain (v_a,v_a*t,1)',np.c_[u,u*t,np.ones(len(B))]),('orientation offset (v_a,sin(phi),cos(phi),1)',np.c_[u,np.sin(ph),np.cos(ph),np.ones(len(B))])]:
 b,e,r=fit(w,X);p(f'Angular settled {label}; coefficients={b.tolist()}; RMS={e:.9g} rad/s; n={len(B)} transitions.')
for label,X in [('time offset (v_f,t,1)',np.c_[v,t,np.ones(len(B))]),('time-varying gain (v_f,v_f*t,1)',np.c_[v,v*t,np.ones(len(B))]),('orientation gain (v_f,v_f*sin(phi),v_f*cos(phi),1)',np.c_[v,v*np.sin(ph),v*np.cos(ph),np.ones(len(B))]),('angular coupling (v_f,Abs(v_a),v_f*Abs(v_a),1)',np.c_[v,abs(u),v*abs(u),np.ones(len(B))])]:
 b,e,r=fit(B.speed.to_numpy(),X);p(f'Speed settled {label}; coefficients={b.tolist()}; RMS={e:.9g} m/s; n={len(B)} transitions. Here `t=k*Ts` s is diagnostic only, not an allowed model input.')
p('\n## Settled block means (average phases 1-4)')
blocks=A[A.phase>0].groupby(['tr',A[A.phase>0].k//5]).agg(vf=('vf','mean'),va=('va','mean'),omega=('omega','mean'),speed=('speed','mean'),omega_sd=('omega','std'),speed_sd=('speed','std')).reset_index()
p(f'Block count={len(blocks)}; median within-block angular SD={blocks.omega_sd.median():.9g} rad/s; median speed SD={blocks.speed_sd.median():.9g} m/s.')
for var,cmd,unit in [('omega','va','rad/s'),('speed','vf','m/s')]:
 b,e,r=fit(blocks[var].to_numpy(),np.c_[blocks[cmd],np.ones(len(blocks))]);p(f'Block mean {var} affine coefficients={b.tolist()}; RMS={e:.9g} {unit}.')
B=A[(A.phase==0)&(A.k>0)]
for var,cmd,prev,unit in [('omega','va','pva','rad/s'),('speed','vf','pvf','m/s')]:
 b,e,r=fit(B[var].to_numpy(),np.c_[B[cmd],B[prev],np.ones(len(B))]);p(f'Noninitial phase0 {var}: current/previous/offset={b.tolist()}; RMS={e:.9g} {unit}; n={len(B)} transitions.')
p('\n## Interpretation and suggestions')
p('Most useful allowed families: calibrated unicycle with midpoint orientation `x_next = x + Ts*v*cos(phi + q*Ts*w)` and analogous sine for `y_next`, where `v` m/s is a static forward response and `w` rad/s a static angular response, `q` dimensionless is a within-step orientation fraction; affine or gain-only forward response; dead-zone angular response; smooth dead-zone alternative `w = a*v_a-b*tanh(v_a/c)+d`, with `a` dimensionless and `b`, `c`, `d` rad/s. Try exact constant-twist integration as a distinct physically motivated integrator, using a guarded zero-rate limit.')
p('Angular response is clearly suppressed near zero commands; odd cubic improves modestly, but a dead zone is more interpretable. Forward cubic gives negligible improvement and is not supported as a necessary static nonlinearity. Angular forward-speed coupling is modest and should be judged by held-out trajectory rollouts, not training residual reduction alone.')
p('There is a dominant command-change timing effect. The previous angular command has more influence than the current command in the first changed-command interval; forward velocity shows a smaller but clear carryover. Settled intervals are reached by the second logged interval. A fractional-delay or actuator-lag structure would describe this if extra memory were allowed. The requested expressions do not allow previous commands or actuator states, so they cannot reproduce this exactly; do not claim a purely static model estimates this delay. Diagnose the influence by phase-dependent residuals, and estimate allowed static parameters by multi-step rollout objectives, because those parameters must compromise over transitions.')
p('Residuals are highly temporally correlated and blockwise coherent rather than independent pose noise. Forward residuals also trend upward within trajectories; a time feature improves diagnostic fit but elapsed time is not allowed. Position or heading dependence might proxy drift in training, but that does not establish a physical law and risks failing on new trajectories. Neither actuator calibration drift nor correlated odometry error can be separated from these data. Prefer conservative parameter counts and trajectory-wise validation.')
p('No external references were used or required. Family names here refer to differential-drive/unicycle kinematics, static dead-zone nonlinearities, and fractional command delay; no unverified citation is supplied. No candidate files or main scripts were written or modified.')
open('helper_report.md','w',encoding='utf-8').write('\n\n'.join(out)+'\n')
