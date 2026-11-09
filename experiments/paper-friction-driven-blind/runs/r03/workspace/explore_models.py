import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
from helper_rollout_core import T,V,nt,nv,mT,mV
@njit
def accel(y,v,u,p,mode):
 # a,b,c,d,e,w,h,j,s
 a,b,c,d,e,w,h,j,s=p
 if mode==0: rest=a*y+h*y**3+j*y**5
 elif mode==1: rest=a*y/(1+h*y*y)+j*y*y/(1+h*y*y)
 elif mode==2: rest=a*np.sin(y)+h*np.cos(y)
 elif mode==3: rest=a*np.sin(y)+h*np.cos(y)+j*np.sin(2*y)
 elif mode==4: rest=a*np.sin(y)+h*np.cos(y)
 elif mode==5: rest=a*y
 elif mode==6: rest=a*np.sin(y)+h*np.cos(y)
 else: rest=a*np.sin(y)+h*np.cos(y)
 friction=e*np.tanh(v/w)
 if mode==2: friction=(e+j*np.exp(-(v/s)**2))*np.tanh(v/w)
 if mode==4: friction=e*np.tanh((v-j*u)/w)
 if mode==6: friction=e*np.tanh(v/w)*(1+j*np.cos(y))
 if mode==7: friction=e*np.tanh(v/w)*(1+j*np.abs(u))
 return rest+b*v+c*u+d+friction
@njit
def rollout(p,A,ns,mode):
 out=np.empty(A.shape[0]);start=0
 for n in ns:
  y=A[start,0];v=A[start,1];out[start]=y
  for z in range(start,start+n-1):
   u=A[z,2];a=accel(y,v,u,p,mode);b=accel(y+.005*v,v+.005*a,u,p,mode);c=accel(y+.005*(v+.005*a),v+.005*b,u,p,mode);d=accel(y+.01*(v+.005*b),v+.01*c,u,p,mode)
   y+=.01/6*(v+2*(v+.005*a)+2*(v+.005*b)+(v+.01*c));v+=.01/6*(a+2*b+2*c+d)
   if abs(y)>1000 or abs(v)>1000: y=1000.;v=1000.
   out[z+1]=y
  start+=n
 return out
results=[]
for mode in range(8):
 p0=np.array([-109.8,-1.652,27.895,-.66,-20.667,.1,4.125,0.,2.])
 ids=list(range(6))+[6,7]
 lo=np.array([-180,-10,5,-15,-50,.09,-20,-40,.15]);hi=np.array([-50,0,50,15,0,3,30,40,15.])
 if mode==0: p0[0]=-110;p0[6]=17.;p0[7]=-.8;lo[6]=0;hi[6]=40;lo[7]=-10;hi[7]=0
 if mode==1: p0[0]=-115;p0[6]=.24;p0[7]=1;lo[6]=0;hi[6]=2;lo[7]=-20;hi[7]=20
 if mode==2: p0[7]=0;ids+=[8];lo[7]=-40;hi[7]=30
 if mode==3: p0[7]=0;lo[7]=-20;hi[7]=20
 if mode==4: p0[7]=0;lo[7]=-2;hi[7]=2
 if mode==5: p0[0]=-75;ids=list(range(6))
 if mode in [6,7]:lo[7]=-.8;hi[7]=.8
 ids=np.array(ids)
 def unpack(q):
  p=p0.copy();p[ids]=q;return p
 def fun(q):return (rollout(unpack(q),T,nt,mode)-T[:,0])[mT]
 fit=least_squares(fun,p0[ids],bounds=(lo[ids],hi[ids]),max_nfev=240,diff_step=1e-4,ftol=2e-8,xtol=2e-8,gtol=2e-8)
 p=unpack(fit.x);rt=rollout(p,T,nt,mode)-T[:,0];rv=rollout(p,V,nv,mode)-V[:,0]
 r=dict(mode=mode,params=p.tolist(),start=p0.tolist(),ids=ids.tolist(),lower=lo.tolist(),upper=hi.tolist(),train_rmse=float(np.sqrt(np.mean(rt[mT]**2))),val_rmse=float(np.sqrt(np.mean(rv[mV]**2))),evaluations=fit.nfev)
 print(json.dumps(r),flush=True);results.append(r);json.dump(results,open('explore_results.json','w'),indent=2)
