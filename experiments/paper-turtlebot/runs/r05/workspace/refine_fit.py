import fit_explore as F
import numpy as np,json
from scipy.optimize import least_squares
# Additional structures motivated by command-change residuals: calibrated quadrature phase and nonlinear wheel response.
F.SPECS.update({
 'phase':dict(names=['gv','gw','tau'],init=[.83,.68,0],lo=[.1,.1,-.5],hi=[1.5,1.5,.5]),
 'coupled':dict(names=['gv','gw','cwforward'],init=[.83,.68,0],lo=[.1,.1,-2],hi=[1.5,1.5,2]),
 'slip':dict(names=['gv','gw','slip'],init=[.83,.68,0],lo=[.1,.1,-.8],hi=[1.5,1.5,3]),
 'drift':dict(names=['gv','gw','bw'],init=[.83,.68,0],lo=[.1,.1,-.3],hi=[1.5,1.5,.3])})
orig=F.response
def response(p,u,fam):
 f,a=u[...,0],u[...,1]
 if fam=='phase': return p[0]*f,p[1]*a,-p[2]*p[1]*a,0
 if fam=='coupled': return p[0]*f,(p[1]+p[2]*f)*a,0,0
 if fam=='slip': return p[0]*f/(1+p[2]*a*a),p[1]*a,0,0
 if fam=='drift': return p[0]*f,p[1]*a+p[2],0,0
 return orig(p,u,fam)
F.response=response
# Original simulate must permit time-dependent phase rather than constant beta.
def simulate(p,pack,fam):
 state=pack[0].copy(); u=pack[1]; out=[]; v,w,b,lat=response(p,u,fam)
 for k in range(u.shape[1]):
  bk=b[:,k] if isinstance(b,np.ndarray) else b
  lk=lat[:,k] if isinstance(lat,np.ndarray) else lat
  angle=state[:,2]+F.TS*w[:,k]/2+bk
  state[:,0]+=F.TS*(v[:,k]*np.cos(angle)-lk*np.sin(angle))
  state[:,1]+=F.TS*(v[:,k]*np.sin(angle)+lk*np.cos(angle))
  state[:,2]+=F.TS*w[:,k]
  out.append(state.copy())
 return np.stack(out,axis=1)
F.simulate=simulate
if __name__=='__main__':
 results={}
 for fam in ['phase','coupled','slip','drift']:
  results[fam]={}
  for kind in ['joint','x']:
   p,info=F.fit(fam,[0,1,2],kind); folds=[]
   for held in range(3):
    q,_=F.fit(fam,[i for i in range(3) if i!=held],kind)
    folds.append(dict(parameters=q.tolist(),rmse=F.scores(q,[held],fam),long=F.longscores(q,[held],fam)))
   results[fam][kind]=dict(parameters=p.tolist(),info=info,train=F.scores(p,[0,1,2],fam),long=F.longscores(p,[0,1,2],fam),folds=folds,cv_x=float(np.sqrt(np.mean([f['rmse'][0]**2 for f in folds]))))
   print(fam,kind,'parameters',np.round(p,5),'train',np.round(results[fam][kind]['train'],5),'long',np.round(results[fam][kind]['long'],4),'CVx',round(results[fam][kind]['cv_x'],5),flush=True)
 json.dump(results,open('refine_results.json','w'),indent=2)
