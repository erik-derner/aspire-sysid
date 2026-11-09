import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
D={n:pd.read_csv('data/'+n+'.csv')[['p','valve','flow','dp']].to_numpy() for n in ['train','val']}
knots=np.array([0.,.10,.20,.30,.45,.65,1.])
@njit
def rhs(p,v,q,z):
 a,s,n,pa=z[:4]; x=max(0.,min(1.,(100.-v)/100.)); cv=0.;full=0.
 for j in range(6):
  cv+=z[4+j]*max(0.,min(1.,(x-knots[j])/(knots[j+1]-knots[j])));full+=z[4+j]
 h=p-pa
 return a*q-cv*max(h,0.)*(max(h,0.)+s)**(n-1.)+full*s**(n-1.)*max(-h,0.)
@njit
def sim(z,d):
 N=len(d);out=np.empty(N);out[0]=d[0,0]
 for k in range(N-1):
  p=out[k];v=d[k,1];q=d[k,2]
  k1=rhs(p,v,q,z);k2=rhs(p+2.5*k1,v,q,z);k3=rhs(p+2.5*k2,v,q,z);k4=rhs(p+5*k3,v,q,z)
  out[k+1]=p+5.*(k1+2.*k2+2.*k3+k4)/6.
  if not np.isfinite(out[k+1]) or abs(out[k+1])>100:out[k+1:]=100.;break
 return out
@njit
def deriv(z,d):
 out=np.empty(len(d))
 for k in range(len(d)):out[k]=rhs(d[k,0],d[k,1],d[k,2],z)
 return out
start=np.array([.0013,.04,.5,.99,.015,.02,.02,.025,.02,.015])
lo=np.r_[.0002,.002,.3,.98,np.zeros(6)];hi=np.r_[.004,.5,1.2,1.02,np.full(6,.15)]
def run(names,previous=None):
 if previous is None:
  def fd(z):return np.concatenate([(deriv(z,D[name])[:-1]-D[name][:-1,3])*100 for name in names])
  init=least_squares(fd,start,bounds=(lo,hi),x_scale='jac',max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-9).x
 else:init=previous
 def fs(z):return np.concatenate([sim(z,D[name])[1:]-D[name][1:,0] for name in names])
 fit=least_squares(fs,init,bounds=(lo,hi),x_scale='jac',max_nfev=1000,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 z=fit.x;rec={'params':z.tolist(),'start':start.tolist(),'init':init.tolist(),'data':names,'nfev':fit.nfev}
 for name,d in D.items():
  pred=sim(z,d);r=pred-d[:,0];dr=deriv(z,d)-d[:,3]
  rec[name+'_rmse']=float(np.sqrt(np.mean(r[1:]**2)));rec[name+'_derivative_rmse']=float(np.sqrt(np.mean(dr[:-1]**2)))
  np.savez('results/tabulated_'+('_'.join(names))+'_'+name+'.npz',pred=pred,res=r,dres=dr)
 print(rec,flush=True);return rec
if __name__=='__main__':
 rec=run(['train']);json.dump({'train':rec},open('results/tabulated.json','w'),indent=2)
 both=run(['train','val'],np.array(rec['params']));json.dump({'train':rec,'both':both},open('results/tabulated.json','w'),indent=2)
