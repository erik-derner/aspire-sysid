"""Deterministic exploration and final training fits; no test access."""
import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
from numba import njit
from pathlib import Path
D={s:pd.read_csv('data/'+s+'.csv').to_numpy() for s in ['train','val']}
# arrays columns p,valve,flow,dp
# families: 0 linear; 1 smoothed root; 2 smoothed power; 3 compressible;
# 4 mixed viscous/inertial; 5 density root; 6 root with storage.
# valvekind: 0 monotone cubic Bernstein, 1 power opening, 2 exponential opening
@njit
def conductance(t,v,vk):
 v=min(max(v/100.,0.),1.);x=1-v
 if vk==0: return t[1]*(1-v**3)+t[2]*(1-3*v*v+2*v**3)+t[3]*x**3
 if vk==1: return t[1]*x**t[2]
 k=t[2]
 if abs(k)<1e-8:return t[1]*x
 return t[1]*np.expm1(k*x)/np.expm1(k)
@njit
def f(t,p,v,q,fam,vk):
 g=conductance(t,v,vk); p0=t[4]; z=max(p-p0,0.); rev=.1*min(p-p0,0.)
 # positive-pressure discharge only, plus valve-independent numerical vacuum relaxation
 if fam==0: h=z
 elif fam==1 or fam==6: h=z/(z*z+t[5]**2)**.25
 elif fam==2: h=z*(z*z+t[5]**2)**((t[6]-1)/2)
 elif fam==3:
  # dimensionless normalized compressible nozzle flux; regularize pressure drop near atmosphere
  pu=max(p,p0);rat=max(p0/pu,(2/2.4)**(1.4/.4))
  h=(pu/p0)*np.sqrt(max(7*(rat**(2/1.4)-rat**(2.4/1.4)),0.))
  h*=np.sqrt(z/np.sqrt(z*z+t[5]**2)) if z>0 else 0.
 elif fam==4:
  h=2*z/(np.sqrt(4*z+(t[5]*g)**2+1e-12)+t[5]*g)
 elif fam==5: h=z/(z*z+t[5]**2)**.25*np.sqrt(max(p,p0)/p0)
 else: h=z
 ans=t[0]*q-g*h-rev
 if fam==6: ans/=1+t[6]*z
 return ans
@njit
def step(t,p,v,q,fam,vk):
 k1=f(t,p,v,q,fam,vk);k2=f(t,p+2.5*k1,v,q,fam,vk);k3=f(t,p+2.5*k2,v,q,fam,vk);k4=f(t,p+5*k3,v,q,fam,vk)
 return p+5/6*(k1+2*k2+2*k3+k4)
@njit
def rollout(t,d,fam,vk):
 n=len(d);y=np.empty(n);y[0]=d[0,0]
 for i in range(n-1):
  y[i+1]=step(t,y[i],d[i,1],d[i,2],fam,vk)
  if not np.isfinite(y[i+1]) or abs(y[i+1])>20:
   for j in range(i+1,n):y[j]=20.
   break
 return y
@njit
def transitions(t,d,fam,vk):
 r=np.empty(len(d)-1)
 for i in range(len(r)):r[i]=step(t,d[i,0],d[i,1],d[i,2],fam,vk)-d[i+1,0]
 return r

def specs(fam,vk):
 x=[.0013,.06,.05,.000001,1.,.02,.55]
 lo=[.0001,1e-8,0.,0.,.97,.001,.25];hi=[.005,.5,.5,.5,1.02,.15,1.0]
 if fam==0:x[1:4]=[.001,.19,.001]
 if fam==3:x[1:4]=[.035,.035,.001]
 if fam==4:x[5]=5.;lo[5]=2.;hi[5]=20.
 if fam==6:x[6]=.1;lo[6]=0.;hi[6]=5.
 if vk==1:x[1:4]=[.12,.9,0.];lo[2]=.25;hi[2]=3.
 if vk==2:x[1:4]=[.12,-1.,0.];lo[2]=-5.;hi[2]=5.
 # unused parameters not passed to solver
 active=[0,1,4]+([2,3] if vk==0 else [2])+([5] if fam!=0 else [])+([6] if fam in [2,6] else [])
 return np.array(x),np.array(lo),np.array(hi),active

def fit(label,fam,vk):
 t,lo,hi,active=specs(fam,vk);initial=t.copy();start=time.time()
 def expand(x):tt=t.copy();tt[active]=x;return tt
 # One-step least squares initialization. All transitions including initial transient are retained.
 opt1=least_squares(lambda x:transitions(expand(x),D['train'],fam,vk),t[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=500,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 first=expand(opt1.x); t=first.copy()
 # Full free-run pressure training SSE refinement, all parameters together.
 opt2=least_squares(lambda x:rollout(expand(x),D['train'],fam,vk)[1:]-D['train'][1:,0],t[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=1000,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 final=expand(opt2.x);out={'label':label,'family':fam,'valvekind':vk,'initial':initial.tolist(),'bounds':[lo.tolist(),hi.tolist()],'active':active,'transition_fit':first.tolist(),'parameters':final.tolist(),'nfev':[opt1.nfev,opt2.nfev],'optimality':opt2.optimality,'metrics':{}}
 for name,d in D.items():
  r=rollout(final,d,fam,vk)-d[:,0];tr=transitions(final,d,fam,vk)
  out['metrics'][name]={'simulation_rmse':float(np.sqrt(np.mean(r[1:]**2))),'simulation_bias':float(r[1:].mean()),'transition_rmse':float(np.sqrt(np.mean(tr**2))),'transition_bias':float(tr.mean()),'flow_change_correlation':float(np.corrcoef(tr,np.diff(d[:,2]))[0,1]),'valve_change_correlation':float(np.corrcoef(tr,np.diff(d[:,1]))[0,1]),'min':float(np.min(r+d[:,0])),'max':float(np.max(r+d[:,0]))}
 print(label,'params',final,'metrics',out['metrics'],'seconds',time.time()-start,flush=True)
 return out

if __name__=='__main__':
 configs=[('linear',0,0),('root',1,0),('power',2,0),('nozzle',3,0),('resistance',4,0),('density',5,0),('storage',6,0),('root_valvepower',1,1),('root_valveexp',1,2)]
 out=[]
 for label,fam,vk in configs:out.append(fit(label,fam,vk));Path('fit_results.json').write_text(json.dumps(out,indent=2))
