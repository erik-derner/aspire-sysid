import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv');results=[]
def basis(d,dq,dr):
 q=PolynomialFeatures(dq).fit_transform(d[['x1','x2']].to_numpy()/[100,30]);r=PolynomialFeatures(dr).fit_transform(d[['x1','x2']].to_numpy()/[100,30]);return q,r

def pred(p,d,dq,dr,mode):
 Q,R=basis(d,dq,dr);n=Q.shape[1];q=Q@p[:n];r=R@p[n:];z=5*r;F=1+z+z*z/2+z**3/6+z**4/24;G=5*(1+z/2+z*z/6+z**3/24)
 if mode=='deriv':return q+r*(d.y.to_numpy()-1)
 if mode=='step':return 1+F[:-1]*(d.y.to_numpy()[:-1]-1)+G[:-1]*q[:-1]
 y=np.empty(len(d));y[0]=d.y.iloc[0]
 for k in range(len(d)-1):
  y[k+1]=1+F[k]*(y[k]-1)+G[k]*q[k]
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:return np.full(len(d),1e3)
 return y
for dq,dr in [(2,1),(3,1),(3,2),(4,1),(4,2),(4,3)]:
 Q,R=basis(A,dq,dr);X=np.c_[Q,R*(A.y.to_numpy()-1)[:,None]];start=np.linalg.lstsq(X,A.dy,rcond=None)[0];p=start.copy()
 for mode in ['deriv','step','flow']:
  target=A.dy.to_numpy() if mode=='deriv' else (A.y.to_numpy()[1:] if mode=='step' else A.y.to_numpy())
  if mode!='deriv':
   opt=least_squares(lambda p:pred(p,A,dq,dr,mode)-target,p,max_nfev=150,x_scale='jac',ftol=1e-9);p=opt.x
  out=dict(dq=dq,dr=dr,mode=mode,p=p.tolist(),start=start.tolist(),train_d=np.sqrt(np.mean((pred(p,A,dq,dr,'deriv')-A.dy)**2)),val_d=np.sqrt(np.mean((pred(p,B,dq,dr,'deriv')-B.dy)**2)),train_y=np.sqrt(np.mean((pred(p,A,dq,dr,'flow')[1:]-A.y.to_numpy()[1:])**2)),val_y=np.sqrt(np.mean((pred(p,B,dq,dr,'flow')[1:]-B.y.to_numpy()[1:])**2)))
  print(out,flush=True);results.append(out)
json.dump(results,open('lpv_results.json','w'),indent=2)
