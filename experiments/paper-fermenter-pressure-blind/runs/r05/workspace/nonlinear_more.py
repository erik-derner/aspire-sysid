import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from refine import rollout,refine,PolyModel,RationalModel,StableModel
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
# Variable projection fits with input-dependent feedback, nonlinear state
results=[]
def features(t,d,label):
 z=d.y.values-t[0];u=d.x1.values/60;v=d.x2.values/20
 h,p,q=t[:3];g=np.sign(z)*np.abs(z)**p
 if label=='power_feedback':return np.c_[np.ones(len(d)),u,u*u,v**q,g,u*g]
 if label=='power_feedback2':return np.c_[np.ones(len(d)),u,u*u,v**q,g,u*g,u*u*g]
 if label=='power_feedback_mix':return np.c_[np.ones(len(d)),u,u*u,v**q,g,u*g,v*g,u*v]
for label in ['power_feedback','power_feedback2','power_feedback_mix']:
 best=None
 for p0 in [.5,1,1.5]:
  def err(t):
   X=features(t,tr,label);c=np.linalg.lstsq(X,tr.dy,rcond=None)[0];return X@c-tr.dy.values
  opt=least_squares(err,[.98,p0,2],bounds=([.7,.1,.1],[.9922,3,5]),max_nfev=700,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  if best is None or np.sum(opt.fun**2)<np.sum(best.fun**2):best=opt
 t=best.x;c=np.linalg.lstsq(features(t,tr,label),tr.dy,rcond=None)[0]
 print(label,t,c,'der',[np.sqrt(np.mean((features(t,d,label)@c-d.dy)**2)) for d in [tr,va]],flush=True)
 results.append(dict(label=label,theta=t.tolist(),coef=c.tolist()))
# finish stable/rational rollout fitting
s=StableModel();start=np.array([.004,-.02,.01,.001,.005,.005,.40,-.15,0]);lo=np.r_[np.full(8,-np.inf),0];hi=np.full(9,np.inf)
opt=least_squares(lambda c:np.array([s.fg(y-1,u/60,v/20,c)[0] for y,u,v in tr[['y','x1','x2']].values])-tr.dy.values,start,bounds=(lo,hi),max_nfev=1000)
c0=opt.x
c,opt=refine(s,c0,[tr],bounds=(lo,hi))
print('stable',c,'roll',[np.sqrt(np.mean((rollout(s,c,d)[1:]-d.y.values[1:])**2)) for d in [tr,va]],flush=True)
results.append(dict(label='stable',start=c0.tolist(),coef=c.tolist()))
for deg in [2,3]:
 r=next(r for r in json.load(open('poly_results.json')) if r['deg']==deg and r['reg']==0)
 m=RationalModel(r['powers']);start=np.r_[r['coef'],0]
 c,opt=refine(m,start,[tr],bounds=(np.r_[np.full(m.m-1,-np.inf),0],np.full(m.m,np.inf)))
 print('rational',deg,c,'roll',[np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2)) for d in [tr,va]],flush=True)
 results.append(dict(label='rational'+str(deg),powers=r['powers'],start=start.tolist(),coef=c.tolist()))
json.dump(results,open('nonlinear_more_results.json','w'),indent=2)
