import numpy as np,json,time
from fit_models import simulate,pack,specs
from crossvalidate import combined,fit

NAMES=['angle_asym','angle_smooth','equal_blend','speed_weakening']
SEED=271828

def run():
 d=combined();dat=pack(d);old=json.load(open('cv_results.json'));rng=np.random.default_rng(SEED);out={}
 for name in NAMES:
  fam,start,lb,ub=specs[name];start=old[name]['p'] if name in old else start
  trials=[]
  for loss in ['linear','soft_l1']:
   best=None;starts=[np.array(start)]
   for z in range(5):
    p=np.array(start);p[:4]*=np.exp(rng.normal(0,.07,4))
    if name in ['angle_asym','equal_blend']:p[4]=rng.uniform(10,200)
    if 'angle' in name or name=='equal_blend':p[5:7]+=rng.normal(0,.07,2)
    p=np.clip(p,np.array(lb)+1e-8,np.array(ub)-1e-8);starts.append(p)
   for s in starts:
    f=fit(dat,name,s,loss=loss,max_nfev=350)
    if best is None or f.cost<best.cost:best=f
   p=best.x;pr=simulate(p,fam,*dat[:3]);by=[float(np.sqrt(np.mean((pr[j,1:n]-dat[3][j,1:n])**2))) for j,n in enumerate(dat[2])];cv=[];pars=[]
   for key in range(1,17):
    tr=pack(d[d.trajectory!=key]);v=pack(d[d.trajectory==key]);f=fit(tr,name,p,loss=loss,max_nfev=180);vp=simulate(f.x,fam,*v[:3]);cv.append(float(np.sqrt(np.mean((vp-v[3])[v[4]]**2))));pars.append(f.x.tolist())
   cvrmse=float(np.sqrt(np.average(np.array(cv)**2,weights=dat[2]-1)))
   rec={'family':fam,'p':p.tolist(),'start':list(start),'starts':[x.tolist() for x in starts],'loss':loss,'bounds':[lb,ub],'all_rmse':float(np.sqrt(np.mean((pr-dat[3])[dat[4]]**2))),'by':by,'cv':cv,'cv_rmse':cvrmse,'cv_parameters':pars}
   trials.append(rec);print(name,loss,'p',np.round(p,7),'fit',rec['all_rmse'],'cv',cvrmse,'by',np.round(cv,4),flush=True)
  out[name]={'selected':min(trials,key=lambda x:x['cv_rmse']),'trials':trials}
  json.dump(out,open('final_results.json','w'),indent=2)
if __name__=='__main__':run()
