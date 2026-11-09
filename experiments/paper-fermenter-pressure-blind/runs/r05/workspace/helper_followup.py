import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv');Y=tr.dy.values;V=va.dy.values
out=[]
# Variable projection: additive shifted-state power, nonlinear input power; smooth shifted-state reciprocal; saturating input.
for family in ['shift_power','rational_state','input_hinge']:
 def mat(p,d):
  y,u,v=[d[k].values for k in ['y','x1','x2']]
  if family=='shift_power':
   sp,up,vp,h=p;z=np.maximum(y-h,1e-10);return np.array([np.ones(len(y)),(u/60)**up,(v/20)**vp,z**sp]).T
  if family=='rational_state':
   sp,up,vp,h=p;return np.array([np.ones(len(y)),(u/60)**up,(v/20)**vp,1/(np.maximum(y-h,1e-10)**sp)]).T
  sp,up,vp,h,hu=p;return np.array([np.ones(len(y)),np.maximum((u-hu)/60,0)**up,(v/20)**vp,np.maximum(y-h,1e-10)**sp]).T
 if family=='input_hinge': starts=[[.5,2,1,.99,20],[.3,3,1,.99,0],[.5,1,1,.98,40]];lo=[.05,.1,.1,-2,-100];hi=[4,8,4,.992308,85]
 else:starts=[[s,up,1,h] for s in [.2,.5,1] for up in [2,4] for h in [0,.99]];lo=[.05,.1,.1,-2];hi=[4,10,4,.992308]
 for start in starts:
  def fun(p):
   a=mat(p,tr);c=np.linalg.lstsq(a,Y,rcond=None)[0];return a@c-Y
  r=least_squares(fun,start,bounds=(lo,hi),max_nfev=800,ftol=1e-11,xtol=1e-11,gtol=1e-11);a,b=mat(r.x,tr),mat(r.x,va);c=np.linalg.lstsq(a,Y,rcond=None)[0]
  res=Y-a@c;rv=V-b@c
  out.append(dict(family=family,start=start,parameters=r.x.tolist(),coefficients=c.tolist(),train_rmse=float(np.sqrt(np.mean(res**2))),val_rmse=float(np.sqrt(np.mean(rv**2))),train_correlations={k:float(np.corrcoef(res,tr[k])[0,1]) for k in ['y','x1','x2']},val_correlations={k:float(np.corrcoef(rv,va[k])[0,1]) for k in ['y','x1','x2']}))
out.sort(key=lambda r:r['val_rmse']);json.dump(out,open('helper_followup_results.json','w'),indent=2);print(json.dumps(out[:6],indent=2));print('VALIDATION RANGES');print(va.describe().to_string())
