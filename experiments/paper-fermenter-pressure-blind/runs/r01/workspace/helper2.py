"""Train-only nonlinear state-transform identification; validation selects structures.
Units of y,x1,x2 are unspecified; seconds are supplied time units.
"""
import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
T=pd.read_csv('data/train.csv').to_numpy();V=pd.read_csv('data/val.csv').to_numpy()
results=[]
def transform(kind,q,y):
 t=y-1
 if kind=='sqrt':return np.sqrt(np.maximum(y-q[0],1e-12))
 if kind=='log':return np.log(np.maximum(y-q[0],1e-12))
 if kind=='power':return np.maximum(y-q[0],1e-12)**q[1]
 if kind=='exp':return np.exp(np.clip(q[0]*t,-50,50))
 if kind=='atan':return np.arctan(q[0]*t)
 if kind=='tanh':return np.tanh(q[0]*t)
 raise ValueError(kind)
def design(kind,q,y,u,v,terms):
 w=transform(kind,q,y)
 D={'one':np.ones_like(y),'u':u,'v':v,'w':w,'uw':u*w,'vw':v*w,'uv':u*v,'uu':u*u,'vv':v*v,'ww':w*w,'y':y,'uy':u*y,'vy':v*y}
 return np.stack([D[t] for t in terms],axis=-1)
def rhs(p,kind,terms,y,u,v):return design(kind,p[len(terms):],y,u,v,terms)@p[:len(terms)]
def step(p,kind,terms,y,u,v):
 a=rhs(p,kind,terms,y,u,v);b=rhs(p,kind,terms,y+2.5*a,u,v);c=rhs(p,kind,terms,y+2.5*b,u,v);d=rhs(p,kind,terms,y+5*c,u,v)
 return y+5*(a+2*b+2*c+d)/6
 defunused=0

def sim(p,kind,terms,D):
 yh=np.empty(len(D));yh[0]=D[0,0]
 with np.errstate(all='ignore'):
  for i in range(len(D)-1):
   yh[i+1]=step(p,kind,terms,np.array([yh[i]]),np.array([D[i,1]/100]),np.array([D[i,2]/30]))[0]
   if not np.isfinite(yh[i+1]) or abs(yh[i+1])>100:return float('inf')
 return float(np.sqrt(np.mean((yh[1:]-D[1:,0])**2)))
def metrics(p,kind,terms,D):
 y,u,v,dy=D.T;u=u/100;v=v/30
 return {'derivative_rmse':float(np.sqrt(np.mean((rhs(p,kind,terms,y,u,v)-dy)**2))),'step_rmse':float(np.sqrt(np.mean((step(p,kind,terms,y[:-1],u[:-1],v[:-1])-y[1:])**2))),'free_rmse':sim(p,kind,terms,D)}
def fit(kind,terms,starts,bounds):
 y,u,v,dy=T.T;u=u/100;v=v/30;n=len(terms)
 def res(p):return step(p,kind,terms,y[:-1],u[:-1],v[:-1])-y[1:]
 best=None;record=[]
 for q in starts:
  A=design(kind,q,y,u,v,terms);c=np.linalg.lstsq(A,dy,rcond=None)[0];p0=np.r_[c,q]
  opt=least_squares(res,p0,bounds=(np.r_[np.full(n,-100),bounds[0]],np.r_[np.full(n,100),bounds[1]]),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  record.append({'initial':p0.tolist(),'cost':float(opt.cost),'nfev':opt.nfev})
  if best is None or opt.cost<best.cost:best=opt
 p=best.x;r={'kind':kind,'terms':terms,'p':p.tolist(),'starts':record,'bounds':bounds,'train':metrics(p,kind,terms,T),'val':metrics(p,kind,terms,V)}
 results.append(r);json.dump(results,open('helper2_results.json','w'),indent=2);print(json.dumps(r),flush=True)
if __name__=='__main__':
 base=['one','u','v','w','uw','vw','uv']
 for extra in [['uu','vv'],['uu','vv','ww'],['uu'],['vv'],['y'],['uu','vv','y']]:
  for kind in ['sqrt','log','exp','atan']:
   if kind in ['sqrt','log']:starts=[[0.98],[0.5]];bounds=([-5],[0.99])
   elif kind=='exp':starts=[[-1],[-4]];bounds=([-15],[15])
   else:starts=[[1],[5]];bounds=([0.01],[30])
   fit(kind,base+extra,starts,bounds)
 for extra in [['uu','vv'],['uu','vv','ww']]:fit('power',base+extra,[[0.98,0.5],[0.5,0.7]],([-5,-2],[0.99,3]))
