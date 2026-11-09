import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
from advanced import D,C
# use advanced parameters appended ell, ratio; delta unused unless smoothing option
@njit
def rhs(p,v,f,t,kind,law):
 a,c,atm,d,b,vc,w,n,r,g=t[:10];ell,ratio=t[17:19];z=p-atm
 cv=C(v,t,kind)
 if law in [0,1,2]:
  if kind==0: lc=ell*c*(max(0.,1-v/100.)/.3)**(b*(1-ratio))
  else:lc=ell*cv
  if law==1:zz=(p*p-atm*atm)/(2*atm)
  else:zz=z
  out=cv*2*zz/(lc+np.sqrt(lc*lc+4*abs(zz)+1e-8))
 elif law==3:
  out=cv*z/(z*z+d*d)**.25+ell*max(0.,1-v/100.)**ratio*z
 else:out=cv*z*(z*z+d*d)**((n-1)/2)
 return a*f-out
@njit
def sim(d,t,kind,law):
 y=np.empty(len(d));y[0]=d[0,0]
 for k in range(len(d)-1):
  p=y[k];v=d[k,1];f=d[k,2];k1=rhs(p,v,f,t,kind,law);k2=rhs(p+2.5*k1,v,f,t,kind,law);k3=rhs(p+2.5*k2,v,f,t,kind,law);k4=rhs(p+5*k3,v,f,t,kind,law);y[k+1]=p+5*(k1+2*k2+2*k3+k4)/6
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:y[k+1:]=100;break
 return y

def fit(kind,law,files=['train'],start=None,fixed_ratio=None):
 t=np.array([.0013,.06,.994,.05,1.,82.,20.,.55,1.,.2]+[.002]*7+[3.,0.])
 lo=np.array([.0001,.0001,.985,.015,.1,0.,2.,.25,.5,0.]+[0.]*7+[.01,0.])
 hi=np.array([.004,.3,1.01,.3,8.,98.,70.,1.2,2.,5.]+[.006]*7+[30.,1.])
 active=[0,2,17]
 if kind==2:active+=list(range(10,17))
 else:active+=[1]
 if kind==0:active+=[4]
 if kind==1:active += [5,6]
 if kind==0 and fixed_ratio is None:active+=[18]
 if fixed_ratio is not None:t[18]=fixed_ratio
 if law==3:
  active += [3]
  if 18 not in active:active +=[18]
  t[17]=.04;hi[17]=.3;lo[17]=0.;t[18]=2.;lo[18]=.2;hi[18]=6.
 if start is not None:t=np.array(start).copy()
 initial=t.copy();active=np.array(active)
 def unpack(x):u=t.copy();u[active]=x;return u
 res=least_squares(lambda x:np.concatenate([sim(D[s],unpack(x),kind,law)[1:]-D[s][1:,0] for s in files]),t[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 u=unpack(res.x);metrics={s:float(np.sqrt(np.mean((sim(D[s],u,kind,law)[1:]-D[s][1:,0])**2))) for s in D}
 return {'kind':kind,'law':law,'params':u.tolist(),'initial':initial.tolist(),'active':active.tolist(),'files':files,'fixed_ratio':fixed_ratio,'rmse':metrics,'nfev':res.nfev,'cost':res.cost,'success':bool(res.success)}
if __name__=='__main__':
 results=[]
 for k,l,r in [(0,0,0.),(0,0,None),(1,0,0.),(2,0,0.),(0,1,0.),(0,1,None),(1,1,0.),(2,1,0.),(0,3,None),(1,3,None),(2,3,None)]:
  z=fit(k,l,fixed_ratio=r);results.append(z);print(k,l,r,z['rmse'],np.round(z['params'][:10],6),np.round(z['params'][17:],6),z['nfev'],flush=True)
  json.dump(results,open('resistance_results.json','w'),indent=2)
