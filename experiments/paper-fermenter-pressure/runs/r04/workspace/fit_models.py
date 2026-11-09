import os,json,time
import numpy as np,pandas as pd
from scipy.optimize import least_squares
from numba import njit
D={n:pd.read_csv('data/'+n+'.csv').to_numpy() for n in ['train','val']}
# Columns are checked explicitly, not assumed.
D={n:pd.read_csv('data/'+n+'.csv')[['p','valve','flow','dp']].to_numpy() for n in ['train','val']}
# Parameters: a inlet; b conductance; c valve shape; s pressure regularizer; n exponent; extras.
@njit
def rhs(p,v,q,z,fam):
 a,b,c,s,n=z[:5]; x=max(0.,min(1.,(100.-v)/100.)); h=p-1.
 if fam==0: cv=b*x**c # power aperture
 elif fam==1: cv=b*(1.-np.exp(-c*x)) # saturating aperture
 elif fam==2: cv=b*x/(c+x) # rational aperture
 elif fam==3: cv=b*np.tanh(c*x) # smooth saturation
 elif fam==4: cv=b*(np.exp(c*x)-1.)/(np.exp(c)-1.) # equal percentage
 elif fam==5: cv=b*(x+z[5]*x*x)/(1.+c*x*x) # rational quadratic
 elif fam==6: cv=b*(1.-np.exp(-c*x**z[5])) # saturating power
 else: cv=b*x**c
 # Regularized pressure power: h*(h+s)**(n-1), finite at atmosphere.
 if h>=0: return a*q-cv*h*(h+s)**(n-1.)
 # linear vacuum recovery independent of closure, enforces global R2.
 if fam==0 or fam==7: full=b
 elif fam==1: full=b*(1.-np.exp(-c))
 elif fam==2: full=b/(c+1.)
 elif fam==3: full=b*np.tanh(c)
 elif fam==4: full=b
 elif fam==5: full=b*(1.+z[5])/(1.+c)
 else: full=b*(1.-np.exp(-c))
 return a*q-full*s**(n-1.)*h
@njit
def sim(z,d,fam):
 N=len(d); out=np.empty(N);out[0]=d[0,0]
 for k in range(N-1):
  p=out[k];v=d[k,1];q=d[k,2]
  k1=rhs(p,v,q,z,fam);k2=rhs(p+2.5*k1,v,q,z,fam);k3=rhs(p+2.5*k2,v,q,z,fam);k4=rhs(p+5*k3,v,q,z,fam)
  out[k+1]=p+5*(k1+2*k2+2*k3+k4)/6.
  if not np.isfinite(out[k+1]) or abs(out[k+1])>100:
   out[k+1:]=100.;break
 return out
@njit
def deriv(z,d,fam):
 out=np.empty(len(d))
 for k in range(len(d)):out[k]=rhs(d[k,0],d[k,1],d[k,2],z,fam)
 return out
specs={
 'linear_power':(0,[.001,.1,1.5,.1,1.],[0,1,2]),
 'orifice_power':(0,[.0012,.12,1.2,.04,.5],[0,1,2,3]),
 'orifice_saturating':(1,[.0012,.12,2.,.04,.5],[0,1,2,3]),
 'orifice_rational':(2,[.0012,.12,.2,.04,.5],[0,1,2,3]),
 'power_saturating':(1,[.0012,.12,2.,.04,.6],[0,1,2,3,4]),
 'power_rational':(2,[.0012,.12,.2,.04,.6],[0,1,2,3,4]),
 'power_tanh':(3,[.0012,.12,2.,.04,.6],[0,1,2,3,4]),
 'power_equalpercent':(4,[.0012,.12,1.,.04,.6],[0,1,2,3,4]),
 'power_satpower':(6,[.0012,.12,2.,.04,.6,1.5],[0,1,2,3,4,5])}
lo=np.array([.00005,.005,.03,.005,.3,.2]);hi=np.array([.006,.8,20.,.4,1.5,4.])
def run(label,fam,start,idx):
 start=np.array(start);idx=np.array(idx); L=lo[:len(start)][idx];H=hi[:len(start)][idx]
 def unpack(t):
  z=start.copy();z[idx]=t;return z
 def fd(t):return (deriv(unpack(t),D['train'],fam)[:-1]-D['train'][:-1,3])*100
 init=least_squares(fd,start[idx],bounds=(L,H),x_scale='jac',max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-9)
 def fs(t):return sim(unpack(t),D['train'],fam)[1:]-D['train'][1:,0]
 fit=least_squares(fs,init.x,bounds=(L,H),x_scale='jac',max_nfev=500,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 z=unpack(fit.x);rec={'fam':fam,'start':start.tolist(),'idx':idx.tolist(),'derivative_init':unpack(init.x).tolist(),'params':z.tolist(),'nfev':fit.nfev,'success':bool(fit.success),'bounds_lower':L.tolist(),'bounds_upper':H.tolist()}
 for name,d in D.items():
  pred=sim(z,d,fam);r=pred-d[:,0];dr=deriv(z,d,fam)-d[:,3]
  rec[name+'_rmse']=float(np.sqrt(np.mean(r[1:]**2)));rec[name+'_derivative_rmse']=float(np.sqrt(np.mean(dr[:-1]**2)))
  np.savez('results/'+label+'_'+name+'.npz',pred=pred,res=r,dres=dr)
 print(label,rec['params'],'RMSE',rec['train_rmse'],rec['val_rmse'],flush=True)
 return rec
if __name__=='__main__':
 os.makedirs('results',exist_ok=True);results={}
 for label,spec in specs.items():
  results[label]=run(label,*spec);json.dump(results,open('results/fits.json','w'),indent=2)
