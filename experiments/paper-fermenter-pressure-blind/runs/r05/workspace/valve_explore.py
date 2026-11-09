import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from rollout import rk4
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv');res=[]
def feat(t,d,label):
 h,p,q,r=t;z=np.maximum(d.y.values-h,1e-8)**p;u=d.x1.values/60;v=d.x2.values/20;angle=d.x1.values*np.pi/180
 if label=='cos':return np.c_[np.ones(len(d)),v**q,-z,-z*np.maximum(np.cos(angle),0)**r]
 if label=='cos_source':return np.c_[np.ones(len(d)),u,u*u,v**q,-z,-z*np.maximum(np.cos(angle),0)**r]
 if label=='sin':return np.c_[np.ones(len(d)),v**q,-z,-z*(1-np.sin(angle))**r]
 if label=='valvepower':return np.c_[np.ones(len(d)),v**q,-z,-z*np.maximum(1.6-u,0)**r]
 if label=='valvelinear':return np.c_[np.ones(len(d)),v**q,-z,-z*u]
for label in ['cos','cos_source','sin','valvepower','valvelinear']:
 best=None
 for h0 in [.95,.99]:
  def err(t):
   X=feat(t,tr,label);c=np.linalg.lstsq(X,tr.dy,rcond=None)[0];return X@c-tr.dy.values
  opt=least_squares(err,[h0,.5,1,1],bounds=([.7,.1,.1,.1],[.9922,2,4,5]),max_nfev=1200,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  if best is None or sum(opt.fun**2)<sum(best.fun**2):best=opt
 t=best.x;X=feat(t,tr,label);c=np.linalg.lstsq(X,tr.dy,rcond=None)[0]
 def f(y,u,v):return (feat(t,pd.DataFrame({'y':[y],'x1':[u],'x2':[v]}),label)@c)[0]
 der=[np.sqrt(np.mean((feat(t,d,label)@c-d.dy)**2)) for d in [tr,va]]
 roll=[np.sqrt(np.mean((rk4(f,d)[1:]-d.y.values[1:])**2)) for d in [tr,va]]
 print(label,t,c,'der',der,'roll',roll,flush=True)
 res.append(dict(label=label,theta=t.tolist(),coef=c.tolist(),der=der,roll=roll))
json.dump(res,open('valve_explore_results.json','w'),indent=2)
