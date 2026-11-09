import numpy as np,json
from scipy.optimize import least_squares
import advanced as A
RATE_CAP=.5

def fit(files,initial):
 # x = a,c,atm,vmid,width,kappa; delta tied to maximum atmospheric relaxation rate
 t=np.array(initial).copy(); c0=A.C(0.,t,1); x0=t[[0,1,2,5,6]].tolist()+[min(.48,c0/np.sqrt(t[3]))]
 def unpack(x):
  u=t.copy();u[[0,1,2,5,6]]=x[:5];u[3]=(A.C(0.,u,1)/x[5])**2;return u
 def obj(x):
  u=unpack(x);return np.concatenate([A.sim(A.D[s],u,1,1,0)[1:]-A.D[s][1:,0] for s in files])
 lo=[.0001,.0001,.985,0.,2.,.01];hi=[.004,.3,1.01,98.,70.,RATE_CAP]
 res=least_squares(obj,x0,bounds=(lo,hi),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 u=unpack(res.x)
 return {'module':'stable_mixed','kind':1,'drive':1,'inlet':0,'params':u.tolist(),'fit_values':res.x.tolist(),'starting_values':x0,'files':files,'rmse':{s:float(np.sqrt(np.mean((A.sim(d,u,1,1,0)[1:]-d[1:,0])**2))) for s,d in A.D.items()},'nfev':res.nfev,'cost':res.cost,'success':bool(res.success)}
if __name__=='__main__':
 results=json.load(open('final_results.json'));initial=results['MixedOutlet']['train_only']['initial'];r=fit(['train'],initial);z=fit(['train','val'],r['params']);z['train_only']=r;print('train-only',r['rmse'],r['fit_values']);print('joint',z['rmse'],z['fit_values'],'delta',z['params'][3]);
 results['MixedOutlet']=z;json.dump(results,open('final_results.json','w'),indent=2)
