import os,json,numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');trajs=[d[['y','x1','x2','x3','x4']].to_numpy() for _,d in D.groupby('trajectory',sort=False)]
def wrap(x):return np.arctan2(np.sin(x),np.cos(x))
def angular(p,w,fam):
 if fam in ['linear_euler','linear_mid']:return p[2]+p[3]*w
 if fam in ['cubic_mid','cubic_arc']:return p[2]+p[3]*w+p[4]*w**3
 if fam=='deadzone_mid':return p[2]+p[3]*np.sign(w)*np.maximum(np.abs(w)-p[4],0)
 if fam=='power_mid':return p[2]+p[3]*np.sign(w)*np.abs(w)**p[4]
def simulate(p,a,fam):
 u=a[:-1,3];w=a[:-1,4];h=angular(p,w,fam);theta=a[0,2]+np.r_[0,np.cumsum(h)];s=p[0]+p[1]*u
 phase=0 if fam=='linear_euler' else .5
 if fam=='cubic_arc':s=s*np.sinc(h/(2*np.pi))
 inc=np.column_stack([s*np.cos(theta[:-1]+phase*h),s*np.sin(theta[:-1]+phase*h)])
 xy=a[0,:2]+np.vstack([np.zeros((1,2)),np.cumsum(inc,axis=0)])
 return np.column_stack([xy,wrap(theta)])
def residual(p,arrays,fam):
 r=[]
 for a in arrays:
  d=simulate(p,a,fam)[1:]-a[1:,:3];d[:,2]=.25*wrap(d[:,2]);r.extend(d.ravel())
 return np.array(r)
def bounds(fam):
 if fam in ['linear_euler','linear_mid']:return ([-.02,0,-.05,0],[.02,.4,.05,.4])
 if fam=='deadzone_mid':return ([-.02,0,-.05,0,0],[.02,.4,.05,.5,.3])
 if fam=='power_mid':return ([-.02,0,-.05,0,.3],[.02,.4,.05,.5,3])
 return ([-.02,0,-.05,0,-.3],[.02,.4,.05,.4,.3])
def fit(arrays,fam):
 base=[0,.1667,0,.14]
 if fam=='deadzone_mid':base+=[.09];base[3]=.1667
 elif fam=='power_mid':base+=[1.24];base[3]=.16
 elif fam in ['cubic_mid','cubic_arc']:base+=[.03];base[3]=.12
 r=least_squares(residual,base,args=(arrays,fam),bounds=bounds(fam),max_nfev=3000,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 return r.x,base
if __name__=='__main__':
 results={}
 for fam in ['linear_euler','linear_mid','deadzone_mid','cubic_mid','power_mid','cubic_arc']:
  p,start=fit(trajs,fam);pred=[simulate(p,a,fam) for a in trajs]; err=np.concatenate([b[1:]-a[1:,:3] for a,b in zip(trajs,pred)]);err[:,2]=wrap(err[:,2]);print('\n',fam,p,'train',np.sqrt(np.mean(err**2,axis=0)))
  loo=[];loo_p=[]
  for i in range(3):
   q,_=fit([a for j,a in enumerate(trajs) if j!=i],fam);e=simulate(q,trajs[i],fam)[1:]-trajs[i][1:,:3];e[:,2]=wrap(e[:,2]);loo.append(np.sqrt(np.mean(e**2,axis=0)).tolist());loo_p.append(q.tolist())
  q,_=fit([a[:100] for a in trajs],fam);e=np.concatenate([(simulate(q,a,fam)-a[:,:3])[100:] for a in trajs]);e[:,2]=wrap(e[:,2]);tail=np.sqrt(np.mean(e**2,axis=0)).tolist()
  print('loo',np.array(loo),'loo pars',np.array(loo_p),'tail',tail)
  results[fam]={'parameters':p.tolist(),'starting':start,'train_rmse':np.sqrt(np.mean(err**2,axis=0)).tolist(),'loo_rmse':loo,'loo_parameters':loo_p,'tail_rmse':tail}
 with open('kinematic_results.json','w') as f:json.dump(results,f,indent=2)
