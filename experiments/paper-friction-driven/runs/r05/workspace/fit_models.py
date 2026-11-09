import numpy as np,pandas as pd,json,os
from scipy.optimize import least_squares
from numba import njit

@njit(cache=True)
def acceleration(t,w,u,p,kind):
 a,b,c,f=p[:4]
 restoring=c*np.sin(t)
 if kind==6: restoring=c*t
 if kind==5: restoring=c*np.sin(t)*(1+p[5]*np.cos(t))
 force=a*u-b*w-restoring
 if kind==3: force-=p[5]*w*abs(w)
 if kind==7: force+=p[5]*u**3
 if kind==11: force=a*np.sign(u)*max(abs(u)-p[5],0)-b*w-restoring
 if kind==12: force-=p[5]*abs(w)
 if kind==0: return force-f*np.tanh(w/p[4])
 if kind==2:
  if abs(w)>p[4]: return force-f*np.sign(w)
  return max(force-f,0)+min(force+f,0)-p[5]*w
 if kind==4:
  lo=-f*(1-p[5]);hi=f*(1+p[5])
 else:
  if kind==9: f=f*(1+p[5]*np.cos(t))
  if kind==10: f=f+p[5]*np.exp(-(w/p[6])**2)
  lo=-f;hi=f
 return force-min(max(force+p[4]*w,lo),hi)

@njit(cache=True)
def simulate(g,p,kind):
 out=np.empty(g.shape[0]);t=g[0,0];w=g[0,1];out[0]=t
 for i in range(len(g)-1):
  u=g[i,2]
  a1=acceleration(t,w,u,p,kind);w1=w
  w2=w+.005*a1;a2=acceleration(t+.005*w1,w2,u,p,kind)
  w3=w+.005*a2;a3=acceleration(t+.005*w2,w3,u,p,kind)
  w4=w+.01*a3;a4=acceleration(t+.01*w3,w4,u,p,kind)
  t+=.01/6*(w1+2*w2+2*w3+w4);w+=.01/6*(a1+2*a2+2*a3+a4)
  if not np.isfinite(t) or abs(t)>1000 or abs(w)>1000:
   out[i+1:]=1000;break
  out[i+1]=t
 return out

def load(path):
 return [g[['theta','omega','u','domega']].to_numpy() for _,g in pd.read_csv(path).groupby('trajectory',sort=False)]
train=load('data/train.csv');val=load('data/val.csv')
def residual(p,kind,data):
 return np.concatenate([simulate(g,p,kind)[1:]-g[1:,0] for g in data])
def scores(p,kind,data):
 return [float(np.sqrt(np.mean((simulate(g,p,kind)[1:]-g[1:,0])**2))) for g in data]

def config(kind):
 base=[26.52770787,1.54606048,108.42444028,19.65668342];lo=[1,0,1,1];hi=[100,20,300,80]
 if kind==0: return base+[.3],lo+[.08],hi+[3]
 if kind==2: return base+[.4,90],lo+[.15,10],hi+[1.2,180]
 p=base+[100];lo+=[20];hi+=[220]
 if kind==3: p+=[.03];lo+=[0];hi+=[1]
 if kind in [4,5,9]: p+=[0];lo+=[-.8];hi+=[.8]
 if kind==7: p+=[.01];lo+=[0];hi+=[3]
 if kind==10: p+=[5,.5];lo+=[0,.1];hi+=[60,5]
 if kind==11: p+=[.05];lo+=[0];hi+=[1]
 if kind==12: p+=[0];lo+=[-1.5];hi+=[1.5]
 return p,lo,hi

if __name__=='__main__':
 os.makedirs('results',exist_ok=True);results={}
 for kind in range(13):
  if kind==8: continue
  p,lo,hi=config(kind)
  fit=least_squares(residual,p,args=(kind,train),bounds=(lo,hi),x_scale='jac',diff_step=1e-4,max_nfev=350,ftol=1e-9,xtol=1e-9,gtol=1e-8)
  tr=scores(fit.x,kind,train);va=scores(fit.x,kind,val)
  r={'p':fit.x.tolist(),'start':p,'lower':lo,'upper':hi,'nfev':fit.nfev,'train':tr,'val':va,'train_rmse':float(np.sqrt(np.mean(residual(fit.x,kind,train)**2))),'val_rmse':float(np.sqrt(np.mean(residual(fit.x,kind,val)**2)))}
  print(kind, r,flush=True);results[str(kind)]=r
  with open('results/fits.json','w') as f:json.dump(results,f,indent=2)
