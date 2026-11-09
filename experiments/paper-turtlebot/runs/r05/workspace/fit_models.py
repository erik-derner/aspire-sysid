"""Reproducible final identification. Only training data are accessed.
Run this script to reproduce final_fit_results.json; candidate JSON creation is in make_submission.py.
The training horizon is 25 transitions (5 s), initialized at every available logged pose.
"""
import numpy as np,json
from scipy.optimize import least_squares
import fit_explore as F
F.SPECS['directional']=dict(names=['gv','gw','ga'],init=[.83,.68,0],lo=[.1,.1,-.4],hi=[1.5,1.5,.4])
old_response=F.response
def response(p,u,fam):
 if fam=='directional':
  f,a=u[...,0],u[...,1]
  return p[0]*f,p[1]*a+p[2]*np.abs(a),0,0
 return old_response(p,u,fam)
F.response=response
CONFIG={'linear':'x','wheel':'xy','deadzone':'joint','body':'x','asymmetric':'x','directional':'x'}
# deterministic multi-start only for piecewise wheel model; piecewise objectives can have local minima.
WHEEL_STARTS=[[.83,.68,h,d] for h in [.08,.115,.18] for d in [.003,.012,.03]]
def fit_final(fam,ids,kind):
 spec=F.SPECS[fam]; pack=F.windows(ids,25,1)
 starts=WHEEL_STARTS if fam=='wheel' else [spec['init']]
 runs=[]
 for init in starts:
  r=least_squares(F.residual,init,bounds=(spec['lo'],spec['hi']),args=(pack,fam,kind),method='trf',max_nfev=600,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  runs.append(dict(parameters=r.x.tolist(),cost=float(r.cost),nfev=int(r.nfev),initial=init))
 best=min(runs,key=lambda q:q['cost'])
 return np.array(best['parameters']),runs
if __name__=='__main__':
 results={}
 for fam,kind in CONFIG.items():
  p,runs=fit_final(fam,[0,1,2],kind); folds=[]
  for held in range(3):
   q,fr=fit_final(fam,[i for i in range(3) if i!=held],kind)
   folds.append(dict(parameters=q.tolist(),rmse=F.scores(q,[held],fam,25,1),rmse_phasezero=F.scores(q,[held],fam,25,5),long=F.longscores(q,[held],fam),runs=fr))
  rec=dict(parameters=p.tolist(),names=F.SPECS[fam]['names'],criterion=kind,runs=runs,train=F.scores(p,[0,1,2],fam,25,1),long=F.longscores(p,[0,1,2],fam),folds=folds,cv_x=float(np.sqrt(np.mean([f['rmse'][0]**2 for f in folds]))),cv_phasezero_x=float(np.sqrt(np.mean([f['rmse_phasezero'][0]**2 for f in folds]))))
  rec['rmse_by_horizon']={str(h):F.scores(p,[0,1,2],fam,h,1) for h in [5,10,25,50]}
  results[fam]=rec
  print(fam,kind,'parameters',np.round(p,6),'train',np.round(rec['train'],5),'long',np.round(rec['long'],4),'CVx',round(rec['cv_x'],6),'CVphase0',round(rec['cv_phasezero_x'],6),flush=True)
 json.dump(results,open('final_fit_results.json','w'),indent=2)
