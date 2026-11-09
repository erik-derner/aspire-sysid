import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv')
def design(d,degree):
 p=PolynomialFeatures(degree);return p.fit_transform(np.c_[d.y-1,d.x1/100,d.x2/30]),p.powers_
# Fit numerator with denominator depending state or inputs using variable projection.
results=[]
for degree in [1,2,3]:
 X,pow=design(A,degree);V,_=design(B,degree)
 for kind in ['state','input','all','statequad']:
  def den(q,d):
   h=d.y.to_numpy()-1;u=d.x1.to_numpy()/100;v=d.x2.to_numpy()/30
   if kind=='state':return 1+q[0]*h
   if kind=='input':return 1+q[0]*u+q[1]*v
   if kind=='all':return 1+q[0]*h+q[1]*u+q[2]*v
   return 1+q[0]*h+q[1]*h*h
  nq={'state':1,'input':2,'all':3,'statequad':2}[kind]
  def res(q):
   D=den(q,A);Z=X/D[:,None];c=np.linalg.lstsq(Z,A.dy,rcond=None)[0];return Z@c-A.dy
  opt=least_squares(res,np.zeros(nq),bounds=(-.6,10),max_nfev=150);q=opt.x;c=np.linalg.lstsq(X/den(q,A)[:,None],A.dy,rcond=None)[0]
  def sim(d):
   u=d.x1.to_numpy()/100;v=d.x2.to_numpy()/30;yp=np.empty(len(d));yp[0]=d.y.iloc[0]
   C=np.array([sum(c[j]*u**pw[1]*v**pw[2] for j,pw in enumerate(pow) if pw[0]==i) for i in range(degree+1)])
   def f(y,k):
    h=y-1
    if kind=='state':D=1+q[0]*h
    elif kind=='input':D=1+q[0]*u[k]+q[1]*v[k]
    elif kind=='all':D=1+q[0]*h+q[1]*u[k]+q[2]*v[k]
    else:D=1+q[0]*h+q[1]*h*h
    return np.polynomial.polynomial.polyval(h,C[:,k])/D
   for k in range(len(d)-1):
    s=yp[k];a=f(s,k);b=f(s+2.5*a,k);e=f(s+2.5*b,k);h=f(s+5*e,k);yp[k+1]=s+5/6*(a+2*b+2*e+h)
    if not np.isfinite(yp[k+1]) or abs(yp[k+1])>100:return np.full(len(d),1e3)
   return yp
  out=dict(degree=degree,kind=kind,q=q.tolist(),c=c.tolist(),powers=pow.tolist(),train_d=np.sqrt(np.mean(res(q)**2)),val_d=np.sqrt(np.mean((V/den(q,B)[:,None]@c-B.dy)**2)),train_y=np.sqrt(np.mean((sim(A)[1:]-A.y.to_numpy()[1:])**2)),val_y=np.sqrt(np.mean((sim(B)[1:]-B.y.to_numpy()[1:])**2)))
  print(out,flush=True);results.append(out)
json.dump(results,open('rational_results.json','w'),indent=2)
# Alignment diagnostic only, not prospective submitted models
for shift in [-1,0,1]:
 d=A.copy();d.x2=d.x2.shift(shift);d=d.dropna();v=B.copy();v.x2=v.x2.shift(shift);v=v.dropna()
 X,_=design(d,2);V,_=design(v,2);c=np.linalg.lstsq(X,d.dy,rcond=None)[0];print('alignment',shift,'rms',np.sqrt(np.mean((X@c-d.dy)**2)),np.sqrt(np.mean((V@c-v.dy)**2)),c)
