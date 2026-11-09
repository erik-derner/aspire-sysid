import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv');results=[]
def qr(p,u,v,kind):
 # common first parameters: baseline, forcing amplitude, restoring amplitude
 c,a,b=p[:3]
 if kind=='power':q=a*u**p[3]*v**p[4];r=b*(1-u)**p[5]
 elif kind=='exp':q=a*np.exp(p[3]*(u-.7))*v**p[4];r=b*np.exp(p[5]*(u-.7))
 elif kind=='logit':q=a*(u/(1-u))**p[3]*v**p[4];r=b*(1-u)**p[5]
 elif kind=='sigmoid':q=a/(1+np.exp(-p[3]*(u-p[4])))*v**p[5];r=b*(1-u)**p[6]
 elif kind=='affinepower':q=a*u**p[3]*v**p[4];r=b+p[5]*(1-u)
 elif kind=='mix':q=a*u**p[3]*v**p[4]+p[6]*(u-p[7]);r=b*(1-u)**p[5]
 return c,q,r

def prediction(p,d,kind,mode):
 u=d.x1.to_numpy()/100;v=d.x2.to_numpy()/30;c,q,r=qr(p,u,v,kind)
 z=5*r;F=1-z+z*z/2-z**3/6+z**4/24;G=5*(1-z/2+z*z/6-z**3/24)
 if mode=='deriv':return q-r*(d.y.to_numpy()-c)
 if mode=='step':return c+F[:-1]*(d.y.to_numpy()[:-1]-c)+G[:-1]*q[:-1]
 y=np.empty(len(d));y[0]=d.y.iloc[0]
 for k in range(len(d)-1):
  y[k+1]=c+F[k]*(y[k]-c)+G[k]*q[k]
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:return np.full(len(d),1e3)
 return y

starts={'power':[1,.05,.2,2,2,1], 'exp':[1,.03,.07,5,2,-3], 'logit':[1,.005,.2,1,2,1], 'sigmoid':[1,.1,.2,10,.7,2,1], 'affinepower':[1,.05,.02,2,2,.1], 'mix':[1,.05,.2,2,2,1,0,.5]}
for kind,start in starts.items():
 lo=[.8,1e-6,1e-5]+([.1,.1,.1] if kind in ['power','logit'] else ([-15,.1,-15] if kind=='exp' else ([.1,0,.1,.1] if kind=='sigmoid' else ([.1,.1,0] if kind=='affinepower' else [.1,.1,.1,-.2,0]))))
 hi=[1.1,2,1]+([15,8,4] if kind in ['power','logit'] else ([15,8,15] if kind=='exp' else ([60,1,8,4] if kind=='sigmoid' else ([15,8,1] if kind=='affinepower' else [15,8,4,.2,1]))))
 p=np.array(start)
 for mode in ['deriv','step','flow']:
  target=A.dy.to_numpy() if mode=='deriv' else (A.y.to_numpy()[1:] if mode=='step' else A.y.to_numpy())
  res=least_squares(lambda p:prediction(p,A,kind,mode)-target,p,bounds=(lo,hi),max_nfev=300,ftol=1e-10,xtol=1e-10,gtol=1e-10,x_scale='jac');p=res.x
  out=dict(kind=kind,mode=mode,p=p.tolist(),train_d=np.sqrt(np.mean((prediction(p,A,kind,'deriv')-A.dy)**2)),val_d=np.sqrt(np.mean((prediction(p,B,kind,'deriv')-B.dy)**2)),train_y=np.sqrt(np.mean((prediction(p,A,kind,'flow')[1:]-A.y.to_numpy()[1:])**2)),val_y=np.sqrt(np.mean((prediction(p,B,kind,'flow')[1:]-B.y.to_numpy()[1:])**2)))
  print(out,flush=True);results.append(out)
json.dump(results,open('relaxation_results.json','w'),indent=2)
