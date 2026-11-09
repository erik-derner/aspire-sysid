import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
from pathlib import Path
D=pd.read_csv('data/train.csv'); TRAJS=[d[['y','x1','x2','x3','x4']].values for g,d in D.groupby('trajectory')]
# Parameter vectors; displacement and angular increment are per sample.
CONFIG={
'linear':([.16,0,.14,0],([.05,-.01,.04,-.02],[.30,.01,.25,.02])),
'deadzone':([.16,0,.16,.07,0],([.05,-.01,.04,0,-.02],[.30,.01,.30,.3,.02])),
'rational':([.16,0,.16,.007,.07,0],([.05,-.01,.04,.00001,0,-.02],[.30,.01,.40,.1,.3,.02])),
'smooth':([.16,0,.16,.012,.08,0],([.05,-.01,.04,0,.005,-.02],[.30,.01,.35,.08,.5,.02])),
'cubic':([.16,0,.13,.03,0,0],([.05,-.01,.02,-.2,-.5,-.02],[.30,.01,.35,.2,.5,.02])),
'wheels':([.16,.16,.1,.01,.01],([.05,.05,.02,0,0],[.30,.30,.5,.08,.08])),
'wheelsoft':([.16,.16,.1,.01,.05],([.05,.05,.02,0,.005],[.30,.30,.5,.08,.20]))}
def maps(p,v,u,f):
 if f in ['wheels','wheelsoft']:
  ar,al,l,dr,dl=p; r=v+l*u;left=v-l*u
  if f=='wheels': R=ar*np.sign(r)*np.maximum(abs(r)-dr,0);L=al*np.sign(left)*np.maximum(abs(left)-dl,0)
  else: R=ar*(r-dr*np.tanh(r/dl));L=al*(left-dr*np.tanh(left/dl))
  return (R+L)/2,(R-L)/(2*l)
 a,b=p[:2];s=a*v+b
 if f=='linear': w=p[2]*u+p[3]
 elif f=='deadzone':w=p[2]*np.sign(u)*np.maximum(abs(u)-p[3],0)+p[4]
 elif f=='rational':w=p[2]*v/(v+p[3])*np.sign(u)*np.maximum(abs(u)-p[4],0)+p[5]
 elif f=='smooth':w=p[2]*u-p[3]*np.tanh(u/p[4])+p[5]
 elif f=='cubic':w=p[2]*u+p[3]*u**3+p[4]*v*u+p[5]
 return s,w
def sim(p,a,f):
 s,w=maps(p,a[:-1,3],a[:-1,4],f);theta=a[0,2]+np.r_[0,np.cumsum(w)]
 mid=theta[:-1]+w/2
 xy=a[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.column_stack([s*np.cos(mid),s*np.sin(mid)]),axis=0)])
 return np.column_stack([xy,theta])
def residual(p,arrays,f,angweight=.25):
 es=[]
 for a in arrays:
  z=sim(p,a,f);e=z[1:]-a[1:,:3];e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2]))*angweight;es.extend(e.ravel())
 return np.array(es)
def fit(f,arrays):
 p,b=CONFIG[f]; return least_squares(residual,p,args=(arrays,f),bounds=b,max_nfev=1000,ftol=1e-10,xtol=1e-10,gtol=1e-10).x
def score(p,arrays,f):
 E=np.vstack([sim(p,a,f)[1:,:2]-a[1:,:2] for a in arrays]);return np.sqrt(np.mean(E**2,axis=0)).tolist()
if __name__=='__main__':
 results={}
 for f in CONFIG:
  t=time.time();p=fit(f,TRAJS);cv=[];cpars=[]
  for j in range(3):
   q=fit(f,[a for k,a in enumerate(TRAJS) if k!=j]);cv.append(score(q,[TRAJS[j]],f));cpars.append(q.tolist())
  q=fit(f,[a[:100] for a in TRAJS]);tail=score(q,[a[99:] for a in TRAJS],f)
  results[f]={'p':p.tolist(),'train':score(p,TRAJS,f),'cv':cv,'cv_rmse':np.sqrt(np.mean(np.array(cv)**2,axis=0)).tolist(),'cv_parameters':cpars,'tail':tail}
  print(f,json.dumps(results[f]),'time',time.time()-t,flush=True)
 Path('fit_results.json').write_text(json.dumps(results,indent=2))
