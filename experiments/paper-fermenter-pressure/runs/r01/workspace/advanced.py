import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
D={s:pd.read_csv('data/'+s+'.csv').to_numpy() for s in ['train','val']}
# a,c,atm,delta,b,vc,w,n,r,g ; spline appended interval slopes scaled conductance reference
K=np.array([0.,30.,50.,65.,75.,85.,95.,100.])
@njit
def C(v,t,kind):
 a,c,atm,d,b,vc,w,n,r,g=t[:10];x=max(0.,1-v/100.)
 if kind==0:return c*(x/.3)**b
 if kind==1:
  z=1/(1+np.exp((v-vc)/w));z100=1/(1+np.exp((100-vc)/w));z70=1/(1+np.exp((70-vc)/w))
  return c*max(0.,z-z100)/(z70-z100)
 if kind==2:
  cval=0.
  for j in range(7):cval+=t[10+j]*min(max(K[j+1]-v,0.),K[j+1]-K[j])
  return cval
 if kind==3:return c*np.tanh(x/b)/np.tanh(.3/b)
 if kind==4:return c*(np.exp(b*(.7-v/100.))-np.exp(-.3*b))/(1-np.exp(-.3*b))
 return 0.
@njit
def rhs(p,v,f,t,kind,drive,inlet):
 a,c,atm,d,b,vc,w,n,r,g=t[:10];z=p-atm
 if drive==0:h=z/(z*z+d*d)**.25
 elif drive==1:h=2*z/(np.sqrt(d)+np.sqrt(d+4*abs(z)))
 elif drive==2:h=z*(z*z+d*d)**((n-1)/2)
 elif drive==3:
  zz=(p*p-atm*atm)/(2*atm)
  h=2*zz/(np.sqrt(d)+np.sqrt(d+4*abs(zz)))
 elif drive==4:h=z*(1+g/(z*z+d*d)**.25)
 elif drive==5:h=z/(z*z+d*d)**.25*np.sqrt(max(.1,p+atm)/(2*atm))
 elif drive==6:h=z*(z*z+d*d)**((n-1)/2)
 else:h=z
 q=a*max(f,0.)
 if inlet==1:q=a*20*(max(f,0.)/20)**r
 if inlet==2:q=a*f/(1+r*max(f,0.)/20)
 out=q-C(v,t,kind)*h
 if drive==6:out/=1+g/max(.1,p)**2
 return out
@njit
def sim(d,t,kind,drive,inlet):
 y=np.empty(len(d));y[0]=d[0,0]
 for k in range(len(d)-1):
  p=y[k];v=d[k,1];f=d[k,2];k1=rhs(p,v,f,t,kind,drive,inlet);k2=rhs(p+2.5*k1,v,f,t,kind,drive,inlet);k3=rhs(p+2.5*k2,v,f,t,kind,drive,inlet);k4=rhs(p+5*k3,v,f,t,kind,drive,inlet);y[k+1]=p+5*(k1+2*k2+2*k3+k4)/6
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:y[k+1:]=100;break
 return y
@njit
def local(d,t,kind,drive,inlet):
 y=np.empty(len(d)-1)
 for k in range(len(d)-1):
  p,v,f=d[k,:3];k1=rhs(p,v,f,t,kind,drive,inlet);k2=rhs(p+2.5*k1,v,f,t,kind,drive,inlet);k3=rhs(p+2.5*k2,v,f,t,kind,drive,inlet);k4=rhs(p+5*k3,v,f,t,kind,drive,inlet);y[k]=p+5*(k1+2*k2+2*k3+k4)/6-d[k+1,0]
 return y

def setup(kind,drive,inlet):
 t=np.array([.0013,.053,.994,.05,1.,82.,20.,.55,1.,.2]+[.002]*7)
 lo=np.array([.0001,.0001,.985,.003,.05,0.,2.,.25,.5,0.]+[0.]*7)
 hi=np.array([.004,.3,1.01,2.,15.,98.,70.,1.2,2.,5.]+[.006]*7)
 active=[0,2]
 if kind==2:active+=list(range(10,17))
 else:active+=[1]
 if kind in [0,3,4]:active+=[4]
 if kind==1:active += [5,6]
 if drive!=7:active += [3]
 if drive in [2,6]:active += [7]
 if drive in [4,6]:active += [9]
 if inlet>0:
  active += [8]
  if inlet==2:t[8]=.1;lo[8]=0.;hi[8]=5.
 return t,lo,hi,np.array(active)

def fit(kind,drive,inlet,files=['train'],start=None,criterion='simulation',max_nfev=300):
 t,lo,hi,active=setup(kind,drive,inlet)
 if start is not None:t=np.array(start).copy()
 initial=t.copy()
 def unpack(x):
  u=t.copy();u[active]=x;return u
 def obj(x):
  u=unpack(x)
  if criterion=='simulation':return np.concatenate([sim(D[s],u,kind,drive,inlet)[1:]-D[s][1:,0] for s in files])
  return np.concatenate([local(D[s],u,kind,drive,inlet) for s in files])
 res=least_squares(obj,t[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=max_nfev,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 u=unpack(res.x)
 metrics={s:float(np.sqrt(np.mean((sim(D[s],u,kind,drive,inlet)[1:]-D[s][1:,0])**2))) for s in D}
 lm={s:float(np.sqrt(np.mean(local(D[s],u,kind,drive,inlet)**2))) for s in D}
 return {'kind':kind,'drive':drive,'inlet':inlet,'params':u.tolist(),'active':active.tolist(),'initial':initial.tolist(),'rmse':metrics,'local_rmse':lm,'nfev':res.nfev,'cost':res.cost,'optimality':res.optimality,'success':bool(res.success),'files':files,'criterion':criterion}
if __name__=='__main__':
 results=[]
 specs=[(k,d,i) for k in [0,1,2] for d in [0,1,2,3,4,5,6] for i in ([0,1] if d in [0,1,2] else [0])]
 for k,d,i in specs:
  q=fit(k,d,i)
  results.append(q);print(k,d,i,'rmse',q['rmse'],'params',np.round(q['params'][:10],6),'slopes',np.round(q['params'][10:],6) if k==2 else '',q['nfev'],flush=True)
  json.dump(results,open('advanced_results.json','w'),indent=2)
