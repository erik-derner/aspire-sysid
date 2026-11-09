import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv');
def sim_poly(c,p,d):
 powers=p.powers_;y=np.empty(len(d));y[0]=d.y.iloc[0]
 x=d.x1.to_numpy()/100;z=d.x2.to_numpy()/30
 # coefficient for each y power, input computed outside loop
 C=np.array([sum(c[j]*x**pw[1]*z**pw[2] for j,pw in enumerate(powers) if pw[0]==i) for i in range(p.degree+1)])
 for k in range(len(y)-1):
  cc=C[:,k]
  def f(s):return np.polynomial.polynomial.polyval(s,cc)
  s=y[k];a=f(s);b=f(s+2.5*a);e=f(s+2.5*b);h=f(s+5*e);y[k+1]=s+5/6*(a+2*b+2*e+h)
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:return np.full(len(y),1e3)
 return y
results=[]
for deg in [1,2,3,4]:
 p=PolynomialFeatures(deg);X=p.fit_transform(np.c_[A.y,A.x1/100,A.x2/30]);V=p.transform(np.c_[B.y,B.x1/100,B.x2/30]);c=np.linalg.lstsq(X,A.dy,rcond=None)[0]
 for fit in ['deriv','flow']:
  if fit=='flow':
   # fit all state samples single uninterrupted trajectory
   res=least_squares(lambda c:sim_poly(c,p,A)-A.y,c,x_scale='jac',max_nfev=100,ftol=1e-9);c=res.x
  pred=sim_poly(c,p,A);v=sim_poly(c,p,B)
  out=dict(degree=deg,fit=fit,c=c.tolist(),powers=p.powers_.tolist(),train_d=float(np.sqrt(np.mean((X@c-A.dy)**2))),val_d=float(np.sqrt(np.mean((V@c-B.dy)**2))),train_y=float(np.sqrt(np.mean((pred[1:]-A.y.to_numpy()[1:])**2))),val_y=float(np.sqrt(np.mean((v[1:]-B.y.to_numpy()[1:])**2))))
  print(out,flush=True);results.append(out)
json.dump(results,open('poly_results.json','w'),indent=2)
