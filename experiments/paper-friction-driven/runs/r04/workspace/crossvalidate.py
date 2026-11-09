import numpy as np,pandas as pd,json,time
from fit_models import simulate,pack,specs
from scipy.optimize import least_squares

def combined():
 t=pd.read_csv('data/train.csv');v=pd.read_csv('data/val.csv');v.trajectory+=13;return pd.concat([t,v],ignore_index=True)

def fit(dat,name,start,loss='linear',max_nfev=180):
 fam,_,lb,ub=specs[name]
 def res(p):return (simulate(p,fam,*dat[:3])-dat[3])[dat[4]]
 opt=least_squares(res,start,bounds=(lb,ub),x_scale='jac',diff_step=1e-4,max_nfev=max_nfev,ftol=2e-8,xtol=2e-8,gtol=1e-7,loss=loss,f_scale=.04)
 return opt

if __name__=='__main__':
 d=combined();r=json.load(open('fit_results.json'));out={};dat=pack(d)
 for name in ['smooth','projection','stribeck','blend','angle_friction','angle_smooth','angle_asym','angle_blend','angle_harmonic']:
  tm=time.time();fam=specs[name][0];start=r[name]['p'];opt=fit(dat,name,start);p=opt.x;pr=simulate(p,fam,*dat[:3]);by=[float(np.sqrt(np.mean((pr[j,1:n]-dat[3][j,1:n])**2))) for j,n in enumerate(dat[2])];cv=[];pars=[]
  for key in range(1,17):
   tr=pack(d[d.trajectory!=key]);v=pack(d[d.trajectory==key]);f=fit(tr,name,p,max_nfev=100);vp=simulate(f.x,fam,*v[:3]);cv.append(float(np.sqrt(np.mean((vp-v[3])[v[4]]**2))));pars.append(f.x.tolist())
  cvrmse=float(np.sqrt(np.average(np.array(cv)**2,weights=dat[2]-1)))
  out[name]={'family':fam,'p':p.tolist(),'start':start,'all_rmse':float(np.sqrt(np.mean((pr-dat[3])[dat[4]]**2))),'by':by,'cv':cv,'cv_rmse':cvrmse,'cv_parameters':pars}
  print(name,'p',p,'fit',out[name]['all_rmse'],'cv',cvrmse,'cvby',np.round(cv,4),'sec',time.time()-tm,flush=True)
  json.dump(out,open('cv_results.json','w'),indent=2)
