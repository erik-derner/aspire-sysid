import numpy as np,json
from scipy.optimize import least_squares
from pathlib import Path
from fit_models import D,transitions,rollout
from refine_models import expand
cfg=[('bernoulli',1,[.0013,.35,.1,.5],[[.0001,.03,.01,0],[.005,.5,.5,1]]),('choked',3,[.0013,.35,.1,.5],[[.0001,.03,.01,0],[.005,.5,.5,1]]),('mixed',4,[.0013,.15,3.,.4],[[.0001,.0001,2.,0.],[.005,.4,30.,1.]])]
output={}
for stage in ['train','blocked','pooled']:
 sets=[D['train']] if stage=='train' else [d[:int(len(d)*2/3)] for d in D.values()] if stage=='blocked' else list(D.values());output[stage]=[]
 for label,fam,initial,bounds in cfg:
  def tt(x):return expand(np.r_[x,1.],fam)
  def residual(x,trans):return np.concatenate([transitions(tt(x),d,fam,0) if trans else rollout(tt(x),d,fam,0)[1:]-d[1:,0] for d in sets])
  o1=least_squares(lambda x:residual(x,True),initial,bounds=bounds,x_scale='jac',max_nfev=1000,ftol=1e-11,xtol=1e-11,gtol=1e-11)
  o2=least_squares(lambda x:residual(x,False),o1.x,bounds=bounds,x_scale='jac',max_nfev=1500,ftol=1e-11,xtol=1e-11,gtol=1e-11)
  t=tt(o2.x);r={'label':label,'family':fam,'initial':initial,'bounds':bounds,'transition_x':o1.x.tolist(),'final_x':o2.x.tolist(),'parameters':t.tolist(),'nfev':[o1.nfev,o2.nfev],'metrics':{}}
  for name,d in D.items():
   e=rollout(t,d,fam,0)[1:]-d[1:,0];tr=transitions(t,d,fam,0);r['metrics'][name]={'rmse':float(np.sqrt(np.mean(e*e))),'bias':float(e.mean()),'transition_rmse':float(np.sqrt(np.mean(tr*tr))),'corr_flow_change':float(np.corrcoef(tr,np.diff(d[:,2]))[0,1])}
  if stage=='blocked':
   r['heldout_tail']={}
   for name,d in D.items():
    d=d[int(len(d)*2/3):];e=rollout(t,d,fam,0)[1:]-d[1:,0];r['heldout_tail'][name]=float(np.sqrt(np.mean(e*e)))
  print(stage,label,o2.x,r['metrics'],r.get('heldout_tail'),flush=True);output[stage].append(r)
 Path('fixed_results.json').write_text(json.dumps(output,indent=2))
