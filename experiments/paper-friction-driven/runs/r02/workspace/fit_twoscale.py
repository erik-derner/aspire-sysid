import numpy as np,json,pandas as pd
from scipy.optimize import least_squares
from numba import njit
from fit_stiction import sim as sim_original
from refit_pool import array
@njit
def sim(p,f,rows,lens):
 q=np.array([p[0],p[1],p[2],p[3],p[4],0.,p[5]])
 return sim_original(q,25,rows,lens)
def metric(p,rows,lens):
 r=sim(p,26,rows,lens)-rows[:,0];off=0;s=[]
 for l in lens:s.append(float(np.sqrt(np.mean(r[off+1:off+l]**2))));off+=l
 return [float(np.sqrt(np.sum(r*r)/(len(r)-len(lens)))),s]
if __name__=='__main__':
 groups=[g for file in ['data/train.csv','data/val.csv'] for _,g in pd.read_csv(file).groupby('trajectory')];rows,lens=array(groups)
 starts=[[28,110,1.6,21,.4,.2],[28,110,1.6,21,.8,.3],[28,110,1.6,21,1.5,.2]];lo=[10,50,0,8,.15,.1];hi=[50,180,8,45,2,3];solutions=[]
 for start in starts:
  fit=least_squares(lambda p:sim(p,26,rows,lens)-rows[:,0],start,bounds=(lo,hi),diff_step=1e-4,max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  solutions.append({'p':fit.x.tolist(),'cost':fit.cost,'nfev':fit.nfev})
 best=min(solutions,key=lambda x:x['cost']);p=best['p'];r={'p':p,'starts':starts,'solutions':solutions,'bounds':[lo,hi],'pooled':metric(p,rows,lens),'train':metric(p,*array(groups[:13])),'val_refit':metric(p,*array(groups[13:])),'family':26}
 cv=[]
 for ix in [[0,3,5,8,11],[1,4,7,10,13],[2,6,9,12,14,15]]:
  rr,ll=array([g for j,g in enumerate(groups) if j not in ix]);test,tl=array([groups[j] for j in ix]);fit=least_squares(lambda p:sim(p,26,rr,ll)-rr[:,0],starts[0],bounds=(lo,hi),diff_step=1e-4,max_nfev=180,ftol=1e-8,xtol=1e-8,gtol=1e-8)
  cv.append({'holdout_indices':ix,'p':fit.x.tolist(),'score':metric(fit.x,test,tl),'samples':len(test)-len(tl)})
 r['cv']=cv;r['cv_rmse']=float(np.sqrt(sum(x['score'][0]**2*x['samples'] for x in cv)/sum(x['samples'] for x in cv)))
 results=json.load(open('refit_results.json'));results['TwoScaleStick']=r;json.dump(results,open('refit_results.json','w'),indent=2);print(json.dumps(r),flush=True)
