import numpy as np,json,os
from scipy.optimize import least_squares
from numba import njit
from fit_models import train,val

@njit(cache=True)
def acc(t,w,u,p,kind):
 a,b,c,f,k=p[:5];restoring=c*np.sin(t);bias=0.;friction=f
 if kind in [13,15,16,17,19,21]: bias=f*p[5]
 if kind in [14,18]: bias=f*p[5]*np.cos(t)
 if kind==15: bias=f*(p[5]+p[6]*np.cos(t))
 if kind in [16,21]: restoring*=1+p[6]*np.cos(t)
 if kind in [17,18]:
  friction=f*(1+p[6]*np.cos(t));bias*=1-abs(p[6])
 if kind==19: friction=f+p[6]*np.exp(-(w/p[7])**2)
 if kind==22:
  friction=f*(1+p[5]*np.cos(t));restoring*=1+p[6]*np.cos(t)
 force=a*u-b*w-restoring+bias
 if kind==21:
  # smooth velocity transition, exact force deadzone at zero velocity
  alpha=np.exp(-(w/p[7])**2)
  return force-alpha*min(max(force,-friction),friction)-(1-alpha)*friction*np.tanh(w/p[8])-k*w*alpha
 return force-min(max(force+k*w,-friction),friction)

@njit(cache=True)
def sim(g,p,kind):
 out=np.empty(len(g));t=g[0,0];w=g[0,1];out[0]=t
 for i in range(len(g)-1):
  u=g[i,2];a1=acc(t,w,u,p,kind);w1=w
  w2=w+.005*a1;a2=acc(t+.005*w1,w2,u,p,kind)
  w3=w+.005*a2;a3=acc(t+.005*w2,w3,u,p,kind)
  w4=w+.01*a3;a4=acc(t+.01*w3,w4,u,p,kind)
  t+=.01/6*(w1+2*w2+2*w3+w4);w+=.01/6*(a1+2*a2+2*a3+a4)
  if not np.isfinite(t) or abs(t)>1000 or abs(w)>1000:
   out[i+1:]=1000;break
  out[i+1]=t
 return out

def res(p,kind,data):return np.concatenate([sim(g,p,kind)[1:]-g[1:,0] for g in data])
def sc(p,kind,data):return [float(np.sqrt(np.mean((sim(g,p,kind)[1:]-g[1:,0])**2))) for g in data]
def cfg(kind):
 p=[28.4,1.95,111.5,19.2,120];lo=[1,0,1,1,20];hi=[100,20,300,80,220]
 if kind in [13,14,15,16,17,18,19,21]: p+=[.1];lo+=[-.45 if kind==15 else -.8];hi+=[.45 if kind==15 else .8]
 if kind==15: p+=[0];lo+=[-.45];hi+=[.45]
 if kind in [16,17,18,21,22]:p+=[.1];lo+=[-.8];hi+=[.8]
 if kind==19:p+=[5,.5];lo+=[0,.1];hi+=[60,5]
 if kind==21:
  p[4]=70;p+=[.6,.2];lo[4]=10;hi[4]=180;lo+=[.15,.08];hi+=[3,1.5]
 if kind==22:p+=[0];lo+=[-.8];hi+=[.8]
 return p,lo,hi

if __name__=='__main__':
 results={}
 for split,data in [('train',train),('all',train+val)]:
  for kind in [13,14,15,16,17,18,19,21,22]:
   p,lo,hi=cfg(kind)
   fit=least_squares(res,p,args=(kind,data),bounds=(lo,hi),x_scale='jac',diff_step=1e-4,max_nfev=400,ftol=1e-9,xtol=1e-9,gtol=1e-8)
   r={'p':fit.x.tolist(),'start':p,'lower':lo,'upper':hi,'nfev':fit.nfev,'train':sc(fit.x,kind,train),'val':sc(fit.x,kind,val),'train_rmse':float(np.sqrt(np.mean(res(fit.x,kind,train)**2))),'val_rmse':float(np.sqrt(np.mean(res(fit.x,kind,val)**2)))}
   print(split,kind,r,flush=True);results[split+str(kind)]=r
   json.dump(results,open('results/extended.json','w'),indent=2)
