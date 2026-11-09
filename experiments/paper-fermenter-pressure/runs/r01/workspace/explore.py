import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
from numba import njit
D={s:pd.read_csv('data/'+s+'.csv').to_numpy() for s in ['train','val']}
# columns p valve flow dp
@njit
def conduct(v,t,kind):
 a,c,b,atm,n,eps=t[:6]; x=max(0.,1-v/100.)
 if kind==0: return c*(x/.3)**b
 if kind==1: return c*(np.exp(b*(.7-v/100.))-np.exp(-.3*b))/(1-np.exp(-.3*b))
 if kind==2:
  vc,w=t[6:8]
  z=1/(1+np.exp((v-vc)/w)); z100=1/(1+np.exp((100-vc)/w)); z70=1/(1+np.exp((70-vc)/w))
  return c*max(0.,z-z100)/(z70-z100)
 if kind==3:
  vc,w=t[6:8]
  return c*(x/.3)*(1+np.exp((70-vc)/w))/(1+np.exp((v-vc)/w))
 return c*x/.3
@njit
def rhs(p,v,f,t,kind,drive):
 a,c,b,atm,n,eps=t[:6]; z=p-atm
 if drive==0: h=z
 elif drive==1: h=z/(z*z+eps*eps)**.25
 elif drive==2: h=z*(z*z+eps*eps)**((n-1)/2)
 elif drive==3: h=z/(z*z+eps*eps)**.25*np.sqrt(max(.05,p+atm))
 else: h=z*(z*z+eps*eps)**((n-1)/2)*(max(.05,p)/atm)**t[8]
 return a*f-conduct(v,t,kind)*h
@njit
def simulate(d,t,kind,drive):
 out=np.empty(len(d));out[0]=d[0,0]
 for i in range(len(d)-1):
  p=out[i];v=d[i,1];f=d[i,2]
  k1=rhs(p,v,f,t,kind,drive);k2=rhs(p+2.5*k1,v,f,t,kind,drive);k3=rhs(p+2.5*k2,v,f,t,kind,drive);k4=rhs(p+5*k3,v,f,t,kind,drive)
  out[i+1]=p+5*(k1+2*k2+2*k3+k4)/6
  if not np.isfinite(out[i+1]) or abs(out[i+1])>100:
   out[i+1:]=100;break
 return out
@njit
def dr(d,t,kind,drive):
 out=np.empty(len(d)-1)
 for i in range(len(out)): out[i]=rhs(d[i,0],d[i,1],d[i,2],t,kind,drive)-d[i,3]
 return out

def setup(kind,drive):
 t=np.array([.0011,.035,3.,.993,.5,.015,50.,15.,.5])
 lo=np.array([.0001,.0001,.15,.97,.2,.001,0.,2.,-1.]);hi=np.array([.004,.3,15.,1.02,1.5,.15,95.,50.,2.])
 active=[0,1,3]
 if kind in [0,1]:active += [2]
 if kind in [2,3]:active += [6,7]
 if drive in [1,2,3,4]:active += [5]
 if drive in [2,4]:active += [4]
 if drive==4:active += [8]
 return t,lo,hi,np.array(active)

def fit(kind,drive,simfit=True,files=['train'],start=None,max_nfev=250):
 t,lo,hi,active=setup(kind,drive)
 if start is not None:t=np.array(start)
 def unpack(x):
  u=t.copy();u[active]=x;return u
 def obj(x):
  u=unpack(x)
  if simfit:return np.concatenate([simulate(D[s],u,kind,drive)[1:]-D[s][1:,0] for s in files])
  return np.concatenate([dr(D[s],u,kind,drive) for s in files])
 fit=least_squares(obj,t[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=max_nfev,ftol=1e-9,xtol=1e-9,gtol=1e-9)
 u=unpack(fit.x)
 metrics={s:float(np.sqrt(np.mean((simulate(D[s],u,kind,drive)[1:]-D[s][1:,0])**2))) for s in D}
 dm={s:float(np.sqrt(np.mean(dr(D[s],u,kind,drive)**2))) for s in D}
 return {'kind':kind,'drive':drive,'params':u.tolist(),'active':active.tolist(),'rmse':metrics,'derivative_rmse':dm,'nfev':fit.nfev,'cost':fit.cost,'optimality':fit.optimality,'success':bool(fit.success)}
if __name__=='__main__':
 results=[]
 for kind in [0,1,2,3]:
  for drive in [0,1,2,3,4]:
   st=time.time();r=fit(kind,drive,False);q=fit(kind,drive,True,start=r['params']);q['derivative_fit']=r
   results.append(q);print(kind,drive,'rmse',q['rmse'],'params',np.round(q['params'],6),'nfev',q['nfev'],'time',round(time.time()-st,1),flush=True)
   with open('explore_results.json','w') as f:json.dump(results,f,indent=2)
