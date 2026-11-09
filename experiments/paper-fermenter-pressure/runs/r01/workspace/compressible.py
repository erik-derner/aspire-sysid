import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
from advanced import D,C
@njit
def rhs(p,v,f,t,kind):
 a,c,atm,delta=t[:4]
 up=max(p,atm);down=max(.01,min(p,atm));rr=max(down/up,(2/2.4)**3.5)
 raw2=3.5*up*up*(rr**(2/1.4)-rr**(2.4/1.4))
 h=np.sign(p-atm)*raw2/np.sqrt(raw2+delta*atm)
 return a*f-C(v,t,kind)*h
@njit
def sim(d,t,kind):
 y=np.empty(len(d));y[0]=d[0,0]
 for k in range(len(d)-1):
  p=y[k];v=d[k,1];f=d[k,2];k1=rhs(p,v,f,t,kind);k2=rhs(p+2.5*k1,v,f,t,kind);k3=rhs(p+2.5*k2,v,f,t,kind);k4=rhs(p+5*k3,v,f,t,kind);y[k+1]=p+5*(k1+2*k2+2*k3+k4)/6
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:y[k+1:]=100;break
 return y

def fit(kind,files=['train'],start=None):
 t=np.array([.0013,.05,.994,.03,1.,82.,20.,.55,1.,.2]+[.002]*7)
 lo=np.array([.0001,.0001,.985,.003,.05,0.,2.,.25,.5,0.]+[0.]*7)
 hi=np.array([.004,.3,1.01,.5,15.,98.,70.,1.2,2.,5.]+[.006]*7)
 active=[0,1,2,3]+([4] if kind==0 else [5,6])
 if start is not None:t=np.array(start).copy()
 initial=t.copy();active=np.array(active)
 def unpack(x):u=t.copy();u[active]=x;return u
 res=least_squares(lambda x:np.concatenate([sim(D[s],unpack(x),kind)[1:]-D[s][1:,0] for s in files]),t[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 u=unpack(res.x);metrics={s:float(np.sqrt(np.mean((sim(D[s],u,kind)[1:]-D[s][1:,0])**2))) for s in D}
 return {'kind':kind,'params':u.tolist(),'initial':initial.tolist(),'active':active.tolist(),'files':files,'rmse':metrics,'nfev':res.nfev,'cost':res.cost,'success':bool(res.success)}
if __name__=='__main__':
 results=[]
 for k in [0,1]:
  r=fit(k);print(k,r['rmse'],np.round(r['params'][:10],6),flush=True);z=fit(k,['train','val'],r['params']);z['train_only']=r;results.append(z);print('joint',k,z['rmse'],np.round(z['params'][:10],6),flush=True)
 json.dump(results,open('compressible_results.json','w'),indent=2)
