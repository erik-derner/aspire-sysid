import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
from helper_rollout_core import T,V,nt,nv,mT,mV
@njit
def accel(y,v,u,p,mode):
 a,b,c,d,f,w,h,s,g=p
 F=a*np.sin(y)+b*v+c*u+d+h*np.cos(y)
 z=np.exp(-(v/s)**2)
 dead=F-min(max(F,-g),g)
 if mode==0:return (F-f*np.tanh(v/w))*(1-z)+dead*z
 if mode==1:return F-f*np.tanh(v/w)-min(max(F,-g),g)*z
 return F-f*np.tanh(v/w)*(1-z)-min(max(F,-g),g)*z
@njit
def rollout(p,A,ns,mode):
 out=np.empty(A.shape[0]);start=0
 for n in ns:
  y=A[start,0];v=A[start,1];out[start]=y
  for j in range(start,start+n-1):
   u=A[j,2];a=accel(y,v,u,p,mode);b=accel(y+.005*v,v+.005*a,u,p,mode);c=accel(y+.005*(v+.005*a),v+.005*b,u,p,mode);d=accel(y+.01*(v+.005*b),v+.01*c,u,p,mode)
   y+=.01/6*(v+2*(v+.005*a)+2*(v+.005*b)+(v+.01*c));v+=.01/6*(a+2*b+2*c+d)
   out[j+1]=y
  start+=n
 return out
results=[]
for mode in [0,1]:
 for s0 in [.3,1.]:
  p0=np.array([-109.8,-1.65,27.9,-.66,20.67,.15,4.12,s0,20.67]);lo=[-180,-10,5,-15,0,.09,-20,.05,1];hi=[-50,0,50,15,60,3,30,4,60]
  def fun(p):return (rollout(p,T,nt,mode)-T[:,0])[mT]
  fit=least_squares(fun,p0,bounds=(lo,hi),max_nfev=220,diff_step=1e-4,ftol=2e-8,xtol=2e-8,gtol=2e-8)
  p=fit.x;rt=rollout(p,T,nt,mode)-T[:,0];rv=rollout(p,V,nv,mode)-V[:,0]
  r=dict(mode=mode,start=p0.tolist(),params=p.tolist(),lower=lo,upper=hi,train_rmse=float(np.sqrt(np.mean(rt[mT]**2))),val_rmse=float(np.sqrt(np.mean(rv[mV]**2))),evaluations=fit.nfev)
  print(json.dumps(r),flush=True);results.append(r);json.dump(results,open('stick_results.json','w'),indent=2)
