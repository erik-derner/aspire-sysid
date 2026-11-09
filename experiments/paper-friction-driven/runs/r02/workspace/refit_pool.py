import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
import fit_models as basic,fit_extended as extended,fit_stiction as stick,fit_projection as projection
import sys
SPECS={'StribeckStick':(stick,25,'stiction_results.json'),'StaticBlend':(basic,1,'fit_results.json'),'DirectionalDry':(basic,6,'fit_results.json'),'HarmonicTorque':(basic,5,'fit_results.json'),'SaturatedDrive':(extended,12,'extended_results.json'),'ProjectionStick':(projection,31,'projection_results.json'),'PeriodicContact':(stick,23,'stiction_results.json')}
def simulate(mod,p,f,rows,lens):return mod.simulate(p,f,rows,lens) if mod is basic else mod.sim(p,f,rows,lens)
def metric(mod,p,f,rows,lens):
 r=simulate(mod,p,f,rows,lens)-rows[:,0];o=0;ss=[]
 for l in lens:ss.append(float(np.sqrt(np.mean(r[o+1:o+l]**2))));o+=l
 return [float(np.sqrt(np.sum(r*r)/(len(r)-len(lens)))),ss]
def array(gs):return np.concatenate([g[['theta','omega','u']].to_numpy() for g in gs]),np.array([len(g) for g in gs],dtype=np.int64)
if __name__=='__main__':
 tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
 groups=[g for _,g in tr.groupby('trajectory')]+[g for _,g in va.groupby('trajectory')];rows,lens=array(groups)
 results=json.load(open('refit_results.json')) if len(sys.argv) else {}
 for label,(mod,f,path) in SPECS.items():
  if len(sys.argv) and label!=sys.argv[1]:continue
  old=json.load(open(path))[str(f)];lo,hi=np.array(old['bounds']);p=np.array(old['p']);starts=[p.tolist()]
  p2=p.copy();p2[4]=.25; p2[5]=max(p2[5],20) if mod is not stick else 2;p2=np.clip(p2,lo+1e-7,hi-1e-7);starts.append(p2.tolist())
  p3=p.copy();p3[4]=1.5;p3[5]=max(p3[5],20) if mod is not stick else 2;p3=np.clip(p3,lo+1e-7,hi-1e-7);starts.append(p3.tolist())
  if mod is projection:
   p2=p.copy();p2[4]=.02;starts[1]=p2.tolist()
   p3=p.copy();p3[4]=.05;starts[2]=p3.tolist()
  sols=[]
  for start in starts:
   fit=least_squares(lambda q:simulate(mod,q,f,rows,lens)-rows[:,0],start,bounds=(lo,hi),diff_step=1e-4,max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-9)
   sols.append({'p':fit.x.tolist(),'cost':fit.cost,'nfev':fit.nfev})
  best=min(sols,key=lambda x:x['cost']);p=best['p'];r={'p':p,'starts':starts,'solutions':sols,'bounds':[lo.tolist(),hi.tolist()],'pooled':metric(mod,p,f,rows,lens),'train':metric(mod,p,f,*array(groups[:13])),'val_refit':metric(mod,p,f,*array(groups[13:])),'family':f}
  print('REFIT',label,json.dumps(r),flush=True)
  # deterministic three-fold trajectory CV; starts use common pre-fit initial, not held-out fitted values
  cv=[]
  folds=[[0,3,5,8,11],[1,4,7,10,13],[2,6,9,12,14,15]]
  for ix in folds:
   rr,ll=array([g for j,g in enumerate(groups) if j not in ix]);test,tl=array([groups[j] for j in ix]);init=old['initial']
   fit=least_squares(lambda q:simulate(mod,q,f,rr,ll)-rr[:,0],init,bounds=(lo,hi),diff_step=1e-4,max_nfev=180,ftol=1e-8,xtol=1e-8,gtol=1e-8)
   cv.append({'holdout_indices':ix,'p':fit.x.tolist(),'score':metric(mod,fit.x,f,test,tl),'samples':len(test)-len(tl)})
  r['cv']=cv;r['cv_rmse']=float(np.sqrt(sum(x['score'][0]**2*x['samples'] for x in cv)/sum(x['samples'] for x in cv)))
  results[label]=r;json.dump(results,open('refit_results.json','w'),indent=2)
  print('CV',label,r['cv_rmse'],flush=True)
