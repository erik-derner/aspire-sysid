import numpy as np,json
from scipy.optimize import least_squares, minimize
import fit_extensions as X
F=X.F
# Deterministic multistart needed for wheel dead-zone thresholds: a nonsmooth objective.
STARTS=[[.83,.8,b,d] for b in [.06,.115,.2] for d in [.003,.015,.03]]
def fitwheel(gs):
 B=F.batches(gs,25,5);bounds=F.SPECS['wheels'][1]
 objective=lambda p:np.sum(F.residual('wheels',p,B)**2)
 best=None;attempts=[]
 for start in STARTS:
  opt=minimize(objective,start,method='Powell',bounds=list(zip(*bounds)),options={'xtol':1e-9,'ftol':1e-10,'maxiter':300})
  ls=least_squares(lambda p:F.residual('wheels',p,B),opt.x,bounds=bounds,ftol=1e-11,xtol=1e-11,gtol=1e-11,max_nfev=400)
  attempts.append({'initial':start,'powell_sse':float(opt.fun),'final_sse':float(2*ls.cost),'p':ls.x.tolist()})
  if best is None or ls.cost<best.cost:best=ls
 return best.x,attempts
if __name__=='__main__':
 p,attempts=fitwheel(F.traj);cv=[];cvps=[];foldattempts=[]
 for i in range(3):
  pc,att=fitwheel([g for j,g in enumerate(F.traj) if i!=j]);cv.append(F.metrics('wheels',pc,[F.traj[i]]));cvps.append(pc.tolist());foldattempts.append(att)
 R={'parameters':p.tolist(),'train':F.metrics('wheels',p,F.traj),'full_x':F.full_metrics('wheels',p,F.traj),'validation':cv,'validation_parameters':cvps,'cv_x':float(np.sqrt(np.mean([a['x']**2 for a in cv]))),'attempts':attempts,'fold_attempts':foldattempts}
 open('wheel_results.json','w').write(json.dumps(R,indent=2))
 print(json.dumps({k:v for k,v in R.items() if k not in ['attempts','fold_attempts']},indent=2))
