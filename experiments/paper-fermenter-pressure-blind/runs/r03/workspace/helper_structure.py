import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv');X=A[['y','x1','x2']].values;V=B[['y','x1','x2']].values;z=A.dy.values;w=B.dy.values
rows=[]
def record(name,F,G,names):
 c=np.linalg.lstsq(F,z,rcond=None)[0];r=z-F@c;v=w-G@c
 row=dict(name=name,parameters=dict(zip(names,c.tolist())),train_RMSE=float(np.sqrt(np.mean(r*r))),val_RMSE=float(np.sqrt(np.mean(v*v))),val_bias=float(v.mean()));rows.append(row);print(row)
 return c
for terms in [['one','y','u','v','yu'],['one','y','u','v','yu','u2'],['one','y','u','v','yu','u2','yu2'],['one','y','u','v','yu','u2','v2'],['one','y','u','v','yu','u2','yv','y2'],['one','y','u','v','yu','u2','yu2','v2','v3']]:
 def mat(T):
  y,u,v=T.T;u=u/60;v=v/18
  lib=dict(one=np.ones(len(y)),y=y,u=u,v=v,yu=y*u,u2=u*u,yu2=y*u*u,v2=v*v,yv=y*v,y2=y*y,v3=v**3)
  return np.stack([lib[t] for t in terms],axis=1)
 record('restricted_'+str(len(terms))+'_'+'_'.join(terms),mat(X),mat(V),terms)
# diagnostic addition of forward x2 increment to polynomial3 and restricted6 (not deployable)
from sklearn.preprocessing import PolynomialFeatures
poly=PolynomialFeatures(3);mu=X.mean(0);sd=X.std(0);F=poly.fit_transform((X-mu)/sd);G=poly.transform((V-mu)/sd)
dx=np.r_[np.diff(A.x2),0];dv=np.r_[np.diff(B.x2),0]
record('poly3_plus_future_x2_DIAGNOSTIC',np.c_[F,dx],np.c_[G,dv],poly.get_feature_names_out(['Y','U','V']).tolist()+['dx2'])
for shift in [-1,1]:
 XS=X.copy();VS=V.copy();XS[:,2]=np.roll(XS[:,2],shift);VS[:,2]=np.roll(VS[:,2],shift)
 FF=poly.fit_transform((XS-mu)/sd);GG=poly.transform((VS-mu)/sd); record('poly3_x2shift'+str(shift)+'_DIAGNOSTIC',FF,GG,poly.get_feature_names_out(['Y','U','V']).tolist())
# Shifted-power relaxation using rate positive on train/val for c>max(u)
for kind in ['linear','quadratic','power','powered_state','square_y','free_outflow']:
 def f(p,T):
  y,u,v=T.T;u=u/60;v=v/18
  base=np.maximum(p[4]-u,1e-8)
  if kind=='linear':return p[0]+p[1]*v-p[2]*(y-p[3])*base
  if kind=='quadratic':return p[0]+p[1]*v-p[2]*(y-p[3])*base**2
  if kind=='power':return p[0]+p[1]*v-p[2]*(y-p[3])*base**p[5]
  if kind=='powered_state':return p[0]+p[1]*v**p[6]-p[2]*np.sign(y-p[3])*np.abs(y-p[3])**p[7]*base**p[5]
  if kind=='square_y':return p[0]+p[1]*v-p[2]*(y*y-p[3])*base**p[5]
  if kind=='free_outflow':return p[0]+p[1]*v-p[2]*(y-p[3])*(p[4]-u)**p[5]
 lo=[-1,-1,0,-5,1.58,.1,.1,.1];hi=[1,1,100,1.5,5,5,5,5]
 if kind=='free_outflow':lo[4]=.1;lo[5]=1;hi[5]=1.00000001
 best=None
 for y0 in [0,1]:
  p0=[0,.01,.1,y0,1.7,1,1,1]
  res=least_squares(lambda p:f(p,X)-z,p0,bounds=(lo,hi),max_nfev=3000,xtol=1e-10,ftol=1e-10,gtol=1e-10)
  if best is None or res.cost<best.cost:best=res
 p=best.x;r=z-f(p,X);rv=w-f(p,V)
 row=dict(name=kind,parameters=p.tolist(),train_RMSE=float(np.sqrt(np.mean(r*r))),val_RMSE=float(np.sqrt(np.mean(rv*rv))),val_bias=float(rv.mean()));rows.append(row);print(row)
json.dump(rows,open('helper_structure_results.json','w'),indent=2)
