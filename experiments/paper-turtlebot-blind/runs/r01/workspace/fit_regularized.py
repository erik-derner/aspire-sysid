import json,numpy as np
from scipy.optimize import least_squares
from fit_kinematic import trajs,simulate,angular,wrap,residual,bounds

def local_res(p,arrays,fam):
 r=[]
 for a in arrays:
  sel=np.arange(len(a)-1)%5>=2
  dt=wrap(a[1:,2]-a[:-1,2]);s=(a[1:,0]-a[:-1,0])*np.cos(a[:-1,2]+dt/2)+(a[1:,1]-a[:-1,1])*np.sin(a[:-1,2]+dt/2)
  r.extend(np.column_stack([p[0]+p[1]*a[:-1,3]-s,.25*(angular(p,a[:-1,4],fam)-dt)])[sel].ravel())
 return np.array(r)
def fit(arrays,fam,mult):
 base=[0,.1667,0,.14]
 if fam=='deadzone_mid':base+=[.09];base[3]=.1667
 elif fam=='power_mid':base+=[1.24];base[3]=.16
 elif fam=='cubic_mid':base+=[.03];base[3]=.12
 def obj(p):
  loc=local_res(p,arrays,fam)
  if mult=='local':return loc
  return np.r_[residual(p,arrays,fam),float(mult)*loc]
 opt=least_squares(obj,base,bounds=bounds(fam),max_nfev=3000,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return opt.x,base
if __name__=='__main__':
 results={}
 for fam in ['linear_mid','deadzone_mid','cubic_mid','power_mid']:
  for mult in [5,20,100,'local']:
   p,start=fit(trajs,fam,mult);e=np.concatenate([simulate(p,a,fam)[1:]-a[1:,:3] for a in trajs]);e[:,2]=wrap(e[:,2]);train=np.sqrt(np.mean(e**2,axis=0)).tolist();loo=[];loo_p=[]
   for i in range(3):
    q,_=fit([a for j,a in enumerate(trajs) if j!=i],fam,mult);e=simulate(q,trajs[i],fam)[1:]-trajs[i][1:,:3];e[:,2]=wrap(e[:,2]);loo.append(np.sqrt(np.mean(e**2,axis=0)).tolist());loo_p.append(q.tolist())
   key=fam+'_'+str(mult);print(key,'params',p,'train',train,'loo',np.array(loo)[:,0],'aggregate',np.sqrt(np.mean(np.array(loo)[:,0]**2)))
   results[key]={'parameters':p.tolist(),'starting':start,'mult':mult,'family':fam,'train_rmse':train,'loo_rmse':loo,'loo_parameters':loo_p}
 with open('regularized_results.json','w') as f:json.dump(results,f,indent=2)
