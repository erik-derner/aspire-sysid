import json,numpy as np
from scipy.optimize import least_squares
from numba import njit
from fit_models import train,val
@njit(cache=True)
def acc(t,w,u,p,kind):
 a,b,c,f,k,r,h,j=p[:8]
 friction=f*(1+h*np.cos(t));bias=f*(1-abs(h))*r*np.cos(t)
 F=a*u-b*w-c*np.sin(t)*(1+j*np.cos(t))+bias
 if kind==0:return F-min(max(F+k*w,-friction),friction)
 alpha=np.exp(-(w/p[8])**2)
 return F-alpha*min(max(F,-friction),friction)-(1-alpha)*friction*np.tanh(w/p[9])-k*w*alpha
@njit(cache=True)
def sim(g,p,kind):
 out=np.empty(len(g));t,w=g[0,:2];out[0]=t
 for i in range(len(g)-1):
  u=g[i,2];a1=acc(t,w,u,p,kind);w1=w
  w2=w+.005*a1;a2=acc(t+.005*w1,w2,u,p,kind)
  w3=w+.005*a2;a3=acc(t+.005*w2,w3,u,p,kind)
  w4=w+.01*a3;a4=acc(t+.01*w3,w4,u,p,kind)
  t+=.01/6*(w1+2*w2+2*w3+w4);w+=.01/6*(a1+2*a2+2*a3+a4);out[i+1]=t
 return out

def res(p,kind,data):return np.concatenate([sim(g,p,kind)[1:]-g[1:,0] for g in data])
def score(p,kind,data):return float(np.sqrt(np.mean(res(p,kind,data)**2)))
if __name__=='__main__':
 results={}
 for split,data in [('train',train),('all',train+val)]:
  for kind in [0,1]:
   p=[28.8,1.55,114.5,29.2,180,.16,-.3,0];lo=[1,0,1,1,10,-.8,-.8,-.8];hi=[100,20,300,80,220,.8,.8,.8]
   if kind==1:p[4]=25;p+=[.3,.5];lo+=[.15,.08];hi+=[3,1.5]
   fit=least_squares(res,p,args=(kind,data),bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-8)
   result={'p':fit.x.tolist(),'start':p,'lower':lo,'upper':hi,'train_rmse':score(fit.x,kind,train),'val_rmse':score(fit.x,kind,val),'nfev':fit.nfev}
   results[split+str(kind)]=result;print(split,kind,result,flush=True);json.dump(results,open('results/combined.json','w'),indent=2)
