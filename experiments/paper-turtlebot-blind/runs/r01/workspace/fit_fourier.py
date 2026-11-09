import json,numpy as np
from scipy.optimize import least_squares
from fit_kinematic import trajs,wrap

def features(theta,u,w):
 return np.column_stack([np.ones(len(u)),u*np.cos(theta),u*np.sin(theta),np.cos(theta),np.sin(theta),u*w*np.cos(theta),u*w*np.sin(theta)])
def ang(q,w):return q[0]+q[1]*np.sign(w)*np.maximum(abs(w)-q[2],0)
def sim(p,a):
 h=ang(p[-3:],a[:-1,4]);theta=a[0,2]+np.r_[0,np.cumsum(h)]
 inc=features(theta[:-1],a[:-1,3],a[:-1,4])@p[:-3].reshape(7,2)
 return np.column_stack([a[0,:2]+np.vstack([np.zeros((1,2)),np.cumsum(inc,axis=0)]),wrap(theta)])
def fit(arrays,mult):
 F=np.vstack([features(a[:-1,2],a[:-1,3],a[:-1,4]) for a in arrays]);Y=np.vstack([a[1:,:2]-a[:-1,:2] for a in arrays]);c=np.linalg.lstsq(F,Y,rcond=None)[0];start=np.r_[c.ravel(),0,.1667,.09]
 def objective(p):
  r=[];loc=[]
  for a in arrays:
   d=sim(p,a)[1:]-a[1:,:3];d[:,2]=.25*wrap(d[:,2]);r.extend(d.ravel())
   sel=np.arange(len(a)-1)%5>=2
   f=features(a[:-1,2],a[:-1,3],a[:-1,4]);dp=f@p[:-3].reshape(7,2)-(a[1:,:2]-a[:-1,:2]);dt=.25*(ang(p[-3:],a[:-1,4])-wrap(a[1:,2]-a[:-1,2]));loc.extend(np.column_stack([dp,dt])[sel].ravel())
  return np.r_[r,mult*np.array(loc)]
 opt=least_squares(objective,start,bounds=(np.r_[np.repeat(-.5,14),-.05,0,0],np.r_[np.repeat(.5,14),.05,.5,.3]),max_nfev=3000,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return opt.x,start
if __name__=='__main__':
 results={}
 for mult in [20,100,300]:
  p,start=fit(trajs,mult);e=np.concatenate([sim(p,a)[1:]-a[1:,:3] for a in trajs]);e[:,2]=wrap(e[:,2]);train=np.sqrt(np.mean(e**2,axis=0)).tolist();loo=[]
  for i in range(3):
   q,_=fit([a for j,a in enumerate(trajs) if i!=j],mult);e=sim(q,trajs[i])[1:]-trajs[i][1:,:3];e[:,2]=wrap(e[:,2]);loo.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  print(mult,'params',p,'train',train,'loo',np.array(loo)[:,0],'aggregate',np.sqrt(np.mean(np.array(loo)[:,0]**2)))
  results[str(mult)]={'parameters':p.tolist(),'starting':start.tolist(),'mult':mult,'train_rmse':train,'loo_rmse':loo}
 with open('fourier_results.json','w') as f:json.dump(results,f,indent=2)
