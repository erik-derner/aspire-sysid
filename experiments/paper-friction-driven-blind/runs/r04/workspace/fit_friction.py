import numpy as np,json
from scipy.optimize import least_squares,differential_evolution
from numba import njit
from fit_rollout import load
@njit
def acc(y,v,u,p,k):
 a,b,c,f,s=p[:5]
 force=-a*np.sin(y+p[5])+c*u
 h=np.tanh(v/s);fric=f*h
 if k==28:fric+=p[6]*h*h
 if k==29:fric+=p[6]*v/(1+(v/p[7])**2)
 if k==30:fric+=max(-p[6],min(p[6],force))*(1-h*h)
 if k==31:fric=f*max(-1.,min(1.,v/s))
 if k==32:
  if abs(v)<s and abs(force)<p[6]:return -100.*v
  fric=f*np.sign(v)
 return force-b*v-fric
@njit
def simh(a,p,k):
 out=np.empty((len(a),2));out[0,:]=a[0,:2]
 for i in range(len(a)-1):
  y,v=out[i];u=a[i,2]
  d1=acc(y,v,u,p,k);y2=y+.005*v;v2=v+.005*d1
  d2=acc(y2,v2,u,p,k);y3=y+.005*v2;v3=v+.005*d2
  d3=acc(y3,v3,u,p,k);y4=y+.01*v3;v4=v+.01*d3
  d4=acc(y4,v4,u,p,k)
  out[i+1,0]=y+.01/6*(v+2*v2+2*v3+v4);out[i+1,1]=v+.01/6*(d1+2*d2+2*d3+d4)
  if not np.isfinite(out[i+1,0]) or abs(out[i+1,0])>100:
   out[i+1:,:]=100.;break
 return out
def residual(p,k,groups):return np.concatenate([simh(a,p,k)[1:,0]-a[1:,0] for a in groups])
def score(p,k,g):return float(np.sqrt(np.mean(residual(p,k,g)**2)))
def main():
 tr=load('data/train.csv');va=load('data/val.csv');out={}
 base=[110.,1.8,28.,20.,.3,-.03];lo=[50.,0.,10.,5.,.1,-.2];hi=[200.,10.,50.,40.,3.,.2]
 specs={'asymmetric':(28,[0.],[-10.],[10.]),'rational_damping':(29,[0.,1.],[-5.,.2],[10.,10.]),'free_static':(30,[20.],[5.],[40.]),'clip_friction':(31,[],[],[])}
 for name,(k,ps,ls,hs) in specs.items():
  best=None
  for s in [.15,.4,1.]:
   start=base+ps;start[4]=s
   fit=least_squares(residual,start,args=(k,tr),bounds=(lo+ls,hi+hs),x_scale='jac',max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-8)
   sc=score(fit.x,k,tr)
   print(name,s,sc,score(fit.x,k,va),fit.nfev,flush=True)
   if best is None or sc<best['train']:best={'kind':k,'p':fit.x.tolist(),'train':sc,'val':score(fit.x,k,va),'start':start,'lower':lo+ls,'upper':hi+hs,'nfev':fit.nfev,'status':fit.message}
  out[name]=best;print('BEST',name,best,flush=True)
  open('friction_results.json','w').write(json.dumps(out,indent=2))
 bounds=[(90,130),(0.5,3.5),(22,34),(15,27),(.1,.4),(-.08,.03),(15,35)]
 fit=differential_evolution(lambda p:score(p,32,tr),bounds,seed=1729,popsize=12,maxiter=300,tol=1e-6,polish=False)
 best={'kind':32,'p':fit.x.tolist(),'train':score(fit.x,32,tr),'val':score(fit.x,32,va),'bounds':bounds,'nfev':fit.nfev,'status':fit.message}
 out['karnopp']=best;print('BEST karnopp',best,flush=True)
 open('friction_results.json','w').write(json.dumps(out,indent=2))
if __name__=='__main__':main()
