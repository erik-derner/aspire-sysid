import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv');X=A[['y','x1','x2']].values;V=B[['y','x1','x2']].values;z=A.dy.values;w=B.dy.values
results=[]
forms={
 'exp_decay':'p[0]+p[1]*v-p[2]*(y-p[3])*np.exp(-p[4]*u)',
 'exp_decay_power':'p[0]+p[1]*v**p[5]-p[2]*np.maximum(y-p[3],1e-9)**p[6]*np.exp(-p[4]*u)',
 'power_decay':'p[0]+p[1]*v-p[2]*(y-p[3])/(1+p[4]*u)**p[5]',
 'reciprocal_decay':'p[0]+p[1]*v-p[2]*(y-p[3])/(1+p[4]*u)',
 'poly_decay':'p[0]+p[1]*v-(p[2]+p[4]*u+p[5]*u*u)*(y-p[3])',
 'exp_decay_xprod':'p[0]+p[1]*v-p[2]*(y-p[3])*np.exp(-p[4]*u-p[5]*v)',
 'exp_affine':'p[0]+p[1]*v+p[5]*u-p[2]*(y-p[3])*np.exp(-p[4]*u)',
 'exp_decay_log':'p[0]+p[1]*v-p[2]*np.log(np.maximum(y-p[3],1e-9))*np.exp(-p[4]*u)',
 'sat_equil':'p[0]+p[1]*v+p[2]*u/(p[4]+u)-p[5]*(y-p[3])',
}
for name,expr in forms.items():
 def f(p,T):
  y,u,v=T.T;u=u/60;v=v/18
  return eval(expr)
 p0=[0,.01,.1,.97,1,1,1]
 if name=='poly_decay':p0=[0,.01,.1,.97,-.1,.03,1]
 if name=='exp_decay_log':p0[3]=0
 lo=[-1,-1,0,-5,0,-5,.1];hi=[1,1,100,.98,20,10,5]
 if name=='poly_decay':lo[4]=-10
 if name=='sat_equil':lo[5]=0
 starts=[p0]
 for c in [0.01,0.1,1,10]:q=p0.copy();q[2]=c;starts.append(q)
 best=None
 for p in starts:
  res=least_squares(lambda p:f(p,X)-z,p,bounds=(lo,hi),max_nfev=1500,xtol=1e-10,ftol=1e-10,gtol=1e-10)
  if best is None or res.cost<best.cost:best=res
 p=best.x;r=z-f(p,X);rv=w-f(p,V)
 row={'name':name,'expression':expr,'parameters':p.tolist(),'train_RMSE':float(np.sqrt(np.mean(r*r))),'val_RMSE':float(np.sqrt(np.mean(rv*rv))),'val_bias':float(rv.mean())}
 results.append(row);print(row)
 if name=='exp_decay':
  for D,R in [(A,r),(B,rv)]:
   print('residual stats')
   print('lag1',np.corrcoef(R[1:],R[:-1])[0,1])
   for col in ['x1','x2','y']:
    dx=np.diff(D[col]); print(col,'delta correlations',np.corrcoef(R[:-1],dx)[0,1],np.corrcoef(R[1:],dx)[0,1])
# polynomial3 residual diagnostics
poly=PolynomialFeatures(3);mu=X.mean(0);sd=X.std(0);F=poly.fit_transform((X-mu)/sd);G=poly.transform((V-mu)/sd);c=np.linalg.lstsq(F,z,rcond=None)[0]
for D,R in [(A,z-F@c),(B,w-G@c)]:
 print('poly3 residual lag1',np.corrcoef(R[1:],R[:-1])[0,1])
 for col in ['x1','x2','y']:
  dx=np.diff(D[col]);print(col,'delta correlations',np.corrcoef(R[:-1],dx)[0,1],np.corrcoef(R[1:],dx)[0,1])
 print('residual quantiles',np.quantile(R,[0,.1,.5,.9,1]))
 for col in ['y','x1','x2']:
  cuts=np.quantile(D[col],[0,.25,.5,.75,1]);print(col,'binned mean',[float(R[(D[col]>=cuts[i])&(D[col]<=cuts[i+1])].mean()) for i in range(4)])
json.dump(results,open('helper_relax_results.json','w'),indent=2)
