import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
def pack(d):
 gs=[g for _,g in d.groupby('trajectory')];return np.concatenate([g[['y','x1','x2']].values for g in gs]),np.array([len(g) for g in gs])
T,nt=pack(tr);V,nv=pack(va)
@njit
def acceleration(y,v,u,p,mode):
 a,b,c,d,e,w,k,h=p
 z=a*np.sin(k*y)+b*v+c*u+d+e*np.tanh(v/w)
 if mode==1:z+=h*u**3
 if mode==2:z+=h*v*np.abs(v)
 if mode==3:z+=h*np.cos(k*y)
 if mode==4:z+=h*u*np.abs(u)
 return z
@njit
def rollout(p,A,ns,mode):
 out=np.empty(A.shape[0]);start=0
 for n in ns:
  y=A[start,0];v=A[start,1];out[start]=y
  for j in range(start,start+n-1):
   u=A[j,2];k1v=acceleration(y,v,u,p,mode);k1y=v
   k2v=acceleration(y+.005*k1y,v+.005*k1v,u,p,mode);k2y=v+.005*k1v
   k3v=acceleration(y+.005*k2y,v+.005*k2v,u,p,mode);k3y=v+.005*k2v
   k4v=acceleration(y+.01*k3y,v+.01*k3v,u,p,mode);k4y=v+.01*k3v
   y+=.01/6*(k1y+2*k2y+2*k3y+k4y);v+=.01/6*(k1v+2*k2v+2*k3v+k4v)
   out[j+1]=y
  start+=n
 return out
mT=np.ones(len(T),bool);mT[np.r_[0,np.cumsum(nt)[:-1]]]=False
mV=np.ones(len(V),bool);mV[np.r_[0,np.cumsum(nv)[:-1]]]=False
results=[]
for mode in range(5):
 for fixedk in [True,False]:
  p0=np.array([-105,-1.5,26,1.5,-19,.3,1,0.])
  ids=np.array([0,1,2,3,4,5]+([] if fixedk else [6])+([] if mode==0 else [7]))
  lo=np.array([-180,-10,5,-15,-50,.015,.6,-10.]);hi=np.array([-50,0,50,15,0,2.,1.4,10.])
  def unpack(q):
   p=p0.copy();p[ids]=q;return p
  def fun(q):return (rollout(unpack(q),T,nt,mode)-T[:,0])[mT]
  fit=least_squares(fun,p0[ids],bounds=(lo[ids],hi[ids]),max_nfev=160,diff_step=1e-4,ftol=2e-8,xtol=2e-8,gtol=2e-8)
  p=unpack(fit.x);rt=rollout(p,T,nt,mode)-T[:,0];rv=rollout(p,V,nv,mode)-V[:,0]
  accel=acceleration(T[:,0],T[:,1],T[:,2],p,mode); av=acceleration(V[:,0],V[:,1],V[:,2],p,mode)
  r=dict(mode=mode,fixedk=fixedk,params=p.tolist(),train_rmse=float(np.sqrt(np.mean(rt[mT]**2))),val_rmse=float(np.sqrt(np.mean(rv[mV]**2))),train_deriv_rmse=float(np.sqrt(np.mean((accel-tr.dx1.values)**2))),val_deriv_rmse=float(np.sqrt(np.mean((av-va.dx1.values)**2))),evaluations=fit.nfev)
  print(json.dumps(r),flush=True);results.append(r);json.dump(results,open('helper_rollout_results.json','w'),indent=2)
