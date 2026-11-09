import numpy as np,pandas as pd,json
from numba import njit
from scipy.optimize import least_squares
@njit
def f(v,a,b,p,mode):
 k,g,y0,c,n=p[:5];z=v-y0
 rate=k*max(1-g*a,0.)
 if mode==0:return -rate*z+c*max(b,0)**n
 if mode==1:return -rate*np.log(max(v/y0,1e-10))+c*max(b,0)**n
 if mode==2:return -rate*z/(1+p[5]*max(z,0))+c*max(b,0)**n
 if mode==3:return -k/(1+np.exp((a-g)/p[5]))*z+c*max(b,0)**n
 return 0.
@njit
def sim(p,m,y,a,b):
 v=y[0];r=np.empty(len(y)-1)
 for i in range(len(r)):
  k1=f(v,a[i],b[i],p,m);k2=f(v+2.5*k1,a[i],b[i],p,m);k3=f(v+2.5*k2,a[i],b[i],p,m);k4=f(v+5*k3,a[i],b[i],p,m);v+=5/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(v) or abs(v)>100:
   for j in range(i,len(r)):r[j]=1000
   return r
  r[i]=v-y[i+1]
 return r
@njit
def dr(p,m,y,a,b,t):
 r=np.empty(len(y))
 for i in range(len(y)):r[i]=f(y[i],a[i],b[i],p,m)-t[i]
 return r
if __name__=='__main__':
 ds={n:pd.read_csv('data/'+n+'.csv') for n in ['train','val']};t=ds['train'];recs=[]
 for m in range(4):
  start=np.array([.18,.66,.99,.012,1.7]+([.5] if m==2 else ([.2] if m==3 else [])));lo=np.array([.001,.1,.7,0,.2]+([0] if m==2 else ([.01] if m==3 else [])));hi=np.array([.55,3,1.3,.5,8]+([10] if m==2 else ([2] if m==3 else [])))
  if m==3:start[1]=1.3
  args=(m,t.y.values,t.x1.values/60,t.x2.values/20)
  for stage in ['der','roll']:
   if stage=='der':init=start;sol=least_squares(lambda p:dr(p,*args,t.dy.values),start,bounds=(lo,hi),max_nfev=1000,ftol=1e-10,gtol=1e-10,xtol=1e-10)
   else:init=p;sol=least_squares(lambda p:sim(p,*args),p,bounds=(lo,hi),x_scale='jac',max_nfev=600,ftol=1e-10,gtol=1e-10,xtol=1e-10)
   p=sol.x;r={'mode':m,'stage':stage,'p':p.tolist(),'start':init.tolist(),'bounds':[lo.tolist(),hi.tolist()]}
   for fn,d in ds.items():
    aa=(m,d.y.values,d.x1.values/60,d.x2.values/20);r[fn+'_der']=float(np.mean(dr(p,*aa,d.dy.values)**2)**.5);r[fn+'_roll']=float(np.mean(sim(p,*aa)**2)**.5)
   print(r);recs.append(r);json.dump(recs,open('clamped_results.json','w'),indent=2)
