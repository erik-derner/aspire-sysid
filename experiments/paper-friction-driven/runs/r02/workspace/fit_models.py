import numpy as np,pandas as pd,json,time,os
from scipy.optimize import least_squares
from numba import njit

def load(path):
 df=pd.read_csv(path);groups=[g for _,g in df.groupby('trajectory',sort=False)]
 return df,np.concatenate([g[['theta','omega','u']].to_numpy() for g in groups]),np.array([len(g) for g in groups],dtype=np.int64)
@njit
def accel(t,w,u,p,fam):
 a,g,b,c,v=p[:5]
 D=a*u-g*np.sin(t)
 if fam==4: D=a*u+p[6]*u**3-g*np.sin(t)
 if fam==5: D=a*u-g*np.sin(t)*(1+p[6]*np.cos(t))
 friction=c
 if fam==3: friction=c+p[6]*np.exp(-(w/p[7])**2)
 if fam==6: friction=c+p[6]*np.tanh(w/v)
 out=D-b*w-friction*np.tanh(w/v)
 if fam==7:out-=p[6]*w*abs(w)
 if fam!=0:
  fs=p[5]
  out-=np.exp(-(w/v)**2)*min(max(D,-fs),fs)
 return out
@njit
def simulate(p,fam,rows,lens):
 out=np.empty(len(rows));offset=0
 for L in lens:
  t,w=rows[offset,:2];out[offset]=t
  for i in range(offset,offset+L-1):
   u=rows[i,2]
   z1=accel(t,w,u,p,fam);v1=w
   z2=accel(t+.005*v1,w+.005*z1,u,p,fam);v2=w+.005*z1
   z3=accel(t+.005*v2,w+.005*z2,u,p,fam);v3=w+.005*z2
   z4=accel(t+.01*v3,w+.01*z3,u,p,fam);v4=w+.01*z3
   t+=.01/6*(v1+2*v2+2*v3+v4);w+=.01/6*(z1+2*z2+2*z3+z4)
   if not np.isfinite(t) or abs(t)>100 or abs(w)>500:
    out[i+1:]=1e3;return out
   out[i+1]=t
  offset+=L
 return out

def stats(p,fam,rows,lens):
 r=simulate(p,fam,rows,lens)-rows[:,0];o=0;s=[]
 for l in lens:s.append(float(np.sqrt(np.mean(r[o+1:o+l]**2))));o+=l
 return float(np.sqrt(np.mean(r*r))),s

if __name__=='__main__':
 tr,rows,lens=load('data/train.csv');va,vr,vl=load('data/val.csv')
 results={}
 initial=[26.52770787,108.42444028,1.54606048,19.65668342,.4]
 for fam in [0,1,3,4,5,6,7]:
  p=initial.copy();lo=[10,50,0,1,.15];hi=[50,180,8,45,2]
  if fam!=0:p+=[20];lo+=[1];hi+=[45]
  if fam==3:p+=[5,1];lo+=[0,.2];hi+=[30,5]
  if fam==4:p+=[.1];lo+=[0];hi+=[3]
  if fam==5:p+=[0];lo+=[-.6];hi+=[.6]
  if fam==6:p+=[0];lo+=[-8];hi+=[8]
  if fam==7:p+=[.02];lo+=[0];hi+=[.5]
  start=time.time()
  fit=least_squares(lambda p:simulate(p,fam,rows,lens)-rows[:,0],p,bounds=(lo,hi),diff_step=1e-4,max_nfev=220,ftol=1e-8,xtol=1e-8,gtol=1e-8)
  res={'p':fit.x.tolist(),'initial':p,'bounds':[lo,hi],'train':stats(fit.x,fam,rows,lens),'val':stats(fit.x,fam,vr,vl),'nfev':fit.nfev,'cost':fit.cost}
  results[str(fam)]=res;print('FAMILY',fam,json.dumps(res),'time',time.time()-start,flush=True)
  with open('fit_results.json','w') as f:json.dump(results,f,indent=2)
