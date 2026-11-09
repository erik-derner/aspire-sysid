import helper2 as h
import numpy as np,json
from scipy.optimize import least_squares
R=json.load(open('helper2_results.json'));out=[]
# Contiguous shooting blocks begin at every measured training state and use held inputs.
for kind,extra in [('log',['uu']),('sqrt',['uu']),('log',['uu','vv']),('sqrt',['uu','vv']),('exp',['uu','vv']),('atan',['uu','vv'])]:
 r=next(r for r in R if r['kind']==kind and r['terms']==['one','u','v','w','uw','vw','uv']+extra)
 terms=r['terms'];n=len(terms);p0=np.array(r['p']);y,u,v,dy=h.T.T;u=u/100;v=v/30
 for horizon in [3,10,30]:
  def res(p):
   yp=y[:-horizon].copy();es=[]
   for j in range(horizon):
    yp=h.step(p,kind,terms,yp,u[j:len(y)-horizon+j],v[j:len(y)-horizon+j]);es.append(yp-y[j+1:len(y)-horizon+j+1])
   return np.concatenate(es)/np.sqrt(horizon)
  opt=least_squares(res,p0,bounds=(np.r_[np.full(n,-100),r['bounds'][0]],np.r_[np.full(n,100),r['bounds'][1]]),x_scale='jac',max_nfev=200,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  rr={'kind':kind,'terms':terms,'horizon':horizon,'initial':p0.tolist(),'p':opt.x.tolist(),'cost':opt.cost,'nfev':opt.nfev,'train':h.metrics(opt.x,kind,terms,h.T),'val':h.metrics(opt.x,kind,terms,h.V)}
  out.append(rr);json.dump(out,open('helper2_multistep_results.json','w'),indent=2);print(json.dumps(rr),flush=True)
