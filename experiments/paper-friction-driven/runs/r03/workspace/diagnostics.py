import refine_models as rm, fit_models as fm
import numpy as np,pandas as pd,json
R=json.load(open('refine_results.json'));out=[]
for r in R:
 if r['label'] not in ['Projected','Compensated','HarmonicAsymmetric','SaturatingDamping','AngleFriction','HarmonicMotorAsymmetric','Harmonic']:continue
 p=np.array(r['parameters']);mode=r['mode'];lines=[r['label']+' final fit both supplied files; angle RMSE in rad, derivative residuals in rad/s^2']
 for file,data in [('train',fm.train),('val',fm.val)]:
  d=pd.read_csv('data/'+file+'.csv');pred=np.array([rm.accel(t,w,u,p,mode) for t,w,u in d[['theta','omega','u']].to_numpy()]);d['e']=d.domega-pred
  lines.append(file+' moving speed >0.5 rad/s: '+str(d.loc[d.omega.abs()>.5,'e'].agg(['mean','std']).to_dict()))
  for var,bins in [('theta',[-3.2,-1,-.2,.2,1,3.2]),('omega',[-24,-5,-.5,.5,5,24]),('u',[-10,-1,-.01,.01,1,10])]:
   z=d.loc[d.omega.abs()>.5].copy();lines.append(file+' '+var+' moving residual mean/count: '+z.groupby(pd.cut(z[var],bins),observed=True).e.agg(['mean','count']).to_string())
  for j,a in enumerate(data):
   y=rm.sim(a,p,mode);lines.append(file+' trajectory '+str(j+1)+' angle bias/RMSE/final error (rad): '+str([float(np.mean(y[1:]-a[1:,0])),float(np.sqrt(np.mean((y[1:]-a[1:,0])**2))),float(y[-1]-a[-1,0])]))
 # dense restoring audit and finite-difference monotonic audit
 th=np.linspace(-np.pi,np.pi,4001);prod=[rm.accel(t,0.,0.,p,mode)*t for t in th];lines.append('R2 max acceleration*theta over 4001 grid points (rad^2/s^2): '+str(max(prod)))
 rng=np.random.default_rng(20261009);pts=rng.uniform([-3.1416,-23,-10],[3.1416,23,10],size=(30000,3));der=[(rm.accel(t,w,u+1e-6,p,mode)-rm.accel(t,w,u,p,mode))/1e-6 for t,w,u in pts];lines.append('R3 min finite-difference voltage derivative over 30000 points (rad/(s^2 V)): '+str(min(der)))
 extrema=[]
 for j in range(100):
  a=np.zeros((2001,4));a[0,:2]=rng.uniform([-np.pi,-23],[np.pi,23]);a[:,2]=rng.choice([-10.,0.,10.],2001);y=rm.sim(a,p,mode);extrema.append(float(np.max(np.abs(y))))
 lines.append('Stress: 100 deterministic-seed random binary/zero voltage runs, each 20 s; maximal absolute angle (rad): '+str(max(extrema)))
 out+=lines+['']
open('diagnostics.txt','w').write('\n'.join(out))
print('\n'.join(x for x in out if ('final fit' in x or 'R2' in x or 'R3' in x or 'Stress' in x or 'moving speed' in x)))
