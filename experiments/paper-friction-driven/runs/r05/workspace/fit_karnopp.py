import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
from fit_models import train,val
@njit(cache=True)
def acc(t,w,u,p):
 a,b,c,f,v,k,r,h=p
 F=a*u-b*w-c*np.sin(t)*(1+h*np.cos(t))+f*r
 if abs(w)>v:return F-f*np.sign(w)
 return max(F-f,0)+min(F+f,0)-k*w
@njit(cache=True)
def sim(g,p):
 out=np.empty(len(g));t,w=g[0,:2];out[0]=t
 for i in range(len(g)-1):
  u=g[i,2];a1=acc(t,w,u,p);w1=w
  w2=w+.005*a1;a2=acc(t+.005*w1,w2,u,p)
  w3=w+.005*a2;a3=acc(t+.005*w2,w3,u,p)
  w4=w+.01*a3;a4=acc(t+.01*w3,w4,u,p)
  t+=.01/6*(w1+2*w2+2*w3+w4);w+=.01/6*(a1+2*a2+2*a3+a4);out[i+1]=t
 return out

def res(p,data):return np.concatenate([sim(g,p)[1:]-g[1:,0] for g in data])
def score(p,data):return float(np.sqrt(np.mean(res(p,data)**2)))
if __name__=='__main__':
 results=[]
 for v in [.16,.24,.32,.4,.6,.8]:
  # band held fixed per fit: discontinuous band edge does not admit useful infinitesimal finite differences
  p0=[28.3,1.8,108.5,21,v,25,.075,.10];lo=[1,0,1,1,v-1e-10,1,-.8,-.8];hi=[100,20,300,80,v+1e-10,180,.8,.8]
  fit=least_squares(res,p0,args=(train,),bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=300,ftol=1e-8,xtol=1e-8,gtol=1e-8)
  r={'p':fit.x.tolist(),'start':p0,'lower':lo,'upper':hi,'train_rmse':score(fit.x,train),'val_rmse':score(fit.x,val),'nfev':fit.nfev};results.append(r);print('grid',r,flush=True)
 best=min(results,key=lambda r:r['val_rmse']);p0=best['p'];lo=best['lower'];hi=best['upper']
 fit=least_squares(res,p0,args=(train+val,),bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=300,ftol=1e-8,xtol=1e-8,gtol=1e-8)
 result={'grid':results,'selected_start':p0,'final':fit.x.tolist(),'train_rmse':score(fit.x,train),'val_rmse':score(fit.x,val),'nfev':fit.nfev}
 json.dump(result,open('results/karnopp.json','w'),indent=2);print('final',result,flush=True)
