import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from scipy.linalg import lstsq
from numba import njit
from fit_polys import design
from sklearn.preprocessing import PolynomialFeatures
pw=PolynomialFeatures(2).fit(np.zeros((1,3))).powers_
@njit
def fun(v,a,b,p,mode):
 if mode==0:z=v-1
 elif mode==1:z=np.log(max(v,1e-8))
 elif mode==2:z=1-1/max(v,1e-8)
 else:z=v-1
 numer=p[0]+p[1]*z+p[2]*a+p[3]*b+p[4]*z*z+p[5]*z*a+p[6]*z*b+p[7]*a*a+p[8]*a*b+p[9]*b*b
 if mode==0:return numer/(1+p[10]*max(v-1,0))
 if mode in [1,2]:return numer
 if mode==3:return numer/(1+p[10]*a)
 if mode==4:return numer/(1+p[10]*b)
 if mode==5:return numer/(1+p[10]*(v-1)**2)
 return numer
@njit
def sim(p,mode,y,a,b):
 v=y[0];r=np.empty(len(y)-1)
 for i in range(len(r)):
  k1=fun(v,a[i],b[i],p,mode);k2=fun(v+2.5*k1,a[i],b[i],p,mode);k3=fun(v+2.5*k2,a[i],b[i],p,mode);k4=fun(v+5*k3,a[i],b[i],p,mode);v+=5/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(v) or abs(v)>100:
   for j in range(i,len(r)):r[j]=1000
   return r
  r[i]=v-y[i+1]
 return r
@njit
def dr(p,mode,y,a,b,t):
 r=np.empty(len(y))
 for i in range(len(y)):r[i]=fun(y[i],a[i],b[i],p,mode)-t[i]
 return r
if __name__=='__main__':
 ds={n:pd.read_csv('data/'+n+'.csv') for n in ['train','val']};tr=ds['train'];records=[]
 for mode in range(6):
  z=tr.y.values-1 if mode not in [1,2] else (np.log(tr.y.values) if mode==1 else 1-1/tr.y.values)
  zz=np.column_stack([z,tr.x1/60,tr.x2/20]);X=np.prod(zz[:,None,:]**pw[None,:,:],axis=2);start=lstsq(X,tr.dy)[0]
  if mode not in [1,2]:start=np.r_[start,0.]
  lo=np.r_[np.full(10,-np.inf),0.] if len(start)==11 else -np.inf;hi=np.r_[np.full(10,np.inf),20.] if len(start)==11 else np.inf
  args=(mode,tr.y.values,tr.x1.values/60,tr.x2.values/20)
  for stage in ['der','roll']:
   if stage=='der':
    init=start;sol=least_squares(lambda p:dr(p,*args,tr.dy.values),start,bounds=(lo,hi),max_nfev=800,x_scale='jac',ftol=1e-10,xtol=1e-10,gtol=1e-10)
   else:
    init=p;sol=least_squares(lambda p:sim(p,*args),p,bounds=(lo,hi),max_nfev=500,x_scale='jac',ftol=1e-10,xtol=1e-10,gtol=1e-10)
   p=sol.x;r={'mode':mode,'stage':stage,'p':p.tolist(),'start':init.tolist()}
   for fn,d in ds.items():
    aa=(mode,d.y.values,d.x1.values/60,d.x2.values/20);r[fn+'_der']=float(np.mean(dr(p,*aa,d.dy.values)**2)**.5);r[fn+'_roll']=float(np.mean(sim(p,*aa)**2)**.5)
   records.append(r);print(r);json.dump(records,open('rational_results.json','w'),indent=2)
