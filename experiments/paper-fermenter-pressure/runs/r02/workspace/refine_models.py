import numpy as np,json,pandas as pd,time
from pathlib import Path
from numba import njit
from scipy.optimize import least_squares
from fit_models import D,step,rollout,transitions
# stable regularized Bernoulli or nozzle parametrization with two normalized monotone valve basis weights.
# Parameters: a, cap (max pressure restoring slope), eps, w (basis1 fraction), p0;
# resistance uses a, gtotal, R, w, p0. Linear uses a, gtotal, w, p0.
@njit
def expand(x,fam):
 t=np.zeros(7);t[0]=x[0]
 if fam==0:
  B=x[1];w=x[2];t[4]=x[3]
 else:
  B=x[1];w=x[3];t[4]=x[4];t[5]=x[2]
  if fam==1:B=x[1]*np.sqrt(x[2])
  if fam==3:B=x[1]*np.sqrt(x[2]*x[4]/2)
 t[1]=B*w;t[2]=B*(1-w)
 return t

def fit(label,fam,sets,initial,bounds,criterion='simulation'):
 lo,hi=map(np.array,bounds)
 def residual(x,transition):
  t=expand(x,fam)
  return np.concatenate([transitions(t,d,fam,0) if transition else rollout(t,d,fam,0)[1:]-d[1:,0] for d in sets])
 o1=least_squares(lambda x:residual(x,True),initial,bounds=(lo,hi),x_scale='jac',max_nfev=1000,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 o2=least_squares(lambda x:residual(x,False),o1.x,bounds=(lo,hi),x_scale='jac',max_nfev=1500,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 t=expand(o2.x,fam);r={'label':label,'family':fam,'initial':initial,'bounds':bounds,'transition_x':o1.x.tolist(),'final_x':o2.x.tolist(),'parameters':t.tolist(),'nfev':[o1.nfev,o2.nfev],'metrics':{}}
 for name,d in D.items():
  e=rollout(t,d,fam,0)[1:]-d[1:,0];tr=transitions(t,d,fam,0)
  r['metrics'][name]={'rmse':float(np.sqrt(np.mean(e**2))),'bias':float(e.mean()),'transition_rmse':float(np.sqrt(np.mean(tr**2))),'corr_flow_change':float(np.corrcoef(tr,np.diff(d[:,2]))[0,1])}
 print(label,criterion,o2.x,r['metrics'],flush=True)
 return r
if __name__=='__main__':
 configs=[('viscous',0,[.001,.22,.05,1.],[[.0001,.0001,0.,.985],[.005,.5,1.,1.01]]),('bernoulli',1,[.0014,.4,.12,.5,1.],[[.0001,.03,.01,0.,.985],[.005,.5,.5,1.,1.01]]),('choked',3,[.0014,.4,.12,.5,1.],[[.0001,.03,.01,0.,.985],[.005,.5,.5,1.,1.01]]),('mixed',4,[.0013,.15,3.,.4,1.],[[.0001,.0001,2.,0.,.985],[.005,.4,30.,1.,1.01]])]
 outputs={}
 for stage in ['train','blocked','pooled']:
  outputs[stage]=[]
  if stage=='train':sets=[D['train']]
  elif stage=='blocked':sets=[d[:int(len(d)*2/3)] for d in D.values()]
  else:sets=list(D.values())
  for label,fam,initial,bounds in configs:
   r=fit(label,fam,sets,initial,bounds,stage)
   if stage=='blocked':
    r['heldout_tail']={}
    for name,d in D.items():
     tail=d[int(len(d)*2/3):];e=rollout(np.array(r['parameters']),tail,fam,0)[1:]-tail[1:,0]
     r['heldout_tail'][name]=float(np.sqrt(np.mean(e**2)))
    print('heldout tail',r['heldout_tail'],flush=True)
   outputs[stage].append(r)
  Path('refined_results.json').write_text(json.dumps(outputs,indent=2))
